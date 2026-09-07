from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd


PTBR_NAMES = {
    "issuer": "Emissor",
    "isin": "ISIN",
    "ticker": "Ticker",
    "event_type": "Tipo de evento",
    "approval_date": "Data de aprovação",
    "record_date": "Data 'com'",
    "ex_date": "Data 'ex'",
    "payment_date": "Data de pagamento",
    "gross_value": "Valor bruto",
    "net_value": "Valor líquido",
    "proportion": "Proporção",
    "currency": "Moeda"
}

def _field_value(record: dict[str, Any], *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value.get("value") if isinstance(value, dict) else value

def _normalize(value: Any) -> Any:
    return value.strip().lower() if isinstance(value, str) else value

def validate_reference(record: dict[str, Any], reference_path: str = "data/golden_records.csv") -> dict[str, Any]:
    """Compare issuer, ISIN and ticker with the golden reference CSV."""

    def get_message(check: Any = None, gr_value: str = None) -> str:
        if check is None:
            return "Nenhum valor correspondente encontrado no banco de dados."
        if check is False:
            return f"Valor divergente do banco de dados (esperado: {gr_value})."
        if check is True:
            return "Validado no banco de dados."

    basic_cols = ["emissor", "isin", "ticker"]
    reference = pd.read_csv(Path(reference_path), encoding="utf-8-sig", usecols=basic_cols)
    reference = reference.apply(lambda col: col.apply(_normalize))

    basic_info = {
        "emissor": _normalize(_field_value(record, "issuer")),
        "isin": _normalize(_field_value(record, "isin")),
        "ticker": _normalize(_field_value(record, "ticker"))
    }

    matches = reference[list(basic_info)] == pd.Series(basic_info)
    n_matches = matches.sum(axis=1)
    reference["n_matches"] = n_matches
    if n_matches.max() == 0:
        best_row = None
    else:
        best_row = reference.loc[reference["n_matches"].idxmax()]

    if best_row is None:
        return {
            "checks": {
                "issuer": False,
                "isin": False,
                "ticker": False
            },
            "messages": {
                "issuer": get_message(),
                "isin": get_message(),
                "ticker": get_message()
            }
        }

    return {
        "checks": {
            "issuer": best_row["emissor"] == basic_info["emissor"],
            "isin": best_row["isin"] == basic_info["isin"],
            "ticker": best_row["ticker"] == basic_info["ticker"]
        },
        "messages": {
            "issuer": get_message(best_row["emissor"] == basic_info["emissor"], best_row["emissor"]),
            "isin": get_message(best_row["isin"] == basic_info["isin"], best_row["isin"]),
            "ticker": get_message(best_row["ticker"] == basic_info["ticker"], best_row["ticker"])
        }
    }

def validate_dates(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the chronological order of dates in a corporate action record."""

    date_fields = ("approval_date", "record_date", "ex_date", "payment_date")
    date_formats = ("%d-%m-%Y", "%d/%m/%Y")
    parsed_dates: dict[str, datetime] = {}
    results = {
        "checks": {},
        "messages": {},
    }

    for field_name in date_fields:
        value = _field_value(record, "dates", field_name)
        if not value:
            continue

        parsed = None
        for format in date_formats:
            try:
                parsed = datetime.strptime(value, format)
                break
            except ValueError:
                continue

        if parsed is None:
            results["checks"][field_name] = False
            results["messages"][field_name] = "Formato de data inválido."
        else:
            parsed_dates[field_name] = parsed

    for earlier, later in combinations(date_fields, 2):
        if (
            earlier in parsed_dates
            and later in parsed_dates
            and parsed_dates[earlier] > parsed_dates[later]
        ):
            results["checks"][earlier] = False
            results["checks"][later] = False
            results["messages"][earlier] = f"{PTBR_NAMES[earlier]} deve ser anterior a {PTBR_NAMES[later]}."
            results["messages"][later] = f"{PTBR_NAMES[later]} deve ser posterior a {PTBR_NAMES[earlier]}."

    return results

def validate_monetary_values(record: dict[str, Any]) -> dict[str, Any]:
    """Validate gross and net monetary values from a corporate action record."""

    gross = _field_value(record, "monetary_details", "gross_value")
    net = _field_value(record, "monetary_details", "net_value")
    results = {
        "checks": {},
        "messages": {},
    }

    if gross is not None and net is not None:
        if float(net) > float(gross):
            results["checks"]["net_value"] = False
            results["messages"]["net_value"] = "O valor líquido não pode ser maior que o valor bruto."

    if gross is not None and float(gross) < 0:
        results["checks"]["gross_value"] = False
        results["messages"]["gross_value"] = "O valor bruto não pode ser negativo."
    if net is not None and float(net) < 0:
        results["checks"]["net_value"] = False
        results["messages"]["net_value"] = "O valor líquido não pode ser negativo."

    return results

def _append_rationale(field: dict[str, Any], message: str) -> None:
    current = field.get("rationale", "")
    field["rationale"] = f"{current} {message}".strip()

def _apply_validation_result(record: dict[str, Any], validation_result: dict[str, Any], field_map: dict[str, dict[str, Any]]) -> None:
    checks = validation_result.get("checks", {})
    messages = validation_result.get("messages", {})

    for field_name, check in checks.items():
        field = field_map.get(field_name)
        message = messages.get(field_name)

        if field is None or field.get("value") is None:
            continue

        if message:
            _append_rationale(field, message)

        if check is False:
            field["status"] = "validation_error"
            if field.get("confidence") is not None:
                field["confidence"] /= 3

            if message:
                record.setdefault("validation_notes", []).append(
                    f"{field_name}: {message}"
                )

def _field_confidences(value: Any):
    if isinstance(value, dict):
        if "value" in value and "confidence" in value:
            if value["value"] is not None and value["confidence"] is not None:
                yield value["confidence"]

        for child in value.values():
            yield from _field_confidences(child)

    elif isinstance(value, list):
        for child in value:
            yield from _field_confidences(child)

def _update_document_confidence(response: dict[str, Any]) -> None:
    confidences = list(_field_confidences(response["record"]))

    if not confidences:
        response["document_confidence"] = 0.0
        return

    response["document_confidence"] = round(sum(confidences) / len(confidences), 2)

def improve_response(response: dict[str, Any]) -> dict[str, Any]:
    """Run validations and enrich each affected extracted field."""

    reference_result = validate_reference(response["record"])
    dates_result = validate_dates(response["record"])
    monetary_result = validate_monetary_values(response["record"])

    reference_fields = {
        "issuer": response["record"]["issuer"],
        "isin": response["record"]["isin"],
        "ticker": response["record"]["ticker"],
    }
    date_fields = {
        field_name: response["record"]["dates"][field_name]
        for field_name in ("approval_date", "record_date", "ex_date", "payment_date")
    }
    monetary_fields = {
        field_name: response["record"]["monetary_details"][field_name]
        for field_name in ("gross_value", "net_value")
    }

    _apply_validation_result(response["record"], reference_result, reference_fields)
    _apply_validation_result(response["record"], dates_result, date_fields)
    _apply_validation_result(response["record"], monetary_result, monetary_fields)

    _update_document_confidence(response)

    return response

def get_exception_lines(document_name: str, response: dict) -> list[str]:
    """Format extraction and validation notes for the exceptions report."""

    lines = []
    extraction_notes = response["record"].get("extraction_notes", [])
    validation_notes = response["record"].get("validation_notes", [])

    if extraction_notes:
        lines.append(f"\n{document_name} | Problemas de Extração:")
        lines.extend(f"  - {note}" for note in extraction_notes)

    if validation_notes:
        lines.append(f"\n{document_name} | Problemas de Validação:")
        lines.extend(f"  - {note}" for note in validation_notes)

    return lines