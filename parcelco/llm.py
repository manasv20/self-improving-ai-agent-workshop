from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from parcelco.paths import ROOT

load_dotenv(ROOT / ".env")


def model_name() -> str:
    return os.getenv("PARCELCO_MODEL", "qwen3.5-4b")


def eval_model_name() -> str:
    """Optional tiny SLM used only for soft evaluation (not generation)."""
    return os.getenv("PARCELCO_EVAL_MODEL", "").strip()


def embedding_model_name() -> str:
    return os.getenv("PARCELCO_EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")


def llm_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")


def llm_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "lm-studio")


def chat_model(*, temperature: float = 0.2, model: str | None = None) -> ChatOpenAI:
    """Local Qwen (or any OpenAI-compatible model) via LM Studio."""
    reasoning = os.getenv("PARCELCO_REASONING_EFFORT", "none").strip()
    return ChatOpenAI(
        model=model or model_name(),
        api_key=llm_api_key(),
        base_url=llm_base_url(),
        temperature=temperature,
        max_tokens=1024,
        timeout=120,
        max_retries=1,
        **({"reasoning_effort": reasoning} if reasoning else {}),
    )


def eval_chat_model(*, temperature: float = 0.0) -> ChatOpenAI:
    """Small local judge model — short JSON verdicts only."""
    name = eval_model_name()
    if not name:
        raise RuntimeError("PARCELCO_EVAL_MODEL is not set")
    reasoning = os.getenv("PARCELCO_EVAL_REASONING_EFFORT", "none").strip()
    return ChatOpenAI(
        model=name,
        api_key=llm_api_key(),
        base_url=llm_base_url(),
        temperature=temperature,
        max_tokens=384,
        timeout=60,
        max_retries=1,
        **({"reasoning_effort": reasoning} if reasoning else {}),
    )


def embed_model() -> OpenAIEmbeddings:
    """LM Studio embeddings (nomic) — used for Chroma RAG."""
    return OpenAIEmbeddings(
        model=embedding_model_name(),
        api_key=llm_api_key(),
        base_url=llm_base_url(),
        # Local embedding servers expect text, not OpenAI/tiktoken token IDs.
        check_embedding_ctx_length=False,
        timeout=30,
        max_retries=0,
    )
