# Self-improving AI agent workshop

Teach a support agent to check its work, retry a reply, and save lessons for later tickets. **The model stays the same; its instructions and saved lessons can change.**

ParcelCo is a fictional delivery company. You'll use its policy, sample customer tickets, and a Python checklist to see what improves—and what still fails. No fine-tuning is required.

**Start with the [visual workshop guide](docs/index.html).** Download the repo and open `docs/index.html` in your browser; it works offline, with diagrams, exercises, and an interactive keep/revert graph. GitHub's file view shows HTML source, not the rendered page.

## Join the session

- **Following along?** Open the visual guide. You can do the prediction and scoring exercises without running a model.
- **Running the demo?** Follow [Setup](docs/SETUP.md), then use the command below.
- **Teaching?** Use the [facilitator notes](docs/SPEAKER_NOTES.md) and rehearse before the event.

From the repository folder, with your virtual environment activated and LM Studio serving a chat model:

```bash
python -m parcelco.cli serve --suite demo
```

Open <http://127.0.0.1:5050>. Select a ticket, then click **Run this ticket**. The reference guide and the live dashboard are separate pages.

## What you will learn

1. Retrieve policy and FAQ text before drafting a reply.
2. Check the reply against a labeled example.
3. Use specific failure feedback to retry, up to a limit.
4. Distinguish saving a lesson from measuring whether it helps.

The dashboard's single-ticket path can save a learn-set lesson immediately. **Only the batch “Learn + keep/revert” path tests proposed changes against both ticket sets before keeping them.** See [How it works](docs/CONCEPT.md) for the exact behavior and evaluation limits.

## Pick a guide

| You need… | Read this |
|---|---|
| A browser reference during the session | [Visual guide](docs/index.html) |
| Installation and troubleshooting | [Setup](docs/SETUP.md) |
| Activities, commands, hints, and answers | [Workshop exercises](docs/WORKSHOP.md) |
| The diagram and key terms | [Concepts](docs/CONCEPT.md) |
| A timed teaching plan and backup plan | [Facilitator notes](docs/SPEAKER_NOTES.md) |
| A shorter walkthrough | [15-minute demo](docs/PRESALES_DEMO.md) |
| Optional model-call traces | [Langfuse setup](docs/LANGFUSE_DOCKER.md) |
| Where the implementation lives | [Code map](IMPLEMENT_FOR_QWEN.md) |

## Dataset and checks

| Suite | Learn set (Part A) | Holdout (Part B) | Total |
|---|---:|---:|---:|
| `demo` — use live | 28 | 19 | 47 |
| `full` — rehearse separately | 700 | 300 | 1,000 |

The 47 core tickets include ambiguous examples added to the original 35. These counts come from `parcelco/data/tickets/all.jsonl`; the exercises show how to verify them.

Run the existing checks without a model or Docker:

```bash
python -m unittest discover -s tests -v
```

Model replies and timings vary. A failed retry or a reverted lesson is a useful workshop result, not a reason to hide the run.
