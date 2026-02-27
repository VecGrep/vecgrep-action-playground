"""API route handlers — wires auth middleware to domain logic."""

from __future__ import annotations

from ..auth.authentication import Session, authenticate_user, revoke_token
from ..auth.middleware import Request, Response, auth_middleware
from ..database.repository import (
    create_order,
    get_order_by_id,
    get_orders_by_user,
    get_user_by_username,
    update_order_status,
)
from ..payments.processor import (
    ChargeResult,
    charge,
    create_payment_intent,
    get_payment_intent,
    refund,
)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

def login(request: Request) -> Response:
    """POST /auth/login — exchange credentials for a session token."""
    import json
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status=400, body="Invalid JSON body.")

    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return Response(status=400, body="username and password are required.")

    user_record = get_user_by_username(username)
    if not user_record:
        return Response(status=401, body="Invalid credentials.")

    from ..auth.authentication import User, authenticate_user
    user = User(
        id=user_record.id,
        username=user_record.username,
        email=user_record.email,
        password_hash=user_record.password_hash,
        is_active=user_record.is_active,
    )
    user_db = {user.username: user}
    session = authenticate_user(username, password, user_db)
    if not session:
        return Response(status=401, body="Invalid credentials.")

    return Response(status=200, body=json.dumps({"token": session.token}))


@auth_middleware
def logout(request: Request, session: Session) -> Response:
    """POST /auth/logout — invalidate the current session token."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    revoke_token(token)
    return Response(status=200, body="Logged out.")


# ---------------------------------------------------------------------------
# Order routes
# ---------------------------------------------------------------------------

@auth_middleware
def list_orders(request: Request, session: Session) -> Response:
    """GET /orders — list orders for the authenticated user."""
    import json
    orders = get_orders_by_user(session.user_id)
    data = [
        {"id": o.id, "total_amount": o.total_amount, "status": o.status}
        for o in orders
    ]
    return Response(status=200, body=json.dumps(data))


@auth_middleware
def create_order_handler(request: Request, session: Session) -> Response:
    """POST /orders — create a new order for the authenticated user."""
    import json
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status=400, body="Invalid JSON body.")

    total_amount = body.get("total_amount")
    if total_amount is None or float(total_amount) <= 0:
        return Response(status=400, body="total_amount must be a positive number.")

    create_order(session.user_id, float(total_amount))
    return Response(status=201, body="Order created.")


# ---------------------------------------------------------------------------
# Payment routes
# ---------------------------------------------------------------------------

@auth_middleware
def charge_handler(request: Request, session: Session) -> Response:
    """POST /payments/charge — charge a payment intent."""
    import json
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status=400, body="Invalid JSON body.")

    amount_cents = body.get("amount_cents")
    if not amount_cents or int(amount_cents) <= 0:
        return Response(status=400, body="amount_cents must be a positive integer.")

    intent = create_payment_intent(session.user_id, int(amount_cents))
    result: ChargeResult = charge(intent.id)

    if not result.success:
        return Response(status=402, body=json.dumps({"error": result.error_message}))
    return Response(status=200, body=json.dumps({"payment_intent_id": result.payment_intent_id}))


@auth_middleware
def refund_handler(request: Request, session: Session) -> Response:
    """POST /payments/refund — refund a payment intent."""
    import json
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status=400, body="Invalid JSON body.")

    payment_intent_id = body.get("payment_intent_id", "")
    amount_cents = body.get("amount_cents")

    result = refund(payment_intent_id, int(amount_cents) if amount_cents else None)
    if not result.success:
        return Response(status=400, body=json.dumps({"error": result.error_message}))
    return Response(status=200, body=json.dumps({"refund_id": result.refund_id}))
