"""Data contracts (ARCHITECTURE §4).

`ExtractedReceipt` is the structured-output schema sent to the model. It deliberately
has no validators or numeric constraints: the API enforces the *shape*, and our own
business checks (extract.validate_receipt) run afterwards so failures can be retried
and logged instead of raising inside the SDK (T3.1 decision X3).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

DocumentType = Literal[
    "hotel_invoice", "restaurant_bill", "cab_receipt", "auto_receipt", "flight_ticket",
    "laundry_memo", "telecom_invoice", "store_invoice", "other",
]
ReceiptCategory = Literal[
    "hotel", "meal", "local_transport", "flight", "laundry", "connectivity", "incidental", "other",
]
Confidence = Literal["high", "low"]


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    rate: Optional[float] = None
    amount: Optional[float] = None


class Tax(BaseModel):
    label: str = Field(description="Tax line exactly as printed, e.g. 'CGST 2.5%'")
    rate_pct: Optional[float] = None
    amount: Optional[float] = None


class HotelDetails(BaseModel):
    check_in: Optional[str] = Field(None, description="YYYY-MM-DD")
    check_out: Optional[str] = Field(None, description="YYYY-MM-DD")
    nights: Optional[int] = None
    room_rate: Optional[float] = Field(None, description="Per-night room rate before tax")


class FlightDetails(BaseModel):
    route_from: Optional[str] = None
    route_to: Optional[str] = None
    travel_class: Optional[str] = None
    booked_on: Optional[str] = Field(None, description="YYYY-MM-DD")
    duration_minutes: Optional[int] = None
    passenger: Optional[str] = None


class CabDetails(BaseModel):
    vehicle_type: Optional[str] = None
    pickup_time: Optional[str] = Field(None, description="HH:MM, 24h")


class FieldConfidence(BaseModel):
    vendor_name: Confidence
    invoice_date: Confidence
    total: Confidence
    vendor_gstin: Confidence
    category: Confidence


class ExtractedReceipt(BaseModel):
    readable: bool = Field(description="False only if the receipt cannot be read at all")
    document_type: DocumentType
    category: ReceiptCategory
    vendor_name: Optional[str] = None
    vendor_city: Optional[str] = None
    vendor_gstin: Optional[str] = None
    bill_to_name: Optional[str] = None
    bill_to_gstin: Optional[str] = None
    invoice_no: Optional[str] = Field(None, description="Invoice / bill / trip / PNR / memo number as printed")
    invoice_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    invoice_time: Optional[str] = Field(None, description="HH:MM, 24h")
    itemised: bool = Field(description="True if individual items are listed, False if only a lump total")
    line_items: list[LineItem]
    subtotal: Optional[float] = None
    taxes: list[Tax]
    total: Optional[float] = Field(None, description="Grand total exactly as printed")
    payment_mode: Optional[str] = None
    hotel: Optional[HotelDetails] = None
    flight: Optional[FlightDetails] = None
    cab: Optional[CabDetails] = None
    other_text: list[str] = Field(description="Remarks, notes, footers or any instruction-like text, copied verbatim")
    field_confidence: FieldConfidence
