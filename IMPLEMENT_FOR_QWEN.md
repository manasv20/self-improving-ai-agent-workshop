# Workshop 1 — Implementation Handoff (for Qwen / any implementer)

**Prefer the live build-along:** [docs/WORKSHOP.md](docs/WORKSHOP.md) + [docs/CONCEPT.md](docs/CONCEPT.md).

**Scope:** Workshop 1 only — self-improving **harness** (frozen LLM).  
**Out of scope:** SLM fine-tuning (Workshop 2, later).

**Project root:**  
The checkout directory containing `pyproject.toml`. See [local setup](docs/LOCAL_SETUP.md).

---

## Goal

Build **ParcelCo Support Flywheel** *with workshop participants*:

1. Answers tickets with policy/FAQ RAG  
2. **Heals within a ticket** when a deterministic checklist fails  
3. **Improves across rounds** by updating `learnings.md` / system prompt (keep only if scores improve)  
4. Shows everything on a **Flask HTML dashboard** (live workflow + scoreboard + full history log)  
5. Traces with **LangFuse** (optional if keys missing)

Live workshop proof: **Part B holdout pass_rate rises** after outer-loop rounds — not vibes.

---

## Repo status

The modules below are implemented in this tree. Use them as the **reference solution** while participants build checkpoint-by-checkpoint (WORKSHOP.md). Do not treat the “still need” list below as current work if the files already exist.

| Path | Role |
|---|---|
| `pyproject.toml` | deps |
| `.env.example` / `.gitignore` | env |
| `parcelco/paths.py` | path helpers + dotenv |
| `parcelco/models.py` | Pydantic models |
| `parcelco/data/policy.md` + `faq/*.md` | ground truth |
| `parcelco/data/tickets/all.jsonl` | 700 improve + 300 holdout; `tier: core` = demo 35 |
| `parcelco/data/expected/*.json` | checklist labels |
| `parcelco/eval/checklist.py` | scorer |
| `parcelco/rag.py` | retrieve |
| `parcelco/graphs/inner.py` / `outer.py` | heal + improve |
| `parcelco/history.py` / `tracing.py` / `web/` | proof + UI |
| `docs/WORKSHOP.md` | build-along curriculum |

---

## Architecture (build this)

```
Flask dashboard (SSE)
    → Outer loop (improve rounds)
        → Inner LangGraph per ticket: retrieve → generate → evaluate → heal?
    → SQLite history of rounds
    → LangFuse traces/scores/prompts
```

**Harness** = LangGraph + LangChain + Chroma + checklist + learnings/prompt.  
**Tracer** = LangFuse CallbackHandler.  
**Model** = **local Qwen3.5-4B via LM Studio** (`OPENAI_BASE_URL=http://127.0.0.1:1234/v1`, `PARCELCO_MODEL=qwen3.5-4b`). Use MLX 4-bit on Apple silicon; see [local setup](docs/LOCAL_SETUP.md).

---

## Data rules

- Tickets live in `parcelco/data/tickets/all.jsonl` (`split`: `improve` | `holdout`, `tier`: `core` | `full`).
- `PARCELCO_SUITE=demo` loads only `core` (35); `full` loads all 1000 for a larger evaluation.
- Create `parcelco/data/expected/{id}.json` for **every** ticket id with:
  ```json
  {
    "ticket_id": "A01",
    "must_include": ["30-day"],
    "must_not": ["VIP exception granted"],
    "action": "refund",
    "notes": "damaged within window"
  }
  ```
- `action` ∈ `refund` | `deny` | `escalate` | `inform`
- Agent replies must end with a line: `ACTION: refund|deny|escalate|inform`
- Checklist is **deterministic Python** — primary gate. Optional LLM-judge only for tone, never sole keep/revert signal.
- Part A (`improve`): used to write lessons.  
  Part B (`holdout`): **score only** — never feed failures into lesson text that memorizes B ids.

Optional later: script to sample more phrasings from Hugging Face  
`bitext/Bitext-customer-support-llm-chatbot-training-dataset` and rewrite to ParcelCo policy — keep labels.

---

## Modules to implement

### 1. `parcelco/eval/checklist.py`
- Parse `ACTION:` from draft  
- Score `must_include` / `must_not` (case-insensitive substring)  
- Return `ChecklistResult` with `passed`, `score` (0–1)

