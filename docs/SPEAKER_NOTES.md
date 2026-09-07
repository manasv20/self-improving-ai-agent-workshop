# Facilitator notes

[Visual guide](index.html) · [Exercises](WORKSHOP.md) · [Prework](PREWORK.md) · [Setup](SETUP.md)

Teach participants to inspect a result and explain it. A pass, a failed retry, and a reverted lesson are all useful outcomes.

## 24 hours before

- Complete [Setup](SETUP.md) on the presentation machine using the same model, `.env`, suite, and retry limits planned for the session.
- Run the unit tests, then `python -m parcelco.doctor --strict-embeddings`. Confirm its last line is `Ready for the workshop.` and the demo split is **28 learn / 19 holdout / 47 total**.
- Perform an **offline-dashboard check** after dependencies and models are local: disconnect the machine from the internet, reload the guide and dashboard, run one ticket through local LM Studio, and check the browser console/network panel for external asset requests. Restore the connection afterward. The no-model route still uses only the guide, sample replies, checklist exercise, and gate graph.
- Perform a **clean-memory check**: stop active jobs, back up any prompt/learnings/history you need, run `python -m parcelco.cli reset`, then confirm the dashboard starts with baseline memory and empty local round/event history. Do not compare a fresh run with rehearsal-contaminated memory.
- Rehearse A01, A02, and B01. Save a **captured-run fallback** showing one complete run: ticket, reply, checklist, attempt/heal trail, memory outcome, model ID, suite, retry limit, and date. Label it as a captured rehearsal when presenting it.
- Time a full batch baseline plus one learning round on the presentation machine. Keep the live batch facilitator-only unless that measured time fits the agenda with margin; otherwise use the offline gate exercise and a captured batch result.
- Open every captured image or recording once from its offline location. Do not rely on a cloud link as the only fallback.

## Before people arrive

- Open the visual guide and the dashboard in separate tabs. The guide's **Presentation view** enlarges it for a projector; **Print / save PDF** gives participants a handout.
- Re-run `python -m parcelco.doctor --strict-embeddings` and confirm **Demo: 28 learn / 19 holdout / 47 total**.
- Open the captured-run fallback locally and keep it beside the live tabs.
- Decide whether participants are running locally or following your screen. Pair people who are still installing with someone who is ready.
- Back up any memory/history you want before using **Reset memory**. The checkout contains earlier demo lessons; reset restores the built-in standing rules and clears local history.
- Keep the batch controls collapsed unless the rehearsed timing fits the remaining session budget.
- Leave Langfuse off unless you have verified it beforehand. It is optional.

## A 60-minute session

| Minutes | Activity | Ask the room |
|---|---|---|
| 0–5 | Explain the task; show the policy and one customer ticket | “What action should the agent take?” |
| 5–12 | Exercise 1: predict A01/A02/A03; run one | “What policy supports that answer?” |
| 12–22 | Exercise 2: grade the two A02 replies | “What changed besides the wording?” |
| 22–37 | Exercise 3: inspect a retry and a saved lesson | “What feedback did the next draft receive?” |
| 37–50 | Exercise 4: use the gate graph; show a captured batch or a timed live batch | “Would you keep this candidate? Calculate both rates.” |
| 50–60 | Discuss evaluation limits and take questions | “What would you measure before trusting this with real customers?” |

With 75 minutes, give pairs ten more minutes for code checkpoints and five for optional trace inspection. Installation should happen before the session, not consume the opening block.

## Opening words

> “We’re helping a fictional delivery company answer support tickets. First we'll decide what a good reply should do. Then we'll watch a model draft, a checklist check, and a retry use that feedback. Finally we'll look at what gets saved for the next ticket.”

Point at the visual guide's workflow. Explain only the terms needed now: **retrieve** means find policy text; **heal** means retry with specific feedback; **reflect** means write a lesson.

## What to point at on screen

1. **Pick → Demo → Learn**, choose A01, then **Run this ticket**.
2. Show the reply, detected action, and pass/fail. A01 should request `refund`; actual output may fail.
3. Run A02 or A03. If it retries, pause at **Heal trail** and read the concrete failure.
4. Read **Reflect lesson** and the **Memory** tab. A saved lesson here has **not** been tested by the batch gate.
5. Filter **Holdout**, select **B01**, and run it to show reflection being skipped. Explain that its retries can still use expected-label feedback.
6. Expand **Optional · suite proof (Score / Learn / Reset)** only for a facilitator-run batch that was timed during rehearsal. Set rounds to **1**.

If you will compare batch scores, reset/back up before the comparison and avoid single-ticket runs between measurements. **Learn + keep/revert** calculates a fresh starting score of its own. Use the kept/reverted column to distinguish candidates from accepted memory; the history chart includes rejected candidates too.

## If the demo takes an unexpected turn

| What happens | Keep teaching with… |
|---|---|
| Model does not connect | Show the labeled captured-run fallback, then use exercise 1 and the offline checklist example. One facilitator can troubleshoot while pairs predict. |
| Every ticket passes first try | The constructed A02 walkthrough in the guide. Clearly say it is an example, not a captured run. |
| A reply still fails after retries | Ask whether the failure is policy reasoning, output format, or a missing phrase. The limit is doing its job. |
| No lesson appears | Check for a clean first-attempt pass, a holdout ticket, or an empty/filtered lesson. |
| A batch candidate is reverted | Calculate A gain and B drop together. The learning objective is to understand the decision. |
| A suite is too slow | Stop the live batch and use the graph or captured batch result. Inspect/reset provisional memory before restarting a comparison. |
| Scores look mixed across runs | Old history remains until reset. Do not compare different suites or settings as a memory-only experiment. |

## Be precise about the evidence

Say: “The instructions changed; the model weights stayed fixed.”

Say: “This score describes a checklist-based workflow with label-assisted retries.” The expected action and missing phrases can be supplied during repair, including on B.

Say: “B is excluded from durable lesson writing, but participates in candidate selection.” It is a validation signal, not proof against memorization.

Say: “Single-ticket KEEP means saved. Batch KEEP means both configured thresholds passed.” The default B tolerance allows a five-percentage-point drop, not necessarily zero regression.

Avoid promising improvement, fixed runtime, production readiness, or comprehensive quality coverage. Ask participants which failure they would add to the evaluation next.

## Optional trace stop · 5 minutes

With [Langfuse configured](LANGFUSE_DOCKER.md), open the selected ticket's trace link. Compare generation count to the attempt trail: two heals should correspond to three generations. Look at checklist scores alongside the reply. Trace ingestion may lag; “not yet verified” is not itself a policy failure.

## Close with a check for understanding

Have each pair explain one retry and one gate decision. Ask what they would need for a stronger test: an untouched test set, first-attempt scores, human review of meaning, or broader customer scenarios. Collect those ideas before discussing any future fine-tuning session.
