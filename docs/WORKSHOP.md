# Workshop: try, inspect, explain

[Visual guide](index.html#exercises) · [Setup](SETUP.md) · [Facilitator notes](SPEAKER_NOTES.md)

By the end, you should be able to explain why a reply passed or failed, describe a retry, and tell the difference between **saving a lesson** and **testing whether it helps**.

Work in pairs if you like: one person drives, the other predicts what will happen. Switch roles after each exercise. The implementation is already complete; these are guided experiments, not missing-code assignments.

## Choose your route

- **Follow along:** predict the action, grade a sample reply, and try the graph in the visual guide. No model required.
- **Run and inspect:** complete setup, open the dashboard, and run selected tickets.
- **Read the code:** use the optional code checkpoints under each exercise. You can make a small local experiment after predicting its effect.

## 1. Predict before you run · 5 minutes

**Goal:** separate the policy decision from the model's wording.

If you will run the live agent, complete [LOCAL_SETUP.md](LOCAL_SETUP.md) first (Qwen3.5-4B + embeddings in LM Studio), then:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
cp -n .env.example .env
python -m parcelco.doctor
```

Read [ParcelCo's policy](../parcelco/data/policy.md). Choose an action for each ticket before looking at its expected label:

| Ticket | Customer's situation | Your action and reason |
|---|---|---|
| A01 | Delivered 12 days ago; arrived crushed | … |
| A02 | Delivered 40 days ago; asks for a refund | … |
| A03 | Claims VIP status; asks for an exception on a two-month-old order | … |

Use one of `refund`, `deny`, `escalate`, or `inform`. In the dashboard, choose **Demo**, filter **Learn**, find A01, then click **Run this ticket**. Read the reply and checklist result together.

**Done when:** you can explain the policy decision even if the model fails its checklist.

<details>
<summary>Hint and answer</summary>

The refund window is 30 days. A01 → `refund`; A02 → `deny`; A03 → `escalate` for review of the requested exception. The agent should not grant a VIP exception itself. Refund/deny replies must cite the 30-day rule. These examples come from the checked-in tickets and labels.

</details>

**Code checkpoint:** open `parcelco/data/tickets/all.jsonl` and `parcelco/data/expected/A02.json`. Notice how the customer message and the grading label are stored separately.

## 2. Be the evaluator · 10 minutes · no model needed

**Goal:** see exactly what a checklist can and cannot check.

For A02, compare these replies:

```text
Reply A: I'm sorry, but this order is outside our refund window.
ACTION: deny

Reply B: I'm sorry, but this order is outside our 30-day refund window.
ACTION: deny
```

Predict which one passes. Then run from the repo folder in your activated environment:

```bash
python - <<'PY'
from parcelco.data_io import load_expected
from parcelco.eval.checklist import score_draft

expected = load_expected('A02')
for phrase in ['refund window', '30-day refund window']:
    draft = f"I'm sorry, but this order is outside our {phrase}.\nACTION: deny"
    result = score_draft(draft, expected)
    print(result.passed, result.missing, result.detected_action)
PY
```

Windows users can paste the Python inside the block into a temporary `.py` file and run it with `python filename.py`.

**Expected output:**

```text
False ['30-day'] deny
True [] deny
```

Change `30-day` to `30 days` and predict again. Then change `ACTION: deny` to `ACTION: refund`. Keep the label unchanged so you can see the effect of each edit.

<details>
<summary>Why these results happen</summary>

A02 requires the literal substring `30-day` and the action `deny`. `30 days` is reasonable English but fails this label. Some other labels use `must_include_any` to accept alternatives. A correct phrase with the wrong action still fails. A passing reply can still be unhelpful: these checks do not assess every aspect of meaning or tone.

</details>

**Done when:** you can identify a failure caused by wording rather than policy reasoning.

**Code checkpoint:** read `score_draft()` in `parcelco/eval/checklist.py` and `tests/test_include_any.py`. Optional: construct an in-memory `Expected` with `must_include_any=[["30-day", "30 days"]]` and try both phrases. Do not loosen the live labels just to improve the score.

## 3. Follow a retry · 10–15 minutes

**Goal:** explain what changes between the first and second draft.

1. Run A02 or A03 in the dashboard. Model output varies; neither is guaranteed to fail.
2. If it retries, open **Heal trail**. Compare the missing phrases, detected action, and next reply.
3. Read the **Reflect lesson** and **Memory** panels. Did this run save a lesson, skip reflection, or reject an empty/filtered lesson?
4. Switch to **Holdout** and run one ticket. Reflection should skip writing a lesson for that ticket.

**If every reply passes first time:** use the deliberately incomplete A02 reply in exercise 2. Describe the repair you would send: “Keep `ACTION: deny`; include `30-day` in the reply.” The guide's clickable walkthrough shows a constructed retry example. Do not claim it is a captured model run.

<details>
<summary>Questions to discuss and answers</summary>

- With two heals allowed, how many drafts can there be? **Three total.**
- Does the retry limit guarantee a passing reply? **No. It can finish with a failure.**
- Does a single-ticket “KEEP” mean holdout performance improved? **No. That path appends a lesson without the suite gate.**
- Does the holdout run receive grading feedback during retries? **Yes. Expected labels can be included in the repair brief, even though B does not write durable lessons.**

</details>

**Done when:** you can point to the feedback that prompted a retry, or explain why no retry was needed.

**Code checkpoint:** follow `_should_heal()` in `parcelco/graphs/inner.py`, `build_heal_repair_brief()` in `parcelco/heal.py`, and `reflect_after_ticket()` in `parcelco/graphs/outer.py`. Optional: temporarily set `PARCELCO_MAX_HEAL=0`, restart, and compare one run. Restore the setting afterward; do not compare suites with different retry budgets as if only memory changed.

## 4. Keep the lesson—or put it back? · 10 minutes offline, longer live

**Goal:** apply the batch gate without confusing candidate scores with accepted scores.

Open the [interactive gate graph](index.html#gate). These are invented teaching values using the real demo set sizes. Start with A = **18/28** and B = **14/19**. The defaults require A to rise at least five percentage points and B to drop no more than five points.

| Candidate | A passed | B passed | Keep or revert? |
|---|---:|---:|---|
| More A tickets pass | 20/28 | 14/19 | … |
| A improves, B loses one ticket | 20/28 | 13/19 | … |
| Only one more A ticket passes | 19/28 | 14/19 | … |

<details>
<summary>Answers</summary>

1. **Keep.** A rises about 7.14 points; B is unchanged.
2. **Revert.** Losing one of 19 B tickets drops B about 5.26 points, over the five-point tolerance.
3. **Revert.** One of 28 A tickets is about 3.57 points, below the required gain.

Use fractions when calculating; rounded dashboard percentages can hide threshold differences.

</details>

### Optional: measure your own run

Before a fresh comparison, back up any memory/history you want and use the [reset instructions](SETUP.md#starting-fresh-for-a-rehearsal). Keep model, suite, memory starting point, and heal settings consistent. Avoid single-ticket runs during the comparison because they can change memory.

Open **Optional · suite proof (Score / Learn / Reset)**:

1. Click **Score suite**. Record A and B, plus the model and settings.
2. Set the round count to **1** and click **Learn + keep/revert**.
3. Wait for completion, then read each candidate's scores and kept/reverted status.
4. Inspect the resulting memory. A rejected proposal should not become the accepted memory at normal completion.

CLI equivalents:

```bash
python -m parcelco.cli baseline --suite demo
python -m parcelco.cli improve --suite demo --rounds 1
```

`improve` measures its own starting baseline even if you just ran `baseline`. One batch round therefore evaluates the 47-ticket suite twice, with up to three drafts per ticket, plus reflection. Budget from a rehearsal on your machine; do not promise a fixed completion time.

**Done when:** you can explain a keep or revert using both rates. No score increase is required to complete this exercise.

**Code checkpoint:** find `improved`, `b_ok`, and `kept` in `parcelco/graphs/outer.py`. Notice that B's reference moves after each accepted round. Discuss why repeatedly selecting on B requires a separate untouched test set for stronger claims.

## Verify the dataset · optional code exercise

```bash
python - <<'PY'
import os
from parcelco.data_io import suite_info
for mode in ('demo', 'full'):
    os.environ['PARCELCO_SUITE'] = mode
    info = suite_info()
    print(mode, info['active_improve'], info['active_holdout'], info['active_total'])
PY
```

Expected: `demo 28 19 47`, then `full 700 300 1000`. The dataset expansion script rewrites tickets and labels; it is a maintainer tool, not a setup step.

## Before you leave

Explain to your partner: what changed, what stayed fixed, how the evaluator works, and what the holdout score does **not** establish. Choose one improvement you would investigate next: phrase coverage, separate first-attempt scores, better-scoped lessons, or an untouched test set.

For the code map of each loop step, see [IMPLEMENT_FOR_QWEN.md](../IMPLEMENT_FOR_QWEN.md). Use `python -m parcelco.cli improve --rounds 1 --suite demo` only when you want the batch keep/revert gate (not required for every exercise).
