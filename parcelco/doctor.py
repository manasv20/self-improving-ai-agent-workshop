"""Check the actual local inference and vector retrieval path, without fallback."""
from __future__ import annotations

from parcelco.llm import chat_model, embed_model, model_name


def check_setup() -> None:
    from parcelco.data_io import suite_info
    from parcelco.rag import _chroma_retrieve

    print(f"Chat model: {model_name()}")
    reply = chat_model().invoke("Reply with just: pong").content
    if not isinstance(reply, str) or "pong" not in reply.lower():
        raise RuntimeError(f"Unexpected chat response: {reply!r}")
    print(f"Chat OK: {reply.strip()}")
    vector = embed_model().embed_query("search_query: refund policy")
    if not vector:
        raise RuntimeError("Embedding server returned an empty vector")
    print(f"Embeddings OK: {len(vector)} dimensions")
    docs = _chroma_retrieve("What is the refund window?", k=4)
    if not docs:
        raise RuntimeError("Chroma retrieval failed; keyword fallback would hide this error")
    print(f"Chroma OK: retrieved {len(docs)} documents")
    print(f"Dataset: {suite_info()}")


if __name__ == "__main__":
    check_setup()
