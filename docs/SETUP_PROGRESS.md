# Qwen 3.5 local setup progress

Requested setup: LM Studio, Qwen3.5-4B, embeddings, runnable workshop,
documentation audit, and a pull request.

## Inspection

- Machine: Apple M4, 16 GB unified memory. Chose Qwen3.5-4B GGUF Q4_K_M for
  the verified LM Studio setup; MLX remains an optional Apple-silicon format.
- Git checkout was clean; working branch: `setup/qwen35-local-workshop`.
- LM Studio CLI existed but its application was missing. Installing the app.
- Creating a Python 3.12 virtual environment and installing the project.
- Existing model default was a stale custom identifier.
- Example environment enables optional Langfuse using demo credentials even
  when its server is absent; local setup should leave tracing disabled.
- Some setup paths and dataset counts in the docs are stale.

## Installation and fixes

- Installed LM Studio 0.4.23 (Apple silicon) and its current runtimes.
- Installed the project into `.venv` using Python 3.12.6.
- Loaded Nomic Embed Text v1.5 GGUF Q4_K_M (84 MB).
- Started LM Studio's API on localhost port 1234.
- Configured a gitignored `.env` for Qwen3.5-4B, demo suite, and optional tracing off.
- Centralized the Qwen3.5 model ID; corrected embedding text transport and Nomic
  task prefixes. The v2 Chroma collection avoids reusing unprefixed vectors.
- Added `python -m parcelco.doctor` to check real inference and vector retrieval.
- Corrected checkout paths, dataset sizes, and the distinction between immediate
  single-ticket reflection and suite-gated CLI improvement.
- The LM Studio catalog download reported checksum failures. Downloaded the
  Qwen3.5-4B GGUF Q4_K_M file directly, verified its SHA-256 against the
  Hugging Face digest (`25082a7dd3776cc3c741c6347d3bd04523f05796607b3fbc32fa3a25dfa1418c`),
  imported it into LM Studio, and loaded it as `qwen3.5-4b`.
- The MLX weights were also downloaded and independently hash-verified, but
  LM Studio did not index that directory reliably, so GGUF is the documented
  choice for this laptop setup.
- Added the missing optional Langfuse Docker environment template and made the
  startup script copy it only when absent. All service ports bind to localhost.
- Added a live verification script that isolates learning/history in temporary
  files so running it does not pre-complete the student's exercises.

## Verification

- 15 unit tests pass, including an HTTP transport test for embedding strings.
- Nomic API returns 768-dimensional vectors; Chroma retrieves the refund FAQ.
- Flask dashboard and knowledge endpoints return HTTP 200.
- All 120 installed Python packages pass `uv pip check`.
- Optional Langfuse Compose configuration validates against its example environment;
  the Docker services have not been started as part of this local model setup.
- Qwen chat inference passes: `pong`; LM Studio exposes `qwen3.5-4b` on port 1234.
- Live demo verification completed: round 0 Part A `82.1%`, Part B `89.5%`;
  round 1 Part A `89.3%`, Part B `89.5%`; both rounds were kept by the lesson gate.
  Remaining failures are model-quality cases (wrong action or forbidden wording),
  not connection, embedding, or fallback errors.
- Final audit and PR are the remaining delivery steps.

## Sources

- [LM Studio CLI](https://github.com/lmstudio-ai/lms)
- [Qwen3.5-4B model card](https://huggingface.co/Qwen/Qwen3.5-4B)
- [LM Studio MLX conversion](https://huggingface.co/lmstudio-community/Qwen3.5-4B-MLX-4bit)
