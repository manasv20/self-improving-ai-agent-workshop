# Code map and maintainer guide

The original filename is kept for existing links. The workshop is implemented; this is a map of the reference solution, not a list of unfinished modules.

For participant instructions, use [the setup guide](docs/SETUP.md) and [exercises](docs/WORKSHOP.md). This maintainer map covers a support-agent workflow with frozen model weights; fine-tuning is not implemented.

**Project root:** the checkout directory containing `pyproject.toml`.

## Follow one ticket through the code

| File | Read it to understand… |
|---|---|
| `parcelco/models.py` | Ticket, expected-label, checklist-result, and round-record fields. |
| `parcelco/data_io.py` | Suite filtering, labels, prompt/lesson files, and built-in reset text. |
| `parcelco/data/policy.md`, `faq/*.md` | Fictional company policy used as retrieved context. |
| `parcelco/rag.py` | Up to four whole policy/FAQ documents via Chroma embeddings or keyword fallback. |
| `parcelco/llm.py` | Local model connection, model identifiers, and generation settings. |
| `parcelco/eval/checklist.py` | Action parsing, required substrings/OR-groups, forbidden substrings, and internal-jargon checks. |
| `parcelco/heal.py` | Repair brief containing the prior reply, expected action, and concrete fixes. |
| `parcelco/graphs/inner.py` | Retrieve → generate → evaluate → heal, bounded by the retry setting. |
| `parcelco/graphs/outer.py` | Single-ticket reflection and batch improvement; these have different acceptance rules. |
| `parcelco/web/app.py` | Dashboard routes and background jobs. |
| `parcelco/templates/dashboard.html`, `parcelco/static/` | Live teaching interface. |
| `parcelco/events.py`, `parcelco/history.py` | Event stream and SQLite round/event history. |
| `parcelco/tracing.py` | Optional generation callbacks, stored scores, trace verification, and lesson annotations. |
| `parcelco/cli.py` | `serve`, `baseline`, `improve`, and `reset` commands. |
| `parcelco/doctor.py` | Local LM Studio / env sanity checks. |

## Entry points and memory effects

`run_ticket()` alone runs the ticket graph and returns a result. The dashboard's `/api/run-ticket` route then calls `reflect_after_ticket()`. It saves filtered template lessons from failed/repaired **learn-set** tickets immediately, without batch evaluation; clean first-attempt passes and holdout tickets skip lesson writing.

`baseline()` runs A and B with the current prompt/lessons and logs a round. `improve()` first measures a fresh baseline, then proposes lessons from A failures, adds a prompt reminder if needed, and re-runs both sets. Defaults keep a proposal if A gains at least `0.05` and B drops no more than `0.05` relative to the last accepted state. Rejected candidates remain in round history; normal completion restores the best accepted prompt/lessons.

`PARCELCO_MAX_OUTER_ROUNDS` is the default round count; an explicit `--rounds` overrides it. The batch also stops after a candidate A rate reaches `0.999`. These are not guarantees about latency or quality. Interruption may leave provisional files, because updates are not transactional.

## Data contract

- `parcelco/data/tickets/all.jsonl`: 1,000 tickets, **700 improve / 300 holdout**.
- `demo` selects `tier=core`: **28 improve / 19 holdout = 47**. `full` selects all tickets.
- Every ticket ID has a matching `parcelco/data/expected/{id}.json`.
- Supported actions: `refund`, `deny`, `escalate`, `inform`.
- `must_include` requires all listed substrings. Each `must_include_any` inner list requires at least one alternative. Matching is case-insensitive.
- The prompt requests one final `ACTION:` line. The current parser actually takes the **last matching action line anywhere in the reply**; it does not enforce exactly one tag or a final-line position.
- Suite pass rate counts completely passing tickets after retries. The checklist's fractional `score` is a different quantity.

The expansion script rewrites tickets/labels and is not needed for workshop setup. If the catalog changes, regenerate the counts from `suite_info()` and update README, workshop, facilitator/demo notes, code map, and HTML together.

## Markdown files that are runtime inputs

`parcelco/data/policy.md`, `faq/*.md`, and `parcelco/memory/*.md` are passed to the model. Treat changes there as behavior changes, not cosmetic documentation edits. The policy/FAQ are short reference fixtures. The checked-in learnings include prior demo output, including broad action rules that can conflict across ticket types. Use the documented reset before a fresh rehearsal.

Reset text comes from `BASELINE_PROMPT` and `BASELINE_LEARNINGS` in `data_io.py`, not a Git checkout. Changing runtime Markdown alone does not change the reset defaults. Rebuild the Chroma index after changing policy/FAQ or embedding models; a nonempty collection is reused automatically.

## Evaluation boundaries

The checker does not assess full semantic correctness. Expected-label information is supplied during healing on A and B. B is excluded from durable lesson writing but participates in candidate selection, so it is not an untouched final test. See [Concepts](docs/CONCEPT.md) for language suitable for participants.

Langfuse is optional. The callbacks wrap generation calls; do not describe complete graph tracing or model training as implemented features.

## Check a documentation change

```bash
python -m unittest discover -s tests -v
python -m parcelco.cli --help
python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Open the guide at <http://127.0.0.1:8000>. Check desktop and narrow screens, keyboard focus, the walkthrough, graph controls, exercise answers, copy buttons, presentation mode, and print preview. Teaching numbers must be explicitly labeled as examples, not run results. Keep the guide usable without network assets or JavaScript for its core reading content.

Read [Setup](docs/SETUP.md) for live model checks. Default model: **Qwen3.5-4B** via LM Studio. Tests use local fixtures/mocks and do not establish model quality. A kept round or a visible heal is not required for a documentation PR to pass validation.

| Role | Piece |
|---|---|
| Worker | LangGraph generate (+ RAG) |
| Evaluator | Python checklist |
| Memory | `learnings.md` + prompt versions |
| Termination | max heal / max outer rounds |
| Tracing | LangFuse (optional) |
