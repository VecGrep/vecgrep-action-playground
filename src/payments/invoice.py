"""Invoice generation — intentionally similar logic to processor.py for duplicate detection testing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    VOID = "void"


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price_cents: int

    @property
    def total_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass
class Invoice:
    id: str
    user_id: int
    line_items: list[LineItem]
    currency: str
    status: InvoiceStatus
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def total_amount_cents(self) -> int:
        return sum(item.total_cents for item in self.line_items)


@dataclass
class InvoiceResult:
    success: bool
    invoice_id: str
    error_message: str = ""


_invoices: dict[str, Invoice] = {}


def create_invoice(
    user_id: int,
    line_items: list[LineItem],
    currency: str = "usd",
    metadata: dict | None = None,
) -> Invoice:
    """Create a draft invoice for the given user and line items."""
    if not line_items:
        raise ValueError("Invoice must have at least one line item.")
    invoice = Invoice(
        id=str(uuid.uuid4()),
        user_id=user_id,
        line_items=line_items,
        currency=currency.lower(),
        status=InvoiceStatus.DRAFT,
        metadata=metadata or {},
    )
    _invoices[invoice.id] = invoice
    return invoice


def send_invoice(invoice_id: str) -> InvoiceResult:
    """Mark a draft invoice as sent."""
    invoice = _invoices.get(invoice_id)
    if not invoice:
        return InvoiceResult(success=False, invoice_id=invoice_id,
                             error_message="Invoice not found.")
    if invoice.status != InvoiceStatus.DRAFT:
        return InvoiceResult(success=False, invoice_id=invoice_id,
                             error_message=f"Invoice is '{invoice.status.value}', expected 'draft'.")
    invoice.status = InvoiceStatus.SENT
    return InvoiceResult(success=True, invoice_id=invoice.id)


def void_invoice(invoice_id: str) -> InvoiceResult:
    """Void an invoice, preventing further payment."""
    invoice = _invoices.get(invoice_id)
    if not invoice:
        return InvoiceResult(success=False, invoice_id=invoice_id,
                             error_message="Invoice not found.")
    if invoice.status == InvoiceStatus.VOID:
        return InvoiceResult(success=False, invoice_id=invoice_id,
                             error_message="Invoice is already void.")
    invoice.status = InvoiceStatus.VOID
    return InvoiceResult(success=True, invoice_id=invoice.id)


def get_invoice(invoice_id: str) -> Invoice | None:
    return _invoices.get(invoice_id)
