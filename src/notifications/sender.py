"""Notification service — email and webhook delivery."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class Notification:
    id: str
    user_id: int
    channel: str
    subject: str
    body: str
    status: NotificationStatus
    created_at: float = field(default_factory=time.time)
    sent_at: float | None = None
    error: str = ""


@dataclass
class SendResult:
    success: bool
    notification_id: str
    error_message: str = ""


_notifications: dict[str, Notification] = {}


def create_notification(
    user_id: int,
    channel: str,
    subject: str,
    body: str,
) -> Notification:
    """Create a pending notification for the given user."""
    if channel not in ("email", "webhook", "sms"):
        raise ValueError(f"Unsupported notification channel: {channel}")
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        channel=channel,
        subject=subject,
        body=body,
        status=NotificationStatus.PENDING,
    )
    _notifications[notification.id] = notification
    return notification


def send_email(notification_id: str) -> SendResult:
    """Send a pending notification via email (SMTP)."""
    notification = _notifications.get(notification_id)
    if not notification:
        return SendResult(success=False, notification_id=notification_id,
                          error_message="Notification not found.")
    if notification.status != NotificationStatus.PENDING:
        return SendResult(success=False, notification_id=notification_id,
                          error_message=f"Notification is '{notification.status.value}', expected 'pending'.")
    if not SMTP_HOST or not SMTP_USER:
        notification.status = NotificationStatus.FAILED
        notification.error = "SMTP not configured."
        return SendResult(success=False, notification_id=notification_id,
                          error_message="SMTP not configured.")

    notification.status = NotificationStatus.SENT
    notification.sent_at = time.time()
    return SendResult(success=True, notification_id=notification_id)


def send_webhook(notification_id: str, url: str) -> SendResult:
    """Deliver a notification payload to a webhook URL."""
    import json
    import hmac
    import hashlib
    import urllib.request
    import urllib.error

    notification = _notifications.get(notification_id)
    if not notification:
        return SendResult(success=False, notification_id=notification_id,
                          error_message="Notification not found.")
    if notification.status != NotificationStatus.PENDING:
        return SendResult(success=False, notification_id=notification_id,
                          error_message=f"Notification is '{notification.status.value}', expected 'pending'.")

    payload = json.dumps({
        "id": notification.id,
        "user_id": notification.user_id,
        "subject": notification.subject,
        "body": notification.body,
    }).encode()

    headers = {"Content-Type": "application/json"}
    if WEBHOOK_SECRET:
        sig = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        headers["X-VecGrep-Signature"] = f"sha256={sig}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5):
            notification.status = NotificationStatus.SENT
            notification.sent_at = time.time()
            return SendResult(success=True, notification_id=notification_id)
    except urllib.error.URLError as e:
        notification.status = NotificationStatus.FAILED
        notification.error = str(e)
        return SendResult(success=False, notification_id=notification_id,
                          error_message=str(e))


def get_notification(notification_id: str) -> Notification | None:
    return _notifications.get(notification_id)
