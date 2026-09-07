# Participant prework checklist

[Full setup](SETUP.md) · [Visual guide](index.html) · [Exercises](WORKSHOP.md)

Complete this before the event. Set aside **30–60 minutes** and start earlier if your network is slow; do not leave the model download for the opening minutes.

## Choose your route

- [ ] **Run locally:** complete the full [setup guide](SETUP.md), including LM Studio, tests, and doctor.
- [ ] **No model / offline:** download the repository or open the hosted guide once before going offline. You can do the policy prediction, checklist, and gate exercises. The dashboard cannot generate live tickets without a chat model.

## Check the machine and free space

- [ ] Git and Python **3.11 or newer** are installed.
- [ ] For the known-good profile, use an Apple-silicon Mac with **16 GB memory** and Qwen3.5-4B GGUF Q4_K_M. LM Studio also supports qualifying Windows and Linux systems and recommends 16 GB memory; see its [current requirements](https://lmstudio.ai/docs/app/system-requirements).
- [ ] Keep at least **8 GB free; 10 GB is safer**. Budget at least about **3 GB** for the chat model, about **0.1 GB** for optional embeddings, and about **0.5 GB** for the Python environment, plus download caches.
- [ ] Expect slower generation on CPU-only or lower-memory systems. Pair with a ready participant if needed.

## Prove the setup before the event

In LM Studio, load Qwen and the optional Nomic embedding model, then start the local server on port 1234.

### macOS or Linux — Bash

```bash
cd self-improving-ai-agent-workshop
source .venv/bin/activate
lms server start --port 1234
python -m unittest discover -s tests -v
python -m parcelco.doctor
```

### Windows — PowerShell

```powershell
Set-Location self-improving-ai-agent-workshop
.\.venv\Scripts\Activate.ps1
lms server start --port 1234
python -m unittest discover -s tests -v
python -m parcelco.doctor
```

- [ ] Tests pass.
- [ ] Doctor reports Python/configuration, `PASS` for chat, `PASS` or `WARN` for embeddings/Chroma, and the 28/19/47 demo split.
- [ ] The final success line is exactly:

```text
Ready for the workshop.
```

An embedding `WARN` is ready only when keyword fallback is confirmed. A chat/server/model error prints `Not ready`, exits nonzero, and must be fixed before the live-model route. Facilitators using vector retrieval should also pass `python -m parcelco.doctor --strict-embeddings`.

## Start again on the day

Open LM Studio and load both models first. From the repository root:

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

- [ ] Open <http://127.0.0.1:5050> and confirm **28 learn / 19 holdout / 47 total**.
- [ ] Open `docs/index.html` directly. If you prefer a local guide server, run `python -m http.server 8000 --bind 127.0.0.1 --directory docs` in a second activated terminal and open <http://127.0.0.1:8000>.

## Know the local ports

| Port | Service | Alternate |
|---:|---|---|
| 1234 | LM Studio API | Start on 1235 and set `OPENAI_BASE_URL=http://127.0.0.1:1235/v1` in `.env`. |
| 5050 | ParcelCo dashboard | Add `--port 5051` to the `serve` command. |
| 8000 | Optional visual guide server | Use `python -m http.server 8001 --bind 127.0.0.1 --directory docs`. |

Restart ParcelCo after changing `.env`. Stop the dashboard and guide with **Ctrl+C** in their terminals; stop LM Studio's API with `lms server stop`. See [Setup](SETUP.md#use-alternate-ports) for copy-paste Bash and PowerShell alternatives and troubleshooting.
