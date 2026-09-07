"""Participant-friendly preflight checks for the local ParcelCo workshop.

Run ``python -m parcelco.doctor`` for the normal participant check. Facilitators
who require vector retrieval can add ``--strict-embeddings``.
"""

from __future__ import annotations

import argparse
import platform
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from parcelco.llm import embedding_model_name, llm_base_url, model_name

Status = Literal["PASS", "WARN", "FAIL"]


@dataclass(frozen=True)
class Diagnostic:
    """One short, user-facing preflight result."""

    status: Status
    check: str
    message: str

    def render(self) -> str:
        return f"{self.status} {self.check}: {self.message}"


@dataclass(frozen=True)
class DoctorSettings:
    """Displayed configuration, separated so tests need no environment changes."""

    python_version: str
    chat_model: str
    embedding_model: str
    base_url: str


@dataclass(frozen=True)
class DoctorProbes:
    """External operations used by the doctor.

    Keeping these operations injectable makes every error path testable without
    starting LM Studio or creating a Chroma database.
    """

    chat_reply: Callable[[], object]
    embedding_vector: Callable[[], object]
    vector_documents: Callable[[], object]
    keyword_documents: Callable[[], object]
    dataset_info: Callable[[], dict[str, int | str]]


@dataclass(frozen=True)
class DoctorReport:
    diagnostics: tuple[Diagnostic, ...]
    ready: bool
    retrieval_mode: Literal["vector", "keyword", "unavailable"]

    @property
    def exit_code(self) -> int:
        return 0 if self.ready else 1

    def render(self) -> str:
        lines = [item.render() for item in self.diagnostics]
        if self.ready:
            mode = (
                "Chat and vector retrieval are working."
                if self.retrieval_mode == "vector"
                else "Chat is working; keyword retrieval fallback is confirmed."
            )
            lines.extend([mode, "Ready for the workshop."])
        else:
            lines.append(
                "Not ready: fix the FAIL items above, then run the doctor again."
            )
        return "\n".join(lines)


def current_settings() -> DoctorSettings:
    return DoctorSettings(
        python_version=platform.python_version(),
        chat_model=model_name(),
        embedding_model=embedding_model_name(),
        base_url=llm_base_url(),
    )


def default_probes() -> DoctorProbes:
    """Build the real local-service probes lazily."""
    from parcelco.data_io import suite_info
    from parcelco.llm import chat_model, embed_model
    from parcelco.rag import _chroma_retrieve, _keyword_retrieve

    def chat_reply() -> object:
        return chat_model().invoke("Reply with just: pong").content

    def embedding_vector() -> object:
        return embed_model().embed_query("search_query: refund policy")

    def vector_documents() -> object:
        return _chroma_retrieve("What is the refund window?", k=4, raise_errors=True)

    def keyword_documents() -> object:
        return _keyword_retrieve("What is the refund window?", k=4)

    return DoctorProbes(
        chat_reply=chat_reply,
        embedding_vector=embedding_vector,
        vector_documents=vector_documents,
        keyword_documents=keyword_documents,
        dataset_info=suite_info,
    )


def _exception_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def _brief_exception(exc: BaseException) -> str:
    """Return useful exception context without ever printing a traceback."""
    chain = _exception_chain(exc)
    detail = str(chain[-1] if chain else exc).strip()
    detail = re.sub(r"\s+", " ", detail)
    if len(detail) > 160:
        detail = detail[:157].rstrip() + "..."
    name = type(chain[-1] if chain else exc).__name__
    return f"{name}: {detail}" if detail else name


def _error_fingerprint(exc: BaseException) -> tuple[str, set[int]]:
    chain = _exception_chain(exc)
    text = " ".join(f"{type(item).__name__} {item}" for item in chain).lower()
    codes = {
        code
        for item in chain
        for code in [getattr(item, "status_code", None)]
        if isinstance(code, int)
    }
    return text, codes


