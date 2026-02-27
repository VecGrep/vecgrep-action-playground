"""Data access layer — repositories for each domain entity."""

from __future__ import annotations

from dataclasses import dataclass

from .connection import QueryResult, execute, execute_many


# ---------------------------------------------------------------------------
# User repository
# ---------------------------------------------------------------------------

@dataclass
class UserRecord:
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool


def get_user_by_id(user_id: int) -> UserRecord | None:
    result = execute(
        "SELECT id, username, email, password_hash, is_active FROM users WHERE id = ?",
        (user_id,),
    )
    if not result.rows:
        return None
    row = result.rows[0]
    return UserRecord(**row)


def get_user_by_username(username: str) -> UserRecord | None:
    result = execute(
        "SELECT id, username, email, password_hash, is_active FROM users WHERE username = ?",
        (username,),
    )
    if not result.rows:
        return None
    return UserRecord(**result.rows[0])


def create_user(username: str, email: str, password_hash: str) -> int:
    result = execute(
        "INSERT INTO users (username, email, password_hash, is_active) VALUES (?, ?, ?, 1)",
        (username, email, password_hash),
    )
    return result.row_count


def deactivate_user(user_id: int) -> bool:
    result = execute(
        "UPDATE users SET is_active = 0 WHERE id = ?",
        (user_id,),
    )
    return result.row_count > 0


# ---------------------------------------------------------------------------
# Order repository
# ---------------------------------------------------------------------------

@dataclass
class OrderRecord:
    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: str


def get_orders_by_user(user_id: int) -> list[OrderRecord]:
    result = execute(
        "SELECT id, user_id, total_amount, status, created_at FROM orders WHERE user_id = ?",
        (user_id,),
    )
    return [OrderRecord(**row) for row in result.rows]


def get_order_by_id(order_id: int) -> OrderRecord | None:
    result = execute(
        "SELECT id, user_id, total_amount, status, created_at FROM orders WHERE id = ?",
        (order_id,),
    )
    if not result.rows:
        return None
    return OrderRecord(**result.rows[0])


def create_order(user_id: int, total_amount: float) -> int:
    result = execute(
        "INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, 'pending')",
        (user_id, total_amount),
    )
    return result.row_count


def update_order_status(order_id: int, status: str) -> bool:
    result = execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (status, order_id),
    )
    return result.row_count > 0