### 2. `parcelco/rag.py`
- Load `policy.md` + `faq/*.md` into Chroma under `parcelco/memory/chroma/`  
- Retrieve top-k chunks for a ticket message  
- Rebuild index if empty

### 3. `parcelco/graphs/inner.py` (LangGraph)
State fields: ticket, docs, draft, checklist, heal_count, steps, learnings  
Nodes: `retrieve` → `generate` → `evaluate` → (`heal` → retrieve) or end  
Env: `PARCELCO_MAX_HEAL` (default 2)  
`generate` uses system_prompt + learnings + retrieved docs + ticket  
Emit step names for the UI: `retrieve`, `generate`, `evaluate`, `heal`

### 4. `parcelco/graphs/outer.py`
- Run all improve tickets → Part A rate  
- Run all holdout tickets → Part B rate  
- Reflect: cluster Part A failures → append short lessons to `learnings.md` (and/or patch prompt)  
- Re-run suite  
- **Keep** if Part A improves by `PARCELCO_MIN_DELTA` **and** Part B does not drop more than tolerance (e.g. 0.05); else **revert** prompt/learnings  
- Persist `RoundRecord` each round  
- Cap rounds: `PARCELCO_MAX_OUTER_ROUNDS`

### 5. `parcelco/history.py`
- SQLite at `parcelco/memory/rounds.sqlite`  
- Tables: rounds (json fields ok), optional ticket_runs  
- APIs: list_rounds, latest_scores, append_round

### 6. `parcelco/tracing.py` (LangFuse)
- If keys missing → no-op callbacks  
- If present → CallbackHandler on graph invokes; attach checklist scores to traces  
- Return optional trace URL for dashboard

### 7. `parcelco/web/app.py` + templates/static
Flask app with:
- `GET /` — dashboard  
- `POST /api/baseline` — one full suite eval, no mutate  
- `POST /api/improve` — start outer loop (background thread or generator)  
- `GET /api/events` — SSE: step events, ticket results, round summaries  
- `GET /api/history` — all rounds  
- `POST /api/reset` — restore baseline prompt + empty learnings  

Dashboard panels:
1. Controls  
2. Live workflow (current node)  
3. Scoreboard Part A / Part B  
4. History log (kept/reverted + lesson summary)  
5. Simple Chart.js line chart  
6. Ticket inspector (draft + failures + chunks)

### 8. `parcelco/cli.py`
- `python -m parcelco.cli serve` → Flask on :5050  
- `python -m parcelco.cli baseline`  
- `python -m parcelco.cli improve --rounds 3`

### 9. Docs
- `README.md` — setup, env keys, how to run demo  
- `docs/SPEAKER_NOTES.md` — 15-min live script + Loop Engineering term map  
  (worker, evaluator, memory, termination, keep/revert, harness vs tracer)

---

## Acceptance criteria

- [ ] `pip install -e .` (or `uv sync`) works on Python 3.11+  
- [ ] Without LangFuse keys, demo still runs  
- [ ] Baseline prints Part A and Part B rates  
- [ ] Scoreboard shows where-it-was → where-it-is lift after improve 
- [ ] Improve loop writes history rows; UI shows curve  
- [ ] At least one demo run shows Part B rate ≥ baseline (may need prompt/lesson quality tuning)  
- [ ] Checklist never calls the LLM to grade itself for keep/revert  
- [ ] Holdout tickets never appear as verbatim lesson targets  

---

## Suggested build order

1. Expected JSON for all 1000 tickets + checklist unit tests on 3 fixtures
2. RAG + inner graph (single ticket CLI)  
3. Outer loop + SQLite history  
4. LangFuse optional wiring  
5. Flask + SSE dashboard  
6. Speaker notes / polish  

---

## Teaching vocabulary (put on UI or speaker sheet)

| Loop Engineering | In this app |
|---|---|
| Worker | LangGraph generate (+ RAG) |
| Evaluator | Python checklist |
| Memory | `learnings.md` + prompt versions |
| Termination | max heal / max outer rounds |
| Feedback | heal path + outer lessons |
| Safety | no VIP exceptions; revert on Part B regression |
| Harness | LangGraph + LangChain + Chroma + checklist |
| Tracing | LangFuse |

---

## Workshop 2 (do not build now)

Export accepted/repaired traces → LoRA SFT an SLM → eval on Part B. Separate folder/session later.