def _service_error(
    exc: BaseException,
    *,
    service: Literal["chat", "embedding"],
    settings: DoctorSettings,
) -> str:
    text, codes = _error_fingerprint(exc)
    label = "Chat" if service == "chat" else "Embedding"
    env_name = "PARCELCO_MODEL" if service == "chat" else "PARCELCO_EMBED_MODEL"
    selected_model = (
        settings.chat_model if service == "chat" else settings.embedding_model
    )

    connection_terms = (
        "connection refused",
        "connection reset",
        "connecterror",
        "connectionreseterror",
        "apiconnectionerror",
        "connection error",
        "could not connect",
        "all connection attempts failed",
        "failed to establish",
        "name or service not known",
        "nodename nor servname",
    )
    timeout_terms = ("timeout", "timed out", "apitimeouterror")
    model_terms = (
        "model not found",
        "model_not_found",
        "unknown model",
        "no model loaded",
        "invalid model",
        "does not exist",
    )
    model_missing = any(term in text for term in model_terms) or bool(
        re.search(
            r"(?:model.{0,120}(?:not found|not available|unknown)|"
            r"(?:not found|not available|unknown).{0,120}model)",
            text,
        )
    )

    if any(term in text for term in connection_terms):
        action = (
            f"cannot reach LM Studio at {settings.base_url}. Start the local server "
            "and verify OPENAI_BASE_URL"
        )
    elif any(term in text for term in timeout_terms):
        action = (
            f"timed out contacting {settings.base_url}. Check that LM Studio is "
            f"running and that the {label.lower()} model is responsive"
        )
    elif model_missing:
        action = (
            f"model {selected_model!r} is not available. Load it in LM Studio and "
            f"set {env_name} to its exact API id from {settings.base_url}/models"
        )
    elif codes & {401, 403} or "authentication" in text or "unauthorized" in text:
        action = "authentication failed. Check OPENAI_API_KEY for the local server"
    elif 404 in codes or "not found" in text:
        action = (
            f"endpoint was not found at {settings.base_url}. Check OPENAI_BASE_URL "
            "(it normally ends in /v1)"
        )
    else:
        action = (
            f"request failed. Verify {env_name}, confirm the model is loaded in "
            "LM Studio, and retry"
        )
    return f"{action} ({_brief_exception(exc)})"


def _chroma_error(exc: BaseException) -> str:
    text, _ = _error_fingerprint(exc)
    if "modulenotfounderror" in text or "no module named" in text:
        action = "Chroma is not installed; run `python -m pip install -e .`"
    elif any(term in text for term in ("permission denied", "readonly", "read-only")):
        action = (
            "Chroma cannot write its index; check permissions on parcelco/data/chroma"
        )
    elif "locked" in text:
        action = "the Chroma index is locked; stop other ParcelCo processes and retry"
    elif any(
        term in text for term in ("dimension", "dimensionality", "embedding size")
    ):
        action = (
            "the stored index does not match this embedding model; rebuild it with "
            '`python -c "from parcelco.rag import rebuild_index; '
            'print(rebuild_index())"`'
        )
    else:
        action = (
            "Chroma retrieval failed; retry the index rebuild command from the local "
            "setup guide"
        )
    return f"{action} ({_brief_exception(exc)})"


def _item_count(value: object, *, label: str) -> int:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise RuntimeError(f"{label} returned no results")
    return len(value)


def _dataset_message(info: dict[str, int | str]) -> str:
    return (
        f"mode={info['mode']}; active={int(info['active_total']):,} "
        f"(improve={int(info['active_improve']):,}, "
        f"holdout={int(info['active_holdout']):,}); "
        f"catalog={int(info['catalog_total']):,} "
        f"(improve={int(info['catalog_improve']):,}, "
        f"holdout={int(info['catalog_holdout']):,})"
    )


