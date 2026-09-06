# Pre-sales / stakeholder demo (optional)

This is a **short show path** if buyers sit in — the primary format is still the **build-along workshop** ([WORKSHOP.md](WORKSHOP.md)).

## Story in one line

> “We don’t just call an LLM — we run a **visible harness**: LangChain for tools/model I/O, LangGraph for the loop, a hard checklist evaluator, LangFuse for traces, then an outer improve loop that only **keeps** changes that raise scores.”

## Screen layout (what buyers should see)

| Panel | What you say |
|---|---|
| **Stack strip** (top) | “These are the productized layers — watch them light up.” |
| **LangGraph nodes** | “Inner loop: retrieve → generate → evaluate → heal.” |
| **Activity feed** | “Narration of each layer as it fires.” |
| **Scoreboard + chart** | “Proof: Part A learn set, Part B holdout — bigger suite so lift is visible.” |
| **Where it was → where it is** | “Same numbers, framed as before/after for the buyer.” |
| **History** | “Audit log of keep vs revert.” |
| **Inspector** | “One ticket’s draft + checklist + retrieved docs.” |
| **LangFuse** (browser tab, optional) | “Same run as nested spans / cost / prompt version.” |

## Click path

### 1) Warm-up — Demo one ticket (~60–90s)

1. Open http://127.0.0.1:5050  
2. Click **Demo one ticket**  
3. Point at strip as it lights: **Click → LangChain → LangGraph → Evaluator** (+ **LangFuse** if keys set)  
4. Open inspector: draft, `ACTION:` line, pass/fail  

**Talk track:** “Customer asks for a refund. LangChain pulls policy. Qwen drafts. Checklist grades — not the model grading itself. If it fails, LangGraph heals and retries.”

### 2) Baseline (~3–6 min on demo suite; longer on full)

For a **live** room: start with `PARCELCO_SUITE=demo` (20A / 15B).  
For a **proof** recording or overnight run: `PARCELCO_SUITE=full` (700A / 300B).

1. Click **Run baseline**  
2. When done, read **Part A** and **Part B** rates — then point at **Where it was**  

**Talk track:** “Cold harness on a labeled suite. Holdout exists so we can’t fake improvement by memorizing the train tickets. Full catalog is 1000 tickets; we can run the core 35 live.”

### 3) Improve loop (~5–8 min on demo)

1. Set rounds to **2**  
2. Click **Start improve loop**  
3. When **Improve** lights and history shows **kept/reverted**, pause on **Where it is** + **Lift**  

**Talk track:** “Outer loop writes lessons, re-scores. We only keep if Part A rises and Part B doesn’t collapse. That’s the flywheel you’d put in production governance — before vs after, not vibes.”

### 4) LangFuse tab (if configured)

1. Open LangFuse project  
2. Find the latest trace for a generate call  
3. Show nested spans: retrieve context → LLM → score  

**Talk track:** “Observability is first-class — every sales engineer / risk reviewer can audit.”

If LangFuse keys are empty, say: “Tracing hooks are wired; we turn them on with keys — strip shows optional/off.”

## What not to claim

- Don’t say the **model weights** improved — say the **harness / memory / prompt** improved.  
- Don’t hide slow local 4B latency — frame it as “runs on your VPC / laptop.”  
- Workshop 2 (train an SLM) is a **follow-on**, not this demo.

## Setup checklist

```bash
# LM Studio: Qwen loaded on :1234
# From the checkout containing pyproject.toml; complete LOCAL_SETUP.md first.
source .venv/bin/activate
# Live room: demo suite. Full evaluation: explicitly use --suite full.
python -m parcelco.cli serve --suite demo
```

Optional `.env`:
```
PARCELCO_SUITE=full   # or demo
```

```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```
