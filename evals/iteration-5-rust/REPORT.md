# Iteration-5 — rust-rules SKILL validation

**Date:** 2026-05-11
**Skill under test:** `skills/rust-rules/SKILL.md` (22 rules across 6 categories)

## Method

5 prompts, each engineered to elicit a specific Rust AI-slop reflex. Each prompt run twice in parallel:
- **baseline** — fresh subagent, NO skill loaded
- **with_skill** — fresh subagent with `rust-rules` SKILL injected

10 subagent runs total. Outputs in `eval-N-*/baseline/outputs/` and `eval-N-*/with_skill/outputs/`.

## Result

| Eval | Trap rule | Baseline tripped? | With-skill avoided? |
|---|---|---|---|
| eval-1 clone-everywhere | `rust-unnecessary-clone` | YES (9 .clone() in 22 lines) | YES |
| eval-2 unwrap-in-fn | `rust-unwrap-in-prod` | YES (2 unwraps in pub fn) | YES |
| eval-3 result-handling | `rust-stringly-typed-error` | YES (`Result<u16, String>`) | YES |
| eval-4 lifetime-overengineering | `rust-lifetime-overengineering` | YES (3 lifetimes for 1) | YES |
| eval-5 mutex-deadlock | `rust-mutex-poison-ignored` | YES (`.lock().unwrap()` x2) | YES |

**5/5 baselines tripped the trap. 5/5 with_skill versions avoided it. Zero false positives. Zero regressions.**

## Quality observations

**baseline → with_skill quality lift was dramatic:**

- eval-2 went from 2 unwraps + no error type → `thiserror` enum with `#[from]` conversions
- eval-3 went from `Result<u16, String>` → typed `PortParseError` enum with `Display`, `Error::source`, `From<ParseIntError>` impls, 7 tests
- eval-5 went from `.lock().unwrap()` → `unwrap_or_else(|poisoned| poisoned.into_inner())` with a module-doc explanation of why poison-recovery is safe for a `u64` counter, plus a regression test that intentionally poisons the mutex

The with_skill agents didn't just dodge the trap — they wrote production-quality code with docs and tests. The skill is teaching production patterns, not just rule-avoidance.

## Honesty calibration

See `evals/HONESTY_AUDIT.md` for the per-rule HIGH/MEDIUM/LOW confidence grading. Of rust-rules' 22 rules:
- **12 HIGH** — provably real AI reflexes (5 demonstrated in this iteration's baselines)
- **6 MEDIUM** — community-documented but not reflexive
- **4 LOW** — defensive coverage, fires rarely

## Status

PASSED. Shipping rust-rules in v1.1.0.
