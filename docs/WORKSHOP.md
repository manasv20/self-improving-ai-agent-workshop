# Workshop 1 — Build the one loop with us

**Outcome:** everyone can run and explain **one self-improving loop** in realtime.

> retrieve → generate → evaluate → heal → reflect → keep/revert

Concept card: [CONCEPT.md](CONCEPT.md). Facilitator: [SPEAKER_NOTES.md](SPEAKER_NOTES.md).

---

## Tracks

| Track | What you do |
|-------|-------------|
| **A — Run & inspect** | Use this repo; follow the UI teach strip |
| **B — Build with us** | Implement each step; peek at finished files when stuck |

---

## Prerequisites

Complete [LOCAL_SETUP.md](LOCAL_SETUP.md) first: Qwen3.5-4B and Nomic embeddings
must be loaded in LM Studio. Run commands from the checkout with `pyproject.toml`.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
cp -n .env.example .env
# LM Studio: Qwen3.5-4B on http://127.0.0.1:1234/v1
python -m parcelco.doctor
```

Ping:

```bash
python -c "from parcelco.llm import chat_model; print(chat_model().invoke('Reply: pong').content[:40])"
```

---

## Live room path (Track A — 20 min demo inside the build)

```bash
python -m parcelco.cli serve --suite demo
# http://127.0.0.1:5050
```

On screen together:

1. Teach strip: Pick → Run → Heal → Learn  
2. Pick a hard ticket (VIP / invent amount) → **Run loop on ticket**  
3. Watch **one loop** nodes + **Loop attempts**  
4. **Score suite** → where it was  
5. **Learn (1 round)** → Reflect node + where it is now  
6. Optional LangFuse open trace  

Dataset: **1000** labeled tickets (700 learn / 300 holdout). Demo suite = core 35 for speed.

---

## Build checkpoints (Track B)

### 0 — Data

Tickets + `expected/{id}.json`. Verify:

```bash
python -c "from parcelco.data_io import load_tickets; print(len(load_tickets(None, respect_suite=False)))"
```

Expect **1000**.

### 1 — Evaluate (checklist)

`parcelco/eval/checklist.py` — ACTION + must_include / must_not.

### 2 — Retrieve (RAG)

`parcelco/rag.py`

### 3 — Loop body (retrieve → generate → evaluate → heal)

`parcelco/graphs/inner.py` — **this is the loop** for one ticket.

### 4 — Reflect + gate on the suite

`parcelco/graphs/outer.py` — same loop across many tickets; keep/revert.

Use `python -m parcelco.cli improve --rounds 1 --suite demo` for this checkpoint.
This path evaluates both splits and keeps lessons only when the gate passes.
The dashboard's single-ticket/autonomous reflection path saves sanitized
learn-set lessons immediately; it does not run a holdout gate for each ticket.
Do not use that path alone as evidence of holdout improvement.

### 5 — UI + LangFuse

One workspace, teach strip, realtime nodes.

```bash
./scripts/start-langfuse.sh   # optional
python -m parcelco.cli serve --suite demo
```

---

## Facilitator schedule (60–75 min)

| Min | Block |
|-----|--------|
| 0–8 | One-loop punchline + open UI |
| 8–20 | Checkpoint 1–2 together |
| 20–40 | Checkpoint 3 — run tickets live |
| 40–55 | Checkpoint 4 — score + learn |
| 55–70 | LangFuse + Q&A |
| 70–75 | Workshop 2 teaser |

Use `--suite demo` live. Full 1000 is for overnight / recorded proof.

Stop runaway suite: **Ctrl+C** on serve.

---

## Done when

- [ ] You can draw the one loop from memory  
- [ ] A live ticket shows heal attempts  
- [ ] Score → Learn updates where it was → where it is now  
- [ ] You never say “two loops” — only steps of one loop  
