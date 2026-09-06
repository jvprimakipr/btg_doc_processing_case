from datetime import datetime
from pathlib import Path
from typing import Any
from itertools import combinations

import pandas as pd
import pymupdf
import pytesseract
from langchain_core.tools import tool
from PIL import Image


@tool
def read_pdf_with_pymupdf(path: str) -> str:
    """Extract native text from a PDF using PyMuPDF."""

    document = pymupdf.open(path)
    text = "\n".join(page.get_text() for page in document).strip()

    return text

@tool
def read_pdf_with_tesseract(path: str) -> str:
    """Render PDF pages and extract their text using Tesseract OCR."""

    document = pymupdf.open(path)
    pages = []

    for page in document:
        pixels = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixels.width, pixels.height], pixels.samples)

        try:
            pages.append(pytesseract.image_to_string(image, lang="por+eng"))
        except Exception:
            pages.append(pytesseract.image_to_string(image, lang="eng"))

    return "\n".join(pages).strip()

def _field_value(record: dict[str, Any], *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value.get("value") if isinstance(value, dict) else value

@tool
def validate_reference(record: dict[str, Any], reference_path: str = "data/golden_records.csv") -> dict[str, Any]:
    """Compare issuer, ISIN and ticker with the golden reference CSV."""

    reference = pd.read_csv(Path(reference_path), encoding="utf-8-sig").fillna("").to_dict("records")
    issuer = str(_field_value(record, "issuer") or "").strip().upper()
    isin = str(_field_value(record, "isin") or "").strip().upper()
    ticker = str(_field_value(record, "ticker") or "").strip().upper()

    matches = [
        row for row in reference
        if (issuer and str(row.get("emissor", "")).strip().upper() == issuer)
        or (isin and str(row.get("isin", "")).strip().upper() == isin)
        or (ticker and str(row.get("ticker", "")).strip().upper() == ticker)
    ]
    if not matches:
        return {"status": "fail", "matched_fields": [], "reference_record": None}

    row = matches[0]
    checks = {
        "issuer": not issuer or issuer == str(row.get("emissor", "")).strip().upper(),
        "isin": not isin or isin == str(row.get("isin", "")).strip().upper(),
        "ticker": not ticker or ticker == str(row.get("ticker", "")).strip().upper(),
    }

    return {
        "status": "pass" if all(checks.values()) else "conflict",
        "matched_fields": [field for field, passed in checks.items() if passed],
        "reference_record": row,
    }

@tool
def validate_dates(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the chronological order of dates in a corporate action record."""

    date_fields = ("approval_date", "record_date", "ex_date", "payment_date")
    parsed_dates: dict[str, datetime] = {}
    issues = []

    for field_name in date_fields:
        value = _field_value(record, "dates", field_name)
        if not value:
            continue
        try:
            parsed_dates[field_name] = datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError:
            issues.append(f"invalid date format in {field_name}")

    for earlier, later in combinations(date_fields, 2):
        if (
            earlier in parsed_dates
            and later in parsed_dates
            and parsed_dates[earlier] > parsed_dates[later]
        ):
            issues.append(f"{earlier} ({parsed_dates[earlier]}) must not be after {later} ({parsed_dates[later]})")

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
    }

@tool
def validate_monetary_values(record: dict[str, Any]) -> dict[str, Any]:
    """Validate gross and net monetary values from a corporate action record."""

    issues = []
    gross = _field_value(record, "mvalues", "gross_value")
    net = _field_value(record, "mvalues", "net_value")

    if gross is not None and net is not None:
        try:
            if float(net) > float(gross):
                issues.append("net value must not be greater than gross value")
        except (TypeError, ValueError):
            issues.append("gross/net values are not numeric")

        if gross < 0:
            issues.append("gross value must not be negative")
        if net < 0:
            issues.append("net value must not be negative")

    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
    }
