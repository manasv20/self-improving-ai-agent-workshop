# Set up the workshop

[Prework checklist](PREWORK.md) · [Visual guide](index.html) · [Exercises](WORKSHOP.md) · [README](../README.md)

This is the only full setup guide for the repository. Use the short [prework checklist](PREWORK.md) to confirm readiness; return here for installation, restarts, alternate ports, and troubleshooting.

You can take either route:

- **Local-model route:** install Python and LM Studio, then run the ParcelCo dashboard.
- **Offline/no-model route:** use the visual guide, sample replies, checklist exercise, and gate graph. The live dashboard cannot generate ticket replies without a chat model.

## Before you begin

Allow 30–60 minutes and finish setup before the event. Model download time depends on the network. The known-good profile is an Apple-silicon Mac with 16 GB memory running Qwen3.5-4B GGUF Q4_K_M. LM Studio recommends 16 GB memory on supported macOS, Windows, and Linux systems; smaller or CPU-only systems may be slower. Check [LM Studio's current system requirements](https://lmstudio.ai/docs/app/system-requirements) for OS, CPU, and GPU details.

Plan for:

- Git and Python **3.11 or newer**.
- LM Studio and a local chat model for the live route. Docker is not required.
- At least about **3 GB** for the Qwen chat model, about **0.1 GB** for the optional Nomic embedding model, and about **0.5 GB** for the Python environment. Keep at least **8 GB free**; **10 GB or more** is safer for download caches and temporary files.
- Local ports **1234** (LM Studio), **5050** (dashboard), and optionally **8000** (visual guide server).

## 1. Clone the project and install Python dependencies

Run all later commands from the checkout containing `pyproject.toml`.

### macOS or Linux — Bash

```bash
git clone https://github.com/manasv20/self-improving-ai-agent-workshop.git
cd self-improving-ai-agent-workshop
ls pyproject.toml
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -c requirements-lock.txt -e .
if [[ ! -f .env ]]; then cp .env.example .env; fi
```

`ls pyproject.toml` must print the filename. If it does not, change into the actual repository folder before creating the environment. A nested download can otherwise produce `does not appear to be a Python project`.

### Windows — PowerShell

```powershell
git clone https://github.com/manasv20/self-improving-ai-agent-workshop.git
Set-Location self-improving-ai-agent-workshop
Get-Item pyproject.toml
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -c requirements-lock.txt -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`Get-Item pyproject.toml` must display the file. If PowerShell blocks activation, allow scripts only for the current terminal and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The `.env` copy commands preserve an existing file. Keep `.env` local; do not commit credentials or tokens.

## 2. Install and prepare LM Studio

Install the current [LM Studio desktop app](https://lmstudio.ai/download) and open it once so its bundled `lms` command is available. The app and CLI support model downloads, loading, and a local API server; see the official [LM Studio CLI guide](https://lmstudio.ai/docs/cli).

Use these tested model repositories to avoid similarly named fine-tunes:

- [lmstudio-community/Qwen3.5-4B-GGUF](https://huggingface.co/lmstudio-community/Qwen3.5-4B-GGUF), quantization `Q4_K_M`, for chat.
- [nomic-ai/nomic-embed-text-v1.5-GGUF](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF), quantization `Q4_K_M`, for optional vector retrieval.

Embeddings improve retrieval but are not required for the workshop: ParcelCo confirms and uses keyword fallback when embeddings or Chroma are unavailable. A chat model is required to generate live replies.

### macOS or Linux

On macOS, install with the downloaded app or Homebrew, then launch it:

```bash
brew install --cask lm-studio
open -a "LM Studio"
```

On Linux, install the AppImage or package from the LM Studio download page and launch it from the desktop. After the app has run once, the following Bash commands work on both systems:

```bash
lms get lmstudio-community/Qwen3.5-4B-GGUF@Q4_K_M --gguf
lms get nomic-ai/nomic-embed-text-v1.5-GGUF@Q4_K_M --gguf
lms ls
```

Load both models from LM Studio. Start Qwen with an 8192-token context. The equivalent CLI pattern is below; replace each quoted placeholder with the exact model key printed by `lms ls`:

```bash
lms load "CHAT_MODEL_KEY_FROM_LMS_LS" --context-length 8192 --identifier qwen3.5-4b
lms load "EMBED_MODEL_KEY_FROM_LMS_LS" --identifier text-embedding-nomic-embed-text-v1.5
lms ps
lms server start --port 1234
lms server status
curl -fsS http://127.0.0.1:1234/v1/models
```

### Windows — PowerShell

Install LM Studio from its Windows installer and launch it from the Start menu once. Then run:

```powershell
lms get lmstudio-community/Qwen3.5-4B-GGUF@Q4_K_M --gguf
lms get nomic-ai/nomic-embed-text-v1.5-GGUF@Q4_K_M --gguf
lms ls
```

Load both models from LM Studio. Start Qwen with an 8192-token context. Or replace the placeholders below with the exact model keys printed by `lms ls`:

```powershell
lms load "CHAT_MODEL_KEY_FROM_LMS_LS" --context-length 8192 --identifier qwen3.5-4b
lms load "EMBED_MODEL_KEY_FROM_LMS_LS" --identifier text-embedding-nomic-embed-text-v1.5
lms ps
lms server start --port 1234
lms server status
Invoke-RestMethod http://127.0.0.1:1234/v1/models | ConvertTo-Json -Depth 4
```

`lms ps` should show both loaded API identifiers. A display name is not necessarily the API identifier, so also inspect <http://127.0.0.1:1234/v1/models>. If an older CLI reports an invalid passkey after an app update, open LM Studio and rerun the command after its bundled CLI finishes updating. An interrupted model download can resume, but the partial file cannot be loaded.

## 3. Configure ParcelCo

Open the repository-root `.env` in a text editor. The tested local profile is:

```dotenv
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
PARCELCO_MODEL=qwen3.5-4b
PARCELCO_REASONING_EFFORT=none
PARCELCO_EMBED_MODEL=text-embedding-nomic-embed-text-v1.5
PARCELCO_SUITE=demo
PARCELCO_MAX_HEAL=2
PARCELCO_MAX_OUTER_ROUNDS=5
PARCELCO_MIN_DELTA=0.05
PARCELCO_PART_B_TOLERANCE=0.05
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Use the exact identifiers returned by LM Studio if yours differ. `lm-studio` is a local placeholder API key; use your server token if authentication is enabled. Current LM Studio releases accept `reasoning_effort=none`; clear `PARCELCO_REASONING_EFFORT` for a different server that rejects it. Qwen3.5 does not use Qwen3's prompt-only thinking switches.

Leave both Langfuse keys empty for the workshop. Tracing is optional and is not installed by the default reproducible setup. Facilitators who need it can install the extra and follow the separate guide:

```bash
python -m pip install -c requirements-lock.txt -e ".[tracing]"
```

See [optional Langfuse setup](LANGFUSE_DOCKER.md) only after the main route works.

## Optional: tiny SLM as the eval layer

When `PARCELCO_EVAL_MODEL` is set, evaluation is **SLM-gated**: the model applies
the same `expected/*.json` rules (action, must-include, must-not). Heal/PASS follow
that verdict. The Python checklist still runs for evidence and concrete heal
briefs, and is the fallback if the SLM errors or returns unparseable JSON.

Leave `PARCELCO_EVAL_MODEL` empty for checklist-only evaluation.

```bash
# ~1 GB — Q4_K_M into LM Studio's models folder
python - <<'PY'
from pathlib import Path
from huggingface_hub import hf_hub_download
dest = Path.home() / ".lmstudio/models/lmstudio-community/Qwen2.5-1.5B-Instruct-GGUF"
print(hf_hub_download(
    repo_id="lmstudio-community/Qwen2.5-1.5B-Instruct-GGUF",
    filename="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
    local_dir=str(dest),
))
PY
lms load qwen2.5-1.5b-instruct --identifier qwen2.5-1.5b-instruct
```

In the repository `.env`:

```dotenv
PARCELCO_EVAL_MODEL=qwen2.5-1.5b-instruct
PARCELCO_EVAL_REASONING_EFFORT=none
```

Leave `PARCELCO_EVAL_MODEL` empty to keep checklist-only evaluation. Restart
`python -m parcelco.cli serve` after changing it.

## 4. Run tests and the readiness check

The unit tests use local fixtures and do not require LM Studio. The doctor checks the configured chat model, tries embeddings and Chroma, confirms the keyword fallback when needed, and verifies the 47-ticket demo split.

### macOS or Linux — Bash

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m parcelco.doctor
```

### Windows — PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
python -m parcelco.doctor
```

A ready run ends with this standalone line:

```text
Ready for the workshop.
```

Before that final line, expect the Python version, configured model and base URL, `PASS` for chat, `PASS` or `WARN` for embeddings/Chroma, and `Dataset: demo — 28 learn / 19 holdout / 47 total`. An embedding warning is acceptable only when the doctor confirms keyword fallback. A missing server, unloaded chat model, or chat failure ends with a concise `Not ready` summary and a nonzero exit status.

Facilitators who plan to teach vector retrieval should require embeddings:

```bash
python -m parcelco.doctor --strict-embeddings
```

With `--strict-embeddings`, an embedding or Chroma failure is fatal instead of a warning.

## 5. Start the dashboard

### macOS or Linux — Bash

```bash
source .venv/bin/activate
python -m parcelco.cli serve --suite demo
```

### Windows — PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
python -m parcelco.cli serve --suite demo
```

Open <http://127.0.0.1:5050>. Confirm **Demo: 28 learn / 19 holdout / 47 total**, filter **Learn**, select **A01**, and click **Run this ticket**. A completed run shows a reply and checklist result even when the reply fails. The dashboard and visual guide are separate pages.

## 6. Open the visual guide

`docs/index.html` contains local assets and works without a model or internet connection. You can open the file directly. For a local HTTP preview, keep the dashboard running and use a second terminal.

### macOS or Linux — Bash

```bash
cd self-improving-ai-agent-workshop
source .venv/bin/activate
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

### Windows — PowerShell

```powershell
Set-Location self-improving-ai-agent-workshop
.\.venv\Scripts\Activate.ps1
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Open <http://127.0.0.1:8000>. This serves the guide, not the agent.

## Restart on the day of the workshop

After restarting the computer, open LM Studio, load the chat model and optional embedding model, and start its server. Then run the appropriate block from the repository root.

### macOS or Linux — Bash

```bash
source .venv/bin/activate
lms ps
lms server start --port 1234
python -m parcelco.doctor
python -m parcelco.cli serve --suite demo
```

### Windows — PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
lms ps
lms server start --port 1234
python -m parcelco.doctor
python -m parcelco.cli serve --suite demo
```

If `lms ps` does not list Qwen, load it in LM Studio before running the doctor. Open the guide directly or start its server in a second terminal using step 6.

## Use alternate ports

If a port is busy, change only that service and its matching URL.

### macOS or Linux — Bash

```bash
# LM Studio: also set OPENAI_BASE_URL=http://127.0.0.1:1235/v1 in .env
lms server start --port 1235

# ParcelCo dashboard
python -m parcelco.cli serve --suite demo --port 5051

# Visual guide
python -m http.server 8001 --bind 127.0.0.1 --directory docs
```

### Windows — PowerShell

```powershell
# LM Studio: also set OPENAI_BASE_URL=http://127.0.0.1:1235/v1 in .env
lms server start --port 1235

# ParcelCo dashboard
python -m parcelco.cli serve --suite demo --port 5051

# Visual guide
python -m http.server 8001 --bind 127.0.0.1 --directory docs
```

Restart ParcelCo after editing `.env`. Open ports 5051 or 8001 in the browser when using those examples.

## Stop the processes

Press **Ctrl+C** in the terminal running the dashboard and in the terminal running the guide server.

### macOS or Linux — Bash

```bash
lms server stop
# Optional: release model memory too.
lms unload --all
```

### Windows — PowerShell

```powershell
lms server stop
# Optional: release model memory too.
lms unload --all
```

## Offline or no-model route

No installation is needed to discuss the workflow. Open the hosted guide before going offline, or download/clone the repo and open `docs/index.html` locally. Use:

- Exercise 1 to predict policy actions.
- Exercise 2 to compare replies and, if Python is installed, run the local checklist.
- Exercise 4 and the interactive gate graph to make keep/revert decisions.

Do not claim the live dashboard can generate a ticket without a chat model. A facilitator can instead show a clearly labeled captured rehearsal run.

## Start fresh for a rehearsal

The checkout may contain lessons from earlier demos. **Reset memory** replaces the prompt and learnings with built-in defaults and clears local round/event history. Copy `parcelco/memory/system_prompt.md`, `parcelco/memory/learnings.md`, and `parcelco/memory/rounds.sqlite` somewhere safe first if you need them.

```bash
python -m parcelco.cli reset
```

Reset does not remove the retrieval index or remote Langfuse traces. Stop running jobs first. Interrupting batch learning can leave provisional memory on disk; inspect or reset it before another comparison.

After changing the embedding model or policy/FAQ inputs, rebuild the index in a fresh process:

```bash
python -c "from parcelco.rag import rebuild_index; print(rebuild_index())"
```

Facilitators can run the longer live integration check after doctor passes:

```bash
python scripts/verify_local.py
```

It evaluates the demo before and after one learning round using temporary prompt, learning, and history files. It preserves workshop memory, but model-dependent pass rates and runtime vary.

## Troubleshooting

| Symptom | What to do |
|---|---|
| Python is missing or older than 3.11 | Install a supported version, delete only the incomplete `.venv`, and recreate it with the platform command in step 1. |
| `requirements-lock.txt` is missing | Update the checkout. The reproducible install uses the lock file from the runtime prerequisites. |
| `No module named parcelco` | Activate `.venv`, return to the folder containing `pyproject.toml`, and rerun `python -m pip install -c requirements-lock.txt -e .`. |
| PowerShell will not activate `.venv` | Use the process-scoped execution-policy command in step 1; it ends when that terminal closes. |
| `lms` is not found | Open LM Studio once, open a new terminal, and run `lms --help`. |
| Connection refused on port 1234 | Start the LM Studio server and verify `OPENAI_BASE_URL`. |
| Model not found | Copy the loaded chat model's exact API identifier from `/v1/models` into `PARCELCO_MODEL`, then restart ParcelCo. |
| Embeddings warn in doctor | Continue with confirmed keyword fallback, or load Nomic and run `python -m parcelco.doctor --strict-embeddings`. |
| Dashboard port is busy | Use `--port 5051` and open <http://127.0.0.1:5051>. |
| Tracing errors or long waits | Leave both Langfuse keys empty, restart ParcelCo, and continue without tracing. |
| Scores differ from rehearsal | Check the model, suite, heal limit, and saved memory. Local generation can vary with the same settings. |

## Settings used in the workshop

| Setting | Workshop value | Meaning |
|---|---:|---|
| `PARCELCO_MAX_HEAL` | `2` | Two retries after the initial draft; three drafts total. |
| `PARCELCO_MAX_OUTER_ROUNDS` | `5` | Default batch rounds. Use one only after timing it. |
| `PARCELCO_MIN_DELTA` | `0.05` | Required learn-set gain: five percentage points. |
| `PARCELCO_PART_B_TOLERANCE` | `0.05` | Allowed holdout drop: five percentage points. |
| `PARCELCO_SUITE` | `demo` | 28 learn + 19 holdout = 47 tickets. The full catalog is 700 + 300 = 1,000. |

The taught gate policy is **5 percentage points of learn-set improvement and at most 5 percentage points of holdout regression**. Do not change those values when presenting the workshop exercise.
