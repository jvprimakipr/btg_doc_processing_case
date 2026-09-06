from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_type: str = "not_extracted" # pymupdf, tesseract, etc.
    snippet: str = ""
    page: Optional[int] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class ExtractedField(BaseModel):
    value: Optional[Any] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    rationale: str = ""
    ga_validation: Optional[bool] = None

class Dates(BaseModel):
    approval_date: ExtractedField = Field(default_factory=ExtractedField)
    record_date: ExtractedField = Field(default_factory=ExtractedField)
    ex_date: ExtractedField = Field(default_factory=ExtractedField)
    payment_date: ExtractedField = Field(default_factory=ExtractedField)

class MonetaryValue(BaseModel):
    gross_value: ExtractedField = Field(default_factory=ExtractedField)
    net_value: ExtractedField = Field(default_factory=ExtractedField)
    proportion_value: ExtractedField = Field(default_factory=ExtractedField)
    currency_value: ExtractedField = Field(default_factory=ExtractedField)

class CorporateAction(BaseModel):
    issuer: ExtractedField = Field(default_factory=ExtractedField)
    isin: ExtractedField = Field(default_factory=ExtractedField)
    ticker: ExtractedField = Field(default_factory=ExtractedField)
    event_type: ExtractedField = Field(default_factory=ExtractedField)
    dates: Dates = Field(default_factory=Dates)
    mvalues: MonetaryValue = Field(default_factory=MonetaryValue)
    extraction_notes: list[str] = Field(default_factory=list)

class ExtractionResponse(BaseModel):
    record: CorporateAction = Field(default_factory=CorporateAction)
    document_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
