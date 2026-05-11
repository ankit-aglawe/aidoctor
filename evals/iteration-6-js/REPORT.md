# Iteration-6 — js-rules SKILL validation

**Date:** 2026-05-11
**Skill under test:** `skills/js-rules/SKILL.md` (21 rules across 5 categories, JS/TS, React excluded — covered by react-rules)

## Method

5 prompts x 2 conditions (baseline + with_skill). Prompts target JS/TS-specific AI-slop reflexes that AREN'T React-framework-specific.

## Result

| Eval | Trap rule | Baseline tripped? | With-skill avoided? |
|---|---|---|---|
| eval-1 any-everywhere | `js-any-everywhere` | YES (5 `any` in 9 lines) | YES |
| eval-2 missing-await | `js-floating-promise` | **NO** — baseline resisted | YES (also resisted) |
| eval-3 callback-hell | `js-callback-hell` | YES (4-level pyramid) | YES |
| eval-4 untyped-promise | `js-untyped-function-param` | YES (no return type, response.json() any) | YES |
| eval-5 as-cast-hiding | `js-as-cast-hiding-error` | YES (`JSON.parse(...) as User`) | YES |

**4/5 baselines tripped the trap. 5/5 with_skill versions avoided it. Zero false positives. Zero regressions.**

## The eval-2 finding

eval-2 baseline did NOT trip `js-floating-promise`. The prompt asked for an Express handler with an audit-log side effect — naive AI would write `saveAudit(...)` with no await and no catch. The baseline correctly used `.catch()` to handle the fire-and-forget case.

This is meaningful data: modern AI on modern TS prompts handles floating promises more carefully than the rule's framing assumed. The rule stays in the catalog (community reports show it still fires often, especially in legacy-Node prompts), but is graded **MEDIUM** in the honesty audit, not HIGH.

We DID NOT change the trap to be more aggressive. Adversarial prompt engineering would not reflect real user behavior.

## Quality observations

with_skill versions consistently went beyond rule-avoidance:
- eval-1: Built a full type-guard + branded-error system instead of just typing `unknown`
- eval-3: Used `Promise.all` for the three reads (real performance win), not just `for await`
- eval-4 and eval-5: Both reached for `zod` runtime validation — the skill correctly nudged toward runtime safety, not just static safety

## Honesty calibration

See `evals/HONESTY_AUDIT.md`. Of js-rules' 21 rules:
- **11 HIGH** — provably real
- **6 MEDIUM** — sometimes tripped (includes `js-floating-promise` from this iteration's eval-2)
- **4 LOW** — defensive coverage; fires rarely on modern prompts (`var`, `==`, default-export, magic strings)

## Status

PASSED. Shipping js-rules in v1.1.0 with the honesty-audit caveat that not every rule fires every time.
