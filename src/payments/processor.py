"""Payment processing — charge, refund, and transaction management."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


PAYMENT_GATEWAY_URL = os.environ.get("PAYMENT_GATEWAY_URL", "")
PAYMENT_API_KEY = os.environ.get("PAYMENT_API_KEY", "")


class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class PaymentIntent:
    id: str
    user_id: int
    amount_cents: int
    currency: str
    status: PaymentStatus
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class ChargeResult:
    success: bool
    payment_intent_id: str
    error_message: str = ""


@dataclass
class RefundResult:
    success: bool
    refund_id: str
    error_message: str = ""


_intents: dict[str, PaymentIntent] = {}


def create_payment_intent(
    user_id: int,
    amount_cents: int,
    currency: str = "usd",
    metadata: dict | None = None,
) -> PaymentIntent:
    """Create a new payment intent for the given user and amount."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be a positive integer.")
    intent = PaymentIntent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount_cents=amount_cents,
        currency=currency.lower(),
        status=PaymentStatus.PENDING,
        metadata=metadata or {},
    )
    _intents[intent.id] = intent
    return intent


def charge(payment_intent_id: str) -> ChargeResult:
    """
    Attempt to charge a payment intent.
    In production this would call the payment gateway API.
    """
    intent = _intents.get(payment_intent_id)
    if not intent:
        return ChargeResult(success=False, payment_intent_id=payment_intent_id,
                            error_message="Payment intent not found.")
    if intent.status != PaymentStatus.PENDING:
        return ChargeResult(success=False, payment_intent_id=payment_intent_id,
                            error_message=f"Intent is in status '{intent.status.value}', expected 'pending'.")

    # Simulate gateway call
    if not PAYMENT_GATEWAY_URL or not PAYMENT_API_KEY:
        intent.status = PaymentStatus.FAILED
        return ChargeResult(success=False, payment_intent_id=intent.id,
                            error_message="Payment gateway not configured.")

    intent.status = PaymentStatus.SUCCEEDED
    return ChargeResult(success=True, payment_intent_id=intent.id)


def refund(payment_intent_id: str, amount_cents: int | None = None) -> RefundResult:
    """
    Refund a previously succeeded payment intent.
    Partial refunds supported via amount_cents.
    """
    intent = _intents.get(payment_intent_id)
    if not intent:
        return RefundResult(success=False, refund_id="",
                            error_message="Payment intent not found.")
    if intent.status != PaymentStatus.SUCCEEDED:
        return RefundResult(success=False, refund_id="",
                            error_message="Only succeeded payments can be refunded.")

    refund_amount = amount_cents or intent.amount_cents
    if refund_amount > intent.amount_cents:
        return RefundResult(success=False, refund_id="",
                            error_message="Refund amount exceeds original charge.")

    intent.status = PaymentStatus.REFUNDED
    return RefundResult(success=True, refund_id=str(uuid.uuid4()))


def get_payment_intent(payment_intent_id: str) -> PaymentIntent | None:
    return _intents.get(payment_intent_id)
