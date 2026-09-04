from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from parcelco.paths import ROOT

load_dotenv(ROOT / ".env")


def llm_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")


def llm_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "lm-studio")


def chat_model(*, temperature: float = 0.2) -> ChatOpenAI:
    """Local Qwen (or any OpenAI-compatible model) via LM Studio."""
    return ChatOpenAI(
        model=os.getenv("PARCELCO_MODEL", "qwen3.8_4b_distilled_gguf"),
        api_key=llm_api_key(),
        base_url=llm_base_url(),
        temperature=temperature,
        max_tokens=1024,
    )


def embed_model() -> OpenAIEmbeddings:
    """LM Studio embeddings (nomic) — used for Chroma RAG."""
    return OpenAIEmbeddings(
        model=os.getenv("PARCELCO_EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5"),
        api_key=llm_api_key(),
        base_url=llm_base_url(),
    )
