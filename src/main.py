from __future__ import annotations

import argparse
import json
from pathlib import Path

from langchain_core.output_parsers import PydanticOutputParser

from agent import build_agent
from functions import improve_response, get_exception_lines
from schemas import ExtractionResponse


def process_document(agent: object, parser: PydanticOutputParser, pdf_path: Path) -> dict:
    """Extract, parse, validate, and enrich one PDF result."""

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

    return improve_response(structured_response.model_dump())

def get_pdf_list(docs_path: Path) -> list[Path]:
    """Return one PDF or all PDFs from the provided path."""

    if docs_path.is_file():
        if docs_path.suffix.lower() != ".pdf":
            raise ValueError("The path passed to --docs must be a PDF file or a directory containing PDF files.")
        return [docs_path]

    elif docs_path.is_dir():
        return sorted(
            path
            for path in docs_path.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        )

    else:
        raise FileNotFoundError(f"Documents path not found: {docs_path}")

def save_result(output_dir: Path, pdf_path: Path, result: dict) -> Path:
    """Save one processed document as JSON."""

    output_path = output_dir / f"{pdf_path.stem}.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=4, default=str),
        encoding="utf-8",
    )

    return output_path

def save_exceptions_report(output_dir: Path, exception_lines: list[str]) -> Path:
    """Save the accumulated extraction and validation exceptions."""

    exception_lines[0] = exception_lines[0].lstrip("\n")

    exceptions_path = output_dir / "excecoes.txt"
    exceptions_path.write_text(
        "\n".join(exception_lines),
        encoding="utf-8",
    )

    return exceptions_path

def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Extract and validate corporate action PDFs")
    argument_parser.add_argument("--docs", type=Path, default=Path("documents"))
    argument_parser.add_argument("--output", type=Path,default=Path("output"))
    args = argument_parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    agent = build_agent()
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)
    exception_lines = []

    pdf_list = get_pdf_list(args.docs)

    for pdf_path in pdf_list:
        try:
            result = process_document(agent, parser, pdf_path)
            exception_lines.extend(get_exception_lines(pdf_path.name, result))

        except Exception as exc:
            result = {
                "document": pdf_path.name,
                "record": None,
                "error": str(exc),
            }
            exception_lines.append(
                f"\n{pdf_path.name} | Erro de processamento:\n  - {exc}"
            )

        output_path = save_result(args.output, pdf_path, result)
        print(f"Result saved to {output_path}")

    exceptions_path = save_exceptions_report(args.output, exception_lines)
    print(f"Exceptions report saved to {exceptions_path}")

if __name__ == "__main__":
    main()