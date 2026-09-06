from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from agent import build_agent
from schemas import CorporateAction, ExtractionResponse
from tools import validate_dates, validate_monetary_values, validate_reference

def as_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump()

if __name__ == "__main__":
    agent = build_agent()
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)

    pdf_path = Path("documents/07_telecom_norte_jcp_SCAN.pdf")

    response = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Process this PDF and extract the corporate action: "
                    f"{pdf_path.resolve()}"
                ),
            }
        ]
    })

    final_message = response["messages"][-1]
    final_content = final_message.content
    structured_response = parser.parse(final_content)

    # record_dict = structured_response.record.model_dump()

    # reference_result = validate_reference.invoke({
    #     "record": record_dict
    # })

    # dates_result = validate_dates.invoke({
    #     "record": record_dict
    # })

    # monetary_result = validate_monetary_values.invoke({
    #     "record": record_dict
    # })

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "document": pdf_path.name,
        "record": structured_response.model_dump(),
        # "validation": {
        #     "reference": reference_result,
        #     "dates": dates_result,
        #     "monetary_values": monetary_result,
        # },
    }

    output_path = output_dir / f"{pdf_path.stem}.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Result saved to {output_path}")