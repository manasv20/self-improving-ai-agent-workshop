# Get ready for the workshop

[Visual guide](index.html#setup) · [Exercises](WORKSHOP.md) · [README](../README.md)

You can follow the discussion and paper exercises without installing anything. To run the agent yourself, prepare this before the session; model downloads and Python dependencies can take time.

## 1. Get the project

You'll need Git, Python **3.11 or newer**, and LM Studio with a local chat model. Docker is optional and only needed for self-hosted Langfuse.

```bash
git clone https://github.com/manasv20/self-improving-ai-agent-workshop.git
cd self-improving-ai-agent-workshop
python3 --version
python3 -m venv .venv
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` instead. If your Python launcher is `py`, use `py -3` in place of `python3` when creating the environment.

```bash
python -m pip install -e .
python -c "from pathlib import Path; p=Path('.env'); p.exists() or p.write_text(Path('.env.example').read_text())"
```

The last command creates `.env` only if it is missing. Keep that file local. All later commands run from the folder containing `pyproject.toml`.

## 2. Connect a local model

In LM Studio, download and load a Qwen chat model that fits your machine. A tested Apple-silicon profile is **Qwen3.5-4B GGUF Q4_K_M** with **Nomic Embed Text v1.5 GGUF Q4_K_M** for retrieval. This is a useful starting point for a 16 GB Mac; other local models and hardware can work when their API identifiers are configured correctly.

The model files are available from the [Qwen3.5 GGUF repository](https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF) and the [Nomic embedding repository](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF). LM Studio's bundled `lms` command can download them:

```bash
lms get https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF@Q4_K_M --gguf -y
lms get https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF@Q4_K_M --gguf -y
```

Load the chat model and embedding model in LM Studio, then start the local server from its Developer tab. The workshop expects `http://127.0.0.1:1234/v1` unless you configure another address. You can start the server from a terminal with `lms server start --port 1234` when the bundled CLI is available.

Open <http://127.0.0.1:1234/v1/models> and copy your chat model's `id`. **A model's display name is not necessarily its API identifier.** Replace the example identifier in `.env`:

```dotenv
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
PARCELCO_MODEL=qwen3.5-4b
PARCELCO_EMBED_MODEL=text-embedding-nomic-embed-text-v1.5
PARCELCO_SUITE=demo
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

`qwen3.5-4b` is the tested chat-model identifier for the profile above. If LM Studio shows a different ID, use the exact value returned by its API. `lm-studio` is a placeholder for a local server without authentication; use your local server token if authentication is enabled. Leave both Langfuse keys empty for the first run.

Optional: load an embedding model and set `PARCELCO_EMBED_MODEL` to its API identifier. Embeddings turn text into numeric vectors for retrieval. If embeddings or Chroma are unavailable, this repo falls back to keyword matching; the chat model is still required.

For server details, see the official [LM Studio local server guide](https://lmstudio.ai/docs/developer/core/server) and [OpenAI-compatible endpoints](https://lmstudio.ai/docs/developer/openai-compat).

## 3. Check before opening the dashboard

```bash
python -m unittest discover -s tests -v
python -c "from parcelco.llm import chat_model; print(chat_model().invoke('Reply with pong.').content)"
```

The tests should pass without a model. The second command should return a short model reply; it need not be exactly `pong`. If it raises an error, use the table below before starting a suite.

```bash
python -m parcelco.cli serve --suite demo
```

Open <http://127.0.0.1:5050>. Confirm the terminal reports **28A / 19B**, pick **A01**, and click **Run this ticket**. A completed run shows a reply and a checklist result, even when it fails.

## 4. Open the reference page

Double-click `docs/index.html`. It has no external fonts, scripts, or model dependency. For a local HTTP preview, open a second terminal in the repo and run:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Then open <http://127.0.0.1:8000>. This serves the guide, not the agent. Stop each server in its own terminal with **Ctrl+C**.

## If something gets stuck

| Symptom | Try this |
|---|---|
| `python3` is missing or older than 3.11 | Install a supported Python version, then recreate the environment. |
| `No module named parcelco` | Activate `.venv`, return to the repo folder, and rerun `python -m pip install -e .`. |
| Connection refused on port 1234 | Start LM Studio's server and check `OPENAI_BASE_URL`. |
| Model not found | Copy the chat model's exact API `id` into `PARCELCO_MODEL`, load it, and restart ParcelCo. |
| Embeddings fail | Continue with the keyword fallback, or load the embedding model and check its identifier. |
| Dashboard port is busy | Run `python -m parcelco.cli serve --suite demo --port 5051` and use port 5051 in the browser. |
| Tracing errors or long waits with no Langfuse server | Empty both Langfuse keys and restart ParcelCo. |
| A suite takes too long | Use `demo`, run one ticket at a time, and use the guide's scoring exercise while waiting. |
| Scores look different from an earlier run | Check model, suite, heal limit, and saved memory. Local generation can vary even with the same settings. |

## Starting fresh for a rehearsal

This checkout includes lessons from earlier demos. **Reset memory** (or the command below) replaces the prompt and learnings with built-in defaults and clears local round/event history. Copy `parcelco/memory/system_prompt.md`, `learnings.md`, and `rounds.sqlite` somewhere safe first if you want to keep them.

```bash
python -m parcelco.cli reset
```

Reset does not remove the retrieval index or remote Langfuse traces. Stop a running job before resetting. Interrupting a batch Learn run can leave provisional memory on disk; inspect or reset it before comparing another run. The app does not promise transactional rollback after interruption.

## Settings you may discuss in the workshop

| Setting | Default in code | Meaning |
|---|---|---|
| `PARCELCO_MAX_HEAL` | `2` | At most two retries after the initial draft: three drafts total. |
| `PARCELCO_MAX_OUTER_ROUNDS` | `5` | Batch rounds when no explicit round count is supplied. Use one live. |
| `PARCELCO_MIN_DELTA` | `0.05` | Required learn-set gain: five percentage points. |
| `PARCELCO_PART_B_TOLERANCE` | `0.05` | Allowed holdout drop: five percentage points. |
| `PARCELCO_SUITE` | `full` | Use `--suite demo` explicitly for the live session. |

Restart the app after changing `.env`. For an embeddings/policy change, stop the app and rebuild the index in a fresh process with `python -c "from parcelco.rag import rebuild_index; print(rebuild_index())"`. This replaces the local Chroma index; inspect the returned status to see whether indexing worked or keyword fallback is active.
