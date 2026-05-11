# Iteration-7 — go-rules SKILL validation

**Date:** 2026-05-11
**Skill under test:** `skills/go-rules/SKILL.md` (20 rules across 5 categories)

## Method

5 prompts x 2 conditions (baseline + with_skill). Prompts target Go-specific AI-slop reflexes.

## Result

| Eval | Trap rule | Baseline tripped? | With-skill avoided? |
|---|---|---|---|
| eval-1 error-ignored | `go-error-ignored` | YES (`data, _ :=` + `_ = json.Unmarshal`) | YES |
| eval-2 goroutine-leak | `go-goroutine-leak` + `go-context-not-propagated` | YES (no ctx, no termination) | YES |
| eval-3 panic-in-lib | `go-panic-in-library` | YES (`panic(err)` + "use defer/recover" doc) | YES |
| eval-4 mutex-misuse | `go-mutex-by-value` | YES (value receivers on Mutex-embedded struct) | YES |
| eval-5 slice-append-bug | `go-slice-append-aliasing` | YES (`append(items,...)` discarded) | YES |

**5/5 baselines tripped the trap. 5/5 with_skill versions avoided it. Zero false positives. Zero regressions.**

## Why Go baselines are the cleanest evidence

Go AI-slop is uniquely demonstrable. Across 5 short prompts and 5 separate Sonnet-class subagents:

- 2 discarded errors with `_` in 5-line `LoadConfig`
- A worker goroutine with no `context.Context`, no termination, no error path
- A library function that `panic`s with a doc comment instructing callers to `defer/recover` (literally the staticcheck SA9007 anti-pattern, with the AI's own rationalization attached)
- Value receivers on a `sync.Mutex`-embedded struct (silently broken — the increment is lost, the mutex protects a copy)
- `append(items, "default")` with the result discarded (silently broken — returns the unmodified slice)

**The mutex and slice bugs are particularly damning:** they compile, they run, and they produce wrong answers. No Go user reviewing the diff casually would catch them. AI generates them reflexively.

## Quality observations

with_skill outputs were not just bug-avoidant but idiomatic:
- eval-1 wrapped errors with `%w` for `errors.Is`/`errors.As` unwrap chains
- eval-2 used `select` + `ctx.Done()` + the channel-receive `ok` check — the canonical Go cancellation pattern
- eval-3 guarded the empty-input edge case the prompt didn't even ask about
- eval-4 fixed the getter name (`Value()` not `GetValue()`) — bonus rule pickup
- eval-5 inlined the fix to a single line (no over-engineering)

## Honesty calibration

See `evals/HONESTY_AUDIT.md`. Of go-rules' 20 rules:
- **12 HIGH** — provably real (5 demonstrated in this iteration's baselines)
- **5 MEDIUM** — sometimes tripped
- **3 LOW** — defensive coverage

## Status

PASSED with the strongest baseline evidence of the three iterations. Shipping go-rules in v1.1.0.