def run_doctor(
    *,
    strict_embeddings: bool = False,
    settings: DoctorSettings | None = None,
    probes: DoctorProbes | None = None,
) -> DoctorReport:
    """Run all checks and return structured results without printing exceptions."""
    settings = settings or current_settings()
    probes = probes or default_probes()
    diagnostics: list[Diagnostic] = []

    try:
        parts = tuple(int(part) for part in settings.python_version.split(".")[:2])
    except ValueError:
        parts = (0, 0)
    if parts >= (3, 11):
        diagnostics.append(
            Diagnostic("PASS", "Python", f"{settings.python_version} (3.11+ supported)")
        )
    else:
        diagnostics.append(
            Diagnostic(
                "FAIL",
                "Python",
                f"{settings.python_version}; install Python 3.11 or newer and "
                "recreate the virtual environment",
            )
        )

    diagnostics.append(
        Diagnostic(
            "PASS",
            "Configuration",
            f"chat={settings.chat_model}; embeddings={settings.embedding_model}; "
            f"base_url={settings.base_url}",
        )
    )

    try:
        diagnostics.append(
            Diagnostic("PASS", "Dataset", _dataset_message(probes.dataset_info()))
        )
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                "FAIL",
                "Dataset",
                "could not load bundled tickets; reinstall from the repository root "
                f"({_brief_exception(exc)})",
            )
        )

    chat_ok = False
    try:
        reply = probes.chat_reply()
        if not isinstance(reply, str) or "pong" not in reply.lower():
            raise RuntimeError(f"unexpected reply {reply!r}")
        chat_ok = True
        diagnostics.append(
            Diagnostic(
                "PASS", "Chat model", f"{settings.chat_model!r} replied with pong"
            )
        )
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                "FAIL",
                "Chat model",
                _service_error(exc, service="chat", settings=settings),
            )
        )

    vector_status: Status = "FAIL" if strict_embeddings else "WARN"
    embedding_ok = False
    try:
        vector = probes.embedding_vector()
        dimensions = _item_count(vector, label="embedding server")
        embedding_ok = True
        diagnostics.append(
            Diagnostic(
                "PASS",
                "Embeddings",
                f"{settings.embedding_model!r} returned {dimensions:,} dimensions",
            )
        )
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                vector_status,
                "Embeddings",
                _service_error(exc, service="embedding", settings=settings),
            )
        )

    vector_ok = False
    if embedding_ok:
        try:
            document_count = _item_count(
                probes.vector_documents(), label="Chroma retrieval"
            )
            vector_ok = True
            diagnostics.append(
                Diagnostic(
                    "PASS",
                    "Chroma",
                    f"retrieved {document_count} policy/FAQ documents with vectors",
                )
            )
        except Exception as exc:
            diagnostics.append(Diagnostic(vector_status, "Chroma", _chroma_error(exc)))
    else:
        diagnostics.append(
            Diagnostic(
                vector_status,
                "Chroma",
                "skipped because embeddings are unavailable",
            )
        )

    keyword_ok = False
    if not vector_ok:
        try:
            document_count = _item_count(
                probes.keyword_documents(), label="keyword retrieval"
            )
            keyword_ok = True
            diagnostics.append(
                Diagnostic(
                    "PASS",
                    "Keyword fallback",
                    f"confirmed; retrieved {document_count} policy/FAQ documents "
                    "without embeddings",
                )
            )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    "FAIL",
                    "Keyword fallback",
                    "could not retrieve bundled policy/FAQ documents "
                    f"({_brief_exception(exc)})",
                )
            )

    ready = not any(item.status == "FAIL" for item in diagnostics)
    mode: Literal["vector", "keyword", "unavailable"] = (
        "vector" if vector_ok else "keyword" if keyword_ok else "unavailable"
    )
    # A future change to diagnostic severity should never make chat optional.
    ready = ready and chat_ok
    return DoctorReport(tuple(diagnostics), ready, mode)


def check_setup(
    *,
    strict_embeddings: bool = False,
    settings: DoctorSettings | None = None,
    probes: DoctorProbes | None = None,
) -> DoctorReport:
    """Run and print preflight checks; retained as the importable entry point."""
    report = run_doctor(
        strict_embeddings=strict_embeddings, settings=settings, probes=probes
    )
    print(report.render())
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check ParcelCo's local chat model and retrieval setup."
    )
    parser.add_argument(
        "--strict-embeddings",
        action="store_true",
        help=(
            "treat embedding or Chroma failures as fatal (recommended for facilitators)"
        ),
    )
    args = parser.parse_args(argv)
    return check_setup(strict_embeddings=args.strict_embeddings).exit_code


if __name__ == "__main__":
    raise SystemExit(main())
