"""Shared LLM factory for all agents.

Uses OpenRouter as an OpenAI-compatible API, so any provider's model
can be selected via the OPENROUTER_MODEL env var.
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client pointed at OpenRouter."""
    max_tokens = int(os.getenv("OPENROUTER_MAX_TOKENS", "700"))
    timeout_seconds = float(
        os.getenv("OPENROUTER_TIMEOUT_SECONDS", "90")
    )
    temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))
    return ChatOpenAI(
        model=os.getenv(
            "OPENROUTER_MODEL",
            "google/gemini-2.5-flash-lite",
        ),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout_seconds,
        max_retries=1,
    )
