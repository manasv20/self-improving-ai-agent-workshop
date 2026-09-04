# Speaker notes — Workshop 1 (one loop, build-along)

Curriculum: [WORKSHOP.md](WORKSHOP.md) · Concept: [CONCEPT.md](CONCEPT.md)

## Open with the mismatch fix (2 min)

> It’s not two systems. It’s **one loop**: retrieve → generate → evaluate → heal → reflect → keep/revert.

Then open the dashboard teach strip and leave it up the whole session.

## Setup

- Qwen in LM Studio  
- `python -m parcelco.cli serve --suite demo`  
- Optional LangFuse  

## Script

1. Pick ticket from the **1000**-ticket catalog (demo filters to core 35)  
2. **Run loop on ticket** — narrate each node as it lights  
3. Hard ticket → show **Loop attempts** (heal)  
4. **Score suite** / **Learn** — Reflect node + where it was → now  
5. LangFuse trace (optional)  

## Say this

- Heal = retry step in the **same** loop  
- Learn set vs holdout = proof we didn’t memorize  
- Weights frozen; memory gated  

## Pitfalls

- Full suite feels stuck on 4B — use `--suite demo`  
- Ctrl+C stops serve + background job  
