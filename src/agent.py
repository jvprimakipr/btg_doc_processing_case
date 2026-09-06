from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from prompts import build_system_prompt
from schemas import ExtractionResponse
from tools import read_pdf_with_pymupdf, read_pdf_with_tesseract

load_dotenv()


LLM_PROVIDERS = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL"),
        "function": ChatOpenAI,
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("ANTHROPIC_MODEL"),
        "function": ChatAnthropic,
    },
    "google": {
        "api_key": os.getenv("GOOGLE_API_KEY"),
        "model": os.getenv("GOOGLE_MODEL"),
        "function": ChatGoogleGenerativeAI,
    },
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": os.getenv("GROQ_MODEL"),
        "function": ChatGroq,
    },
}

DEFAULT_LLM_PROVIDER_ID = os.getenv("DEFAULT_LLM_PROVIDER", "groq")

def build_agent(llm_provider_id: str | None = None) -> Any:
    """Create the corporate-action extraction agent."""

    provider_id = llm_provider_id or DEFAULT_LLM_PROVIDER_ID
    provider = LLM_PROVIDERS.get(provider_id)

    if provider is None:
        raise ValueError(f"Unsupported provider: {provider_id}")
    if not provider["api_key"]:
        raise RuntimeError(f"API key is not configured for {provider_id}")
    if not provider["model"]:
        raise RuntimeError(f"Model is not configured for {provider_id}")

    llm = provider["function"](
        api_key=provider["api_key"],
        model=provider["model"],
        temperature=0,
    )
    parser = PydanticOutputParser(pydantic_object=ExtractionResponse)
    tools = [read_pdf_with_pymupdf, read_pdf_with_tesseract]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=build_system_prompt(parser.get_format_instructions()),
    )