# Self Improving AI Agent Workshop — Workshop 1

**Goal:** build **one self-improving loop** with the room, in realtime.

> retrieve → generate → evaluate → heal → reflect → keep/revert

Start here: **[docs/WORKSHOP.md](docs/WORKSHOP.md)** · **[docs/CONCEPT.md](docs/CONCEPT.md)**

## Setup

```bash
cd ~/Desktop/Self\ Improving\ AI\ Agent\ Workshop
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp -n .env.example .env
python -m parcelco.cli serve --suite demo
# http://127.0.0.1:5050
```

## Dataset

- **1000** labeled tickets: **700** learn-set + **300** holdout  
- `--suite demo` = core **35** for live rooms  
- Expand: `python scripts/expand_tickets.py`

## Run

```bash
python -m parcelco.cli serve --suite demo
./scripts/start-langfuse.sh   # optional — docs/LANGFUSE_DOCKER.md
```

Punchline: one loop; weights frozen; holdout proves it.

More: [docs/SPEAKER_NOTES.md](docs/SPEAKER_NOTES.md), [IMPLEMENT_FOR_QWEN.md](IMPLEMENT_FOR_QWEN.md).
