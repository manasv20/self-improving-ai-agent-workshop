# A 15-minute walkthrough

For guests who are watching rather than working through exercises. Use [the full workshop](WORKSHOP.md) for the teaching session and [facilitator notes](SPEAKER_NOTES.md) for preparation.

## Prepare

Follow the authoritative [Setup](SETUP.md), rehearse your model, and open the visual guide next to the dashboard:

```bash
python -m parcelco.cli serve --suite demo
```

The demo contains **47 tickets: 28 learn and 19 holdout**. The full catalog contains 1,000: 700 learn and 300 holdout. Use measured rehearsal timings, not promised suite runtimes.

## Walkthrough

| Time | Show | Explain |
|---|---|---|
| 0–3 min | A01 and the policy | “A damaged delivery within 30 days is eligible. Let's see whether the reply follows the rule.” |
| 3–7 min | **Run this ticket**, reply, checklist, and **Heal trail** | “The checker gives specific feedback. A retry uses that feedback, up to a limit.” |
| 7–10 min | A learn-set **Reflect lesson** and the **Memory** tab | “This path saves a lesson immediately. It does not measure whether the whole suite improved.” |
| 10–13 min | The guide's gate graph or completed batch history | “The batch action tests a candidate on both sets and keeps it only if both thresholds pass.” |
| 13–15 min | One limitation and questions | “The scores include label-assisted retries. An untouched test set and broader quality checks would be needed for stronger claims.” |

If a model reply passes immediately, use the guide's labeled, constructed retry example. If using recorded batch results, name the suite, model, retry settings, and memory starting point. Do not present the guide's invented graph values as measured results.

## If a facilitator has timed the live batch

Keep this facilitator-only unless rehearsal showed it fits the agenda with margin. Expand **Optional · suite proof (Score / Learn / Reset)**, click **Score suite**, then set rounds to **1** and click **Learn + keep/revert**. It runs its own starting baseline and then evaluates the proposed memory; allow enough time for both passes.

Read **kept/reverted** beside the scores. A rejected candidate stays in history for inspection but is not the accepted memory at normal completion. By default, A must gain at least five percentage points and B may drop no more than five points relative to the last accepted state.

Optional: open a Langfuse trace to inspect model calls and stored checklist scores. Tracing records evidence; the Python checklist makes the policy pass/fail decision.

## The claim this demo supports

The repo demonstrates a workflow that drafts, checks, retries, and changes text instructions. It makes some failures and acceptance decisions inspectable. It does not fine-tune the model, guarantee improvement, establish that a holdout is untouched during repair, or execute real customer refunds.
