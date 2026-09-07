from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from agent import build_agent
from schemas import CorporateAction, ExtractionResponse
from functions import improve_response


if __name__ == "__main__":
    agent = build_agent()
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)

    pdf_path = Path("documents/07_telecom_norte_jcp_SCAN.pdf")

    print(f"Agent is processing the PDF: {pdf_path.resolve()}")
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
    structured_response = parser.parse(final_message.content)
    response_dict = structured_response.model_dump()

    result = improve_response(response_dict)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{pdf_path.stem}.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=4, default=str),
        encoding="utf-8",
    )

    print(f"Result saved to {output_path}")

    exceptions_path = output_dir / "excecoes.txt"
    exception_lines = []

    extraction_notes = result["record"].get("extraction_notes", [])
    validation_notes = result["record"].get("validation_notes", [])

    if extraction_notes:
        exception_lines.append(f"\n{pdf_path.name} | Problemas de Extração:")
        for note in extraction_notes:
            exception_lines.append(f"  - {note}")

    if validation_notes:
        exception_lines.append(f"\n{pdf_path.name} | Problemas de Validação:")
        for note in validation_notes:
            exception_lines.append(f"  - {note}")

    if len(exception_lines) == 0:
        exception_lines.append(f"Nenhum problema encontrado.")

    exceptions_path.write_text("\n".join(exception_lines), encoding="utf-8")

    print(f"Exceptions report saved to {exceptions_path}")