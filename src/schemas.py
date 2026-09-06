from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_type: Literal["pymupdf", "pytesseract"] = Field(
        description="Method used to extract this evidence from the source text."
    )
    snippet: str = Field(
        description="Exact short excerpt copied from the source text."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in this evidence item, from 0.0 to 1.0."
    )

class ExtractedField(BaseModel):
    value: Optional[Any] = None
    status: Literal[
        "extracted",
        "not_found",
        "not_applicable",
        "unreadable",
        "conflicting",
        "validation_error"
    ] = Field(
        default="not_found",
        description=(
            "Extraction status: use 'extracted' when a value was identified; "
            "'not_found' when the field applies but no value was found; "
            "'not_applicable' when the field does not apply to the event; "
            "'unreadable' when the field is present but unclear; "
            "'conflicting' when extraction sources disagree; and "
            "'validation_error' only when post-extraction validation finds an error."
        )
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in the extracted value; null when no reliable confidence score can be assigned."
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="One evidence item per distinct extraction source that supports the value."
    )
    rationale: str = Field(
        default="",
        description="Short explanation for the extraction status and value."
    )

EventType = Literal[
    "Dividendo",
    "JCP",
    "Bonificação",
    "Grupamento",
    "Desdobramento",
    "Subscrição",
    "Direito de preferência",
    "Fusão",
    "Cisão",
    "Incorporação",
    "Oferta pública",
    "Outro",
]

class EventTypeField(ExtractedField):
    value: Optional[EventType] = None

class Dates(BaseModel):
    approval_date: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Date when the corporate action was approved."
    )
    record_date: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Last date with entitlement to the corporate action."
    )
    ex_date: ExtractedField = Field(
        default_factory=ExtractedField,
        description="First date when the asset is traded without entitlement to the corporate action."
    )
    payment_date: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Date when the benefit is paid or delivered."
    )

class MonetaryDetails(BaseModel):
    gross_value: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Gross monetary amount per share or unit."
    )
    net_value: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Net monetary amount after applicable deductions."
    )
    proportion: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Ratio used for bonuses, splits, or reverse splits."
    )
    currency: ExtractedField = Field(
        default_factory=ExtractedField,
        description="ISO 4217 currency code, such as BRL, USD, or EUR."
    )

class CorporateAction(BaseModel):
    issuer: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Company or issuer responsible for the corporate action."
    )
    isin: ExtractedField = Field(
        default_factory=ExtractedField,
        description="12-character ISIN identifying the relevant security."
    )
    ticker: ExtractedField = Field(
        default_factory=ExtractedField,
        description="Trading ticker of the relevant security."
    )
    event_type: EventTypeField = Field(
        default_factory=EventTypeField,
        description="Classification of the corporate action"
    )
    dates: Dates = Field(
        default_factory=Dates,
        description="Relevant dates using the DD-MM-YYYY format"
    )
    monetary_details: MonetaryDetails = Field(
        default_factory=MonetaryDetails,
        description="Monetary amounts, proportions, and currency of the event. Not all fields apply to every event type."
    )
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Additional notes about ambiguity, missing data or extraction limitations.",
    )
    gr_validation: Literal[
        "not_validated",
        "pass",
        "failed",
    ] = Field(
        default="not_validated",
        description="Validation status of the record against the golden reference data."
    )

class ExtractionResponse(BaseModel):
    record: CorporateAction = Field(default_factory=CorporateAction)
    document_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the extracted document record."
    )
