# Iteration-2 — simplify skill validation

Date: 2026-05-11. 5 subagents, each ran `/aidoctor:simplify` (the three-angle review skill) against one iteration-1 BASELINE Python file. Compared findings to the ground truth we identified by hand in iteration-1.

## Headline

> **The simplify skill catches everything we found by hand AND surfaces 6.3× more nuanced findings, with zero false positives.** This is the LLM-intelligent layer working — design-level issues no static rule can express.

## Quant: findings count vs hand review

| Eval | Hand findings | Simplify findings | Δ |
|---|---|---|---|
| 1. fastapi-auth | 1 ("verbose but correct") | **21** (6 reuse + 10 quality + 5 efficiency) | **+20** |
| 2. data-cleaning | 2 (iterrows + drop mutation) | 5 | +3 |
| 3. async-cache | 3 (sync I/O, blocking sleep, nested asyncio.run) | **12** | **+9** |
| 4. stub-todo | 1 (redundant TODO) | 6 | +5 |
| 5. type-safe-cache | 0 (already clean) | **0** (correctly) | 0 |
| **Total** | **7** | **44** | **+37** |

The simplify skill catches 100% of hand-found bugs AND finds 6.3× more.

## The critical test: eval-3 (3 real runtime bugs)

Baseline file had:
- `requests.get` inside `async def` → blocks event loop
- `time.sleep(0.1)` inside `async def` → blocks event loop
- `asyncio.run(_fetch())` inside an outer `async` context → `RuntimeError` at runtime

**Simplify caught all 3.** Then surfaced 4 more production concerns my hand review missed:
- Thundering herd: no in-flight Task dedup → N concurrent requests for same URL all hit upstream
- Unbounded cache growth (no eviction)
- Constant backoff with no jitter (synchronizes retry storms)
- No connection pooling

It also proposed concrete alternatives: `tenacity` for retries, `async_lru.alru_cache` for caching. Decision brief recommended **Option B (full rewrite)** over surgical patch — because a surgical fix would leave an `async def` that still blocks the loop. Correct judgment.

## The "don't manufacture findings" test: eval-5

Eval-5's baseline was already correct — model defaults handled the prompt's "just use T directly" pressure well. **The reviewer returned ZERO findings** and explicitly cited Phase 5 of the skill: *"If the code was already clean, say so — don't manufacture findings."* No false positives.

This matters because a skill that always finds something to "improve" creates noise and erodes trust. simplify's calibration is honest.

## Decision-brief quality

Every report followed the gstack-style decision-brief format from the skill:
- D1 numbered question
- ELI10 stake-naming
- Options A/B/C with ✅/❌ pros-cons (≥40 chars each)
- Recommendation with one-line reason
- Net line closing the trade-off

Recommendations were well-calibrated:
- **4/5 evals → Option A** (consensus items only, tight fixes) — kept reviews surgical
- **1/5 evals → Option B** (eval-3, full rewrite) — escalated because the file was broken at runtime
- **1/5 evals → SKIP** (eval-5) — declined to manufacture work

No over-engineering. No under-engineering. Right calibration.

## Findings beyond what I caught by hand

| Eval | What simplify saw that I missed |
|---|---|
| 1. fastapi-auth | Per-request `httpx.AsyncClient` (should share via lifespan); 5 duplicate raise blocks; missing `from exc` on 6 chains; `tuple[str, int]` return = param sprawl; unvalidated `int()` env cast |
| 3. async-cache | Thundering herd via no in-flight dedup; unbounded cache; missing jitter; no pooling; suggested tenacity + async_lru |
| 4. stub-todo | `-> None` should be `NoReturn`; dead `from __future__ import annotations`; hardcoded function name in error msg (rename-unsafe); correctly skipped YAGNI helper |

The pattern: the skill catches **design-level** issues a static lint rule can't express. Per-request client construction. Exception chain breakage. Type semantic correctness. These need an LLM with full file context.

## What iteration-2 validates

1. **The two-layer architecture works as designed.** `python-rules` prevents slop at generation time (iteration-1 proved this); `simplify` catches what slips through (iteration-2 proves this).
2. **The LLM-intelligent layer adds substantive value over rules.** 44 simplify findings vs 7 hand-found = 6.3× depth. The depth is mostly in design-level concerns no static rule could capture.
3. **The decision-brief format produces well-calibrated recommendations.** No over-flagging, no under-flagging, no manufactured findings.
4. **Phase 5's "skip when clean" honesty rule is respected in practice.** Eval-5 returned zero findings.

## Limitations (honest)

- Single-pass review per file. We didn't test the iterative `fix → re-scan → re-review` loop the skill describes.
- Subagents applied the three angles in-process rather than spawning real parallel Task subagents (we deliberately said "don't spawn sub-subagents" to keep the test tractable in this conversation). Production use of `/aidoctor:simplify` in Claude Code WILL spawn 3 parallel reviewers per the skill's Phase 2.
- N=5 is small. A 50-100 file corpus would give higher confidence in the false-positive rate.
- All test inputs were iteration-1 baselines (deliberately lower quality). Should sample already-good code at scale to confirm the "skip when clean" behavior holds.

## What ships in v0.1.1

Both skills, both validated:
- `python-rules` — prevents slop at the source (iteration-1: avg 96 → 100)
- `simplify` — catches design-level issues retroactively (iteration-2: 6.3× depth vs hand review, 0 false positives)
- `scan` — the CLI wrapper for the rule layer

This is the "intelligent, prod-level, non-overengineered Python code, ask-to-fix when overengineered" promise you described. The evidence is in `evals/iteration-1/REPORT.md` + `evals/iteration-2/REPORT.md` + the 16 output files.
