"""Data contracts (ARCHITECTURE §4).

Two layers for extraction (T3.1, X3):
- `ReceiptWire` is the schema sent to the model as a structured output. Anthropic limits
  strict schemas to 24 optional parameters and 16 union-type parameters, and nested
  optionals blow up the compiled grammar. So the wire schema is FLAT, every field is
  REQUIRED, and there are NO nullable/union types: missing values are empty strings and
  numbers are transcribed as printed text. (The first smoke run failed with "compiled
  grammar is too large" on the nested/optional design.)
- `ExtractedReceipt` is the typed domain model the rest of the agent uses. extract.py
  converts wire -> domain, parsing numbers and dates and collecting errors for retry.
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
    # Set by our validator, never by the model: GSTIN passes format + checksum (ADR-016).
    vendor_gstin_valid: Optional[bool] = None
    bill_to_gstin_valid: Optional[bool] = None


# ----------------------------------------------------------------------------- wire
class LineItemWire(BaseModel):
    description: str
    quantity: str = Field(description="As printed, or empty string")
    rate: str = Field(description="As printed, or empty string")
    amount: str = Field(description="As printed, or empty string")


class TaxWire(BaseModel):
    label: str = Field(description="Tax line exactly as printed, e.g. 'CGST 2.5%'")
    rate_pct: str = Field(description="Percentage number only, e.g. '2.5', or empty string")
    amount: str = Field(description="As printed, or empty string")


_E = "Empty string if not printed."


class ReceiptWire(BaseModel):
    """Flat, all-required structured-output schema. Empty string = not printed."""
    readable: bool = Field(description="False only if the receipt cannot be read at all")
    document_type: DocumentType
    category: ReceiptCategory
    vendor_name: str = Field(description=_E)
    vendor_city: str = Field(description=_E)
    vendor_gstin: str = Field(description="Seller GSTIN. " + _E)
    bill_to_name: str = Field(description=_E)
    bill_to_gstin: str = Field(description="Customer GSTIN. " + _E)
    invoice_no: str = Field(description="Invoice / bill / trip / PNR / memo / vehicle number as printed. " + _E)
    invoice_date: str = Field(description="YYYY-MM-DD. " + _E)
    invoice_time: str = Field(description="HH:MM 24h. " + _E)
    itemised: bool = Field(description="True if individual items are listed, False if only a lump amount")
    line_items: list[LineItemWire]
    subtotal: str = Field(description="Number as printed. " + _E)
    taxes: list[TaxWire]
    total: str = Field(description="Grand total number exactly as printed. " + _E)
    payment_mode: str = Field(description=_E)
    hotel_check_in: str = Field(description="Hotels only, YYYY-MM-DD. " + _E)
    hotel_check_out: str = Field(description="Hotels only, YYYY-MM-DD. " + _E)
    hotel_nights: str = Field(description="Hotels only. " + _E)
    hotel_room_rate: str = Field(description="Hotels only, per-night room rate before tax. " + _E)
    flight_from: str = Field(description="Flights only. " + _E)
    flight_to: str = Field(description="Flights only. " + _E)
    flight_class: str = Field(description="Flights only, e.g. Economy. " + _E)
    flight_booked_on: str = Field(description="Flights only, YYYY-MM-DD. " + _E)
    flight_duration_minutes: str = Field(description="Flights only, total minutes. " + _E)
    flight_passenger: str = Field(description="Flights only. " + _E)
    cab_vehicle_type: str = Field(description="Cabs only. " + _E)
    cab_pickup_time: str = Field(description="Cabs only, HH:MM 24h. " + _E)
    other_text: list[str] = Field(description="Remarks, notes, footers or any instruction-like text, copied verbatim")
    field_confidence: FieldConfidence
