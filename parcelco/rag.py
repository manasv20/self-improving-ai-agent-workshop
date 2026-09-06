"""RAG over ParcelCo policy + FAQ.

Uses Chroma + LM Studio embeddings when available; falls back to keyword overlap
so the workshop still runs if embeddings are unloaded.
"""

from __future__ import annotations

import re
from functools import lru_cache

from parcelco.paths import CHROMA_DIR, FAQ_DIR, POLICY_PATH

# v2 indexes Nomic documents with the required task prefix.
_COLLECTION = "parcelco_faq_v2"


def _embedding_text(text: str, *, query: bool, model: str) -> str:
    if "nomic-embed-text" in model.lower():
        return f"{'search_query' if query else 'search_document'}: {text}"
    return text


def _load_docs() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    if POLICY_PATH.exists():
        docs.append(("policy.md", POLICY_PATH.read_text()))
    for path in sorted(FAQ_DIR.glob("*.md")):
        docs.append((path.name, path.read_text()))
    return docs


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _keyword_retrieve(query: str, k: int = 4) -> list[str]:
    q = _tokenize(query)
    scored: list[tuple[float, str]] = []
    for name, body in _load_docs():
        overlap = len(q & _tokenize(body))
        # light boost for policy
        score = overlap + (0.5 if name == "policy.md" else 0.0)
        scored.append((score, f"[{name}]\n{body.strip()}"))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in scored[:k] if score > 0] or [
        f"[{name}]\n{body.strip()}" for name, body in _load_docs()[:k]
    ]


def _chroma_retrieve(query: str, k: int = 4) -> list[str] | None:
    try:
        import chromadb
        from parcelco.llm import embed_model

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        emb = embed_model()
        collection = client.get_or_create_collection(_COLLECTION)

        if collection.count() == 0:
            docs = _load_docs()
            texts = [body for _, body in docs]
            ids = [name for name, _ in docs]
            vectors = emb.embed_documents([
                _embedding_text(text, query=False, model=emb.model) for text in texts
            ])
            collection.add(ids=ids, documents=texts, embeddings=vectors)

        qvec = emb.embed_query(_embedding_text(query, query=True, model=emb.model))
        result = collection.query(query_embeddings=[qvec], n_results=k)
        docs = (result.get("documents") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]
        return [f"[{i}]\n{d}" for i, d in zip(ids, docs)]
    except Exception:
        return None


@lru_cache(maxsize=1)
def rebuild_index() -> str:
    """Force rebuild chroma index; returns status string."""
    try:
        import chromadb
        from parcelco.llm import embed_model

        if CHROMA_DIR.exists():
            import shutil

            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        emb = embed_model()
        collection = client.get_or_create_collection(_COLLECTION)
        docs = _load_docs()
        texts = [body for _, body in docs]
        ids = [name for name, _ in docs]
        vectors = emb.embed_documents([
            _embedding_text(text, query=False, model=emb.model) for text in texts
        ])
        collection.add(ids=ids, documents=texts, embeddings=vectors)
        return f"indexed {len(docs)} docs in chroma"
    except Exception as e:
        return f"chroma unavailable ({e}); using keyword RAG"


def retrieve(query: str, k: int = 4) -> list[str]:
    chunks = _chroma_retrieve(query, k=k)
    if chunks:
        return chunks
    return _keyword_retrieve(query, k=k)
