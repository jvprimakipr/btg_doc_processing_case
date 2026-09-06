from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel

from schemas import CorporateAction, ExtractionResponse
from tools import (read_pdf_with_pymupdf, read_pdf_with_tesseract,
                   validate_dates, validate_monetary_values,
                   validate_reference)

load_dotenv()

llm_providers = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL"),
        "function": ChatOpenAI
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("ANTHROPIC_MODEL"),
        "function": ChatAnthropic
    },
    "google": {
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "model": os.getenv("GOOGLE_MODEL"),
        "function": ChatGoogleGenerativeAI
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": os.getenv("GROQ_MODEL"),
        "function": ChatGroq
    }
}

default_llm_provider_id = os.getenv("DEFAULT_LLM_PROVIDER")

def as_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump()

def build_agent(llm_provider_id: str = default_llm_provider_id) -> Any:
    """Create the corporate-action extraction agent."""

    provider = llm_providers.get(llm_provider_id)

    if provider is None:
        raise ValueError(f"Unsupported provider: {llm_provider_id}")
    if not provider["api_key"]:
        raise RuntimeError(
            f"API key is not configured for {llm_provider_id}"
        )

    llm = provider["function"](model = provider["model"], temperature = 0)
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)

    tools = [
        read_pdf_with_pymupdf,
        read_pdf_with_tesseract
    ]

    return create_agent(
        model = llm,
        tools = tools,
        system_prompt = f"""You are a Brazilian corporate action extraction agent.
Process the PDF path provided by the user.
First call both PDF reading tools and compare their outputs.
Extract only information explicitly supported by the documents; never invent values.
Use null for missing or unreadable values.
Dates must use the DD-MM-YYYY format.
Some of the event types are: dividend, interest on capital, stock split, reverse stock split, merger, spin-off, rights issue, tender offer.
The output values must be in portuguese.
Return only JSON following this schema:
{parser.get_format_instructions()}""",
    )

if __name__ == "__main__":
    agent = build_agent()
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)

    pdf_path = Path("documents/01_energetica_vale_tiete_dividendo.pdf")

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

    record_dict = structured_response.record.model_dump()

    reference_result = validate_reference.invoke({
        "record": record_dict
    })

    dates_result = validate_dates.invoke({
        "record": record_dict
    })

    monetary_result = validate_monetary_values.invoke({
        "record": record_dict
    })

    print(structured_response)
    print(structured_response.model_dump())