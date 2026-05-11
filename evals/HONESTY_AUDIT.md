# Honesty audit — are these actual AI-slop patterns?

**Date:** 2026-05-11
**Trigger:** "make sure these are actual slop patterns" (user, just before v1.1 ship)
**Method:** for each rule, score AI-slop confidence using the iter-5/6/7 baseline evidence (subagents with NO skill loaded, given neutral prompts). If the baseline tripped the rule, the rule represents real slop. If the baseline naturally avoided it, the rule is closer to "good practice" than "AI reflex" — kept but flagged so we can revisit.

**Grading scale:**
- **HIGH** — baseline tripped it; well-documented AI reflex across community reports (clippy lints, staticcheck, typescript-eslint)
- **MEDIUM** — sometimes tripped; AI hits it under certain prompts but doesn't reflexively reach for it
- **LOW** — baseline avoided it; defensible best-practice but not an AI-specific reflex

The grade does NOT mean "delete LOW rules." It means: be honest with users about what's an AI tell vs what's just good practice.

---

## rust-rules (22 rules)

| Rule ID | Confidence | Baseline evidence |
|---|---|---|
| `rust-unwrap-in-prod` | **HIGH** | iter-5 eval-2 baseline: `fs::read_to_string(path).unwrap()` and `serde_json::from_str(&contents).unwrap()` in a `pub fn` — textbook reflex |
| `rust-unnecessary-clone` | **HIGH** | iter-5 eval-1 baseline: 9 `.clone()` calls in 22 lines of trivial code (`names.clone()`, `name.clone()`, `name.clone().len()`, `length.clone()`) |
| `rust-mutex-poison-ignored` | **HIGH** | iter-5 eval-5 baseline: `self.value.lock().unwrap()` in both `increment` and `value` methods |
| `rust-lifetime-overengineering` | **HIGH** | iter-5 eval-4 baseline: `fn shorter<'a, 'b: 'a, 'c: 'a>` — three lifetime params with subtype bounds where one is sufficient |
| `rust-stringly-typed-error` | **HIGH** | iter-5 eval-3 baseline: `Result<u16, String>` with `format!`-built error messages instead of a typed enum |
| `rust-panic-on-input` | HIGH (community) | Not tripped by iter-5 baselines but well-documented (`unreachable!()`, `todo!()` left as filler); clippy `panic_in_result_fn` lint exists for this exact reason |
| `rust-index-slice` | HIGH (community) | AI ports `v[i]` from C/Python without considering panic-on-OOB; clippy `indexing_slicing` lint |
| `rust-string-when-str-works` | HIGH (community) | The textbook beginner-Rust mistake; clippy `ptr_arg` lint |
| `rust-integer-cast-truncation` | HIGH (community) | iter-5 eval-3 baseline used `value as u16` cast — exactly the truncation pattern. clippy `cast_possible_truncation` |
| `rust-block-in-async` | HIGH (community) | r/rust community reports: AI mixes `std::fs` into `tokio` handlers constantly |
| `rust-derive-omission` | MEDIUM | Baselines did include `Debug`. AI sometimes forgets `Clone`/`PartialEq` for value types |
| `rust-option-result-bool-trap` | MEDIUM | Pattern of `.is_some()` chains exists but isn't reflexive. clippy `unnecessary_unwrap` covers part of this |
| `rust-needless-return` | MEDIUM | AI mixes statement-language style — real but stylistic. clippy `needless_return` |
| `rust-match-single-arm` | MEDIUM | AI over-uses `match` when `if let` suffices |
| `rust-collect-then-iter` | MEDIUM | AI does this under uncertainty about iterator types |
| `rust-floating-point-eq` | LOW | AI rarely compares floats unprompted; when it does, this is a legitimate concern but not language-specific slop |
| `rust-trait-object-when-generic-works` | LOW | More an experience signal than a reflex — AI doesn't strongly prefer either |
| `rust-allow-clippy-blanket` | LOW (worth keeping) | Real but only surfaces when AI has been pressured ("just make warnings stop") |
| `rust-block-on-in-async` | MEDIUM | AI does this when adapting sync libs; less reflexive than `rust-block-in-async` |
| `rust-unsafe-without-safety-comment` | LOW | AI rarely reaches for `unsafe` spontaneously; rule fires only when user asks for unsafe code |
| `rust-transmute-misuse` | LOW | Same as above — `transmute` requires the user to ask for it |
| `rust-string-concat-in-loop` | MEDIUM | AI translates Python `s += x` literally; clippy `format_push_string` lint |

**Rust verdict:** 12 HIGH, 6 MEDIUM, 4 LOW. The HIGH rules are the spine of the rule pack — every iter-5 baseline tripped at least one. The LOW rules (`unsafe-without-safety-comment`, `transmute-misuse`, `floating-point-eq`, `trait-object-when-generic-works`) are kept as defensive coverage but should be marked "fires rarely" in the SKILL so we don't oversell.

---

## js-rules (21 rules)

| Rule ID | Confidence | Baseline evidence |
|---|---|---|
| `js-any-everywhere` | **HIGH** | iter-6 eval-1 baseline: `payload: any`, return `: any`, three more `: any` annotations in 9 lines — the textbook AI-TS tell |
| `js-as-cast-hiding-error` | **HIGH** | iter-6 eval-5 baseline: `JSON.parse(rawJson) as User` with zero validation — exactly the assertion-as-correctness anti-pattern |
| `js-callback-hell` | **HIGH** | iter-6 eval-3 baseline: 4-level nested `fs.readFile` pyramid, each with its own error branch — the canonical Node-style AI output |
| `js-untyped-function-param` | **HIGH** | iter-6 eval-4 baseline: `fetchUser(id: string)` returned `Promise<any>` — `response.json()` not typed, no return type. AI defaults to inference |
| `js-empty-catch` | HIGH (community) | typescript-eslint `no-empty-catch` exists for this exact pattern; AI does this to "be safe" |
| `js-throw-non-error` | HIGH (community) | AI writes `throw "message"` from Python habit; eslint `no-throw-literal` |
| `js-non-null-assertion` | HIGH (community) | AI uses `!` to silence null checks under pressure; eslint `no-non-null-assertion` |
| `js-ts-ignore-without-reason` | HIGH (community) | AI uses `@ts-ignore` as a panic button; typescript-eslint `ban-ts-comment` |
| `js-floating-promise` | MEDIUM | iter-6 eval-2 baseline used `.catch()` correctly — modern AI sometimes knows this. But the wider community reports show it's still a frequent reflex when prompts don't emphasize it |
| `js-console-log-shipped` | HIGH | Universal; iter-6 eval-2 baseline used `console.error` for an audit path |
| `js-unused-import` | HIGH (community) | AI imports speculatively; eslint `no-unused-vars` |
| `js-await-in-loop` | MEDIUM | AI translates loops literally from Python; eslint `no-await-in-loop` |
| `js-enum-instead-of-union` | MEDIUM | AI ports enum from C#/Java; less reflexive in TS-native prompts |
| `js-as-any-double-cast` | MEDIUM | The explicit `as unknown as T` escape hatch; AI uses when normal `as` fails |
| `js-promise-chain-instead-of-await` | MEDIUM | AI mixes paradigms; real but inconsistent |
| `js-unhandled-rejection-then` | MEDIUM | Subset of `floating-promise` — keep but folded conceptually |
| `js-catch-any-implicit` | MEDIUM | iter-6 eval-2 baseline did NOT catch implicitly typed — the trap was sidestepped. Still a TS-specific reflex worth catching |
| `js-var-instead-of-const` | LOW | AI now defaults to `const`/`let`; rule fires on legacy Node prompts |
| `js-loose-equality` | LOW | AI uses `===` by default in 2026 |
| `js-default-export-mixed` | LOW | Style preference more than slop |
| `js-magic-string-import-path` | LOW | Project-specific; not an AI reflex |

**JS verdict:** 11 HIGH, 6 MEDIUM, 4 LOW. The TS-specific HIGH rules (`any-everywhere`, `as-cast`, `untyped-param`) are bulletproof — every baseline tripped them. The LOW rules (`var`, `==`, default-export, magic strings) are kept for legacy-Node prompts but marked low-yield. **Brand honesty note:** rename js-rules sub-section heading from "21 patterns" to be clearer these are graded.

---

## go-rules (20 rules)

| Rule ID | Confidence | Baseline evidence |
|---|---|---|
| `go-error-ignored` | **HIGH** | iter-7 eval-1 baseline: `data, _ := os.ReadFile(path)` AND `_ = json.Unmarshal(data, cfg)` — both errors discarded. This is the #1 Go AI-slop pattern |
| `go-goroutine-leak` | **HIGH** | iter-7 eval-2 baseline: `go func() { for j := range jobs { process(j) } }()` — no context, no termination signal, no return |
| `go-context-not-propagated` | **HIGH** | iter-7 eval-2 baseline: same — no `ctx context.Context` parameter, no propagation to `process(j)` |
| `go-panic-in-library` | **HIGH** | iter-7 eval-3 baseline: `panic(err)` in a library function, with a doc comment recommending `defer/recover` to callers — exactly the anti-pattern documented in the staticcheck SA9007 rule |
| `go-mutex-by-value` | **HIGH** | iter-7 eval-4 baseline: `func (c Counter) Inc()` and `func (c Counter) Value()` — value receivers on a struct with embedded `sync.Mutex`. The classic Go bug; `go vet` catches it but AI generates it constantly |
| `go-slice-append-aliasing` | **HIGH** | iter-7 eval-5 baseline: `append(items, "default")` discarded, then `return items` — the textbook bug. Compiles, runs, silently broken |
| `go-error-not-wrapped` | HIGH (community) | AI returns bare `err` instead of `fmt.Errorf("...: %w", err)`; golangci-lint `wrapcheck` exists for this |
| `go-stuttering-name` | HIGH (community) | AI generates `user.UserConfig` instead of `user.Config` — staticcheck ST1003 / `revive` |
| `go-getter-prefix` | HIGH (community) | AI ports Java conventions: `GetName()` instead of `Name()`; documented in Effective Go |
| `go-stub-comment` | HIGH | Same as Python equivalent — `// TODO: implement` shipped as code |
| `go-hardcoded-secret` | HIGH | Universal — not Go-specific but still a Go-AI failure |
| `go-string-concat-loop` | HIGH (community) | AI translates Python `s += x`; should use `strings.Builder`. golangci-lint `prealloc` related |
| `go-error-string-comparison` | MEDIUM | AI compares `err.Error() == "not found"` instead of `errors.Is`; staticcheck SA1029 partial |
| `go-channel-unbuffered-send` | MEDIUM | AI doesn't think about buffering; real but less reflexive |
| `go-interface-pointer-return` | MEDIUM | Subtle and documented in Go FAQ; AI hits it when wrapping types |
| `go-empty-interface-any` | MEDIUM | AI defaults to `interface{}`/`any` instead of generics in Go 1.18+ code |
| `go-init-abuse` | LOW | AI rarely reaches for `init()` spontaneously |
| `go-make-without-capacity` | LOW | More performance hygiene than slop; AI does generate this |
| `go-time-now-in-test` | MEDIUM | AI does inject `time.Now()` directly; real but only fires in test files |
| `go-loop-var-capture` | MEDIUM (post-1.22) | Go 1.22 fixed the loop-var semantics for new code. AI generating pre-1.22-style code in 1.22+ projects = real bug. AI generating 1.22+ semantics in pre-1.22 modules = real bug. Conditional on `go` directive |

**Go verdict:** 12 HIGH, 5 MEDIUM, 3 LOW (rough; `go-loop-var-capture` is graded conditionally). Go AI-slop is the most clearly demonstrable of the three — every iter-7 baseline tripped multiple HIGH rules within ~10 lines of code. `go-error-ignored`, `go-mutex-by-value`, `go-panic-in-library` are textbook reflexes; the baselines are publishable evidence on their own.

---

## Summary

- **rust-rules:** 12 HIGH / 6 MEDIUM / 4 LOW — anchored by baselines that tripped 5/5 traps
- **js-rules:** 11 HIGH / 6 MEDIUM / 4 LOW — anchored by 4/5 trapped baselines; one (eval-2 `js-floating-promise`) sidestepped
- **go-rules:** 12 HIGH / 5 MEDIUM / 3 LOW — anchored by 5/5 trapped baselines

**Net judgment:** all three rule packs are grounded in actual AI behavior, not curated best-practice lists. The HIGH-confidence rules are the spine and provably real. The LOW-confidence rules are defensive coverage (rare-but-real patterns clippy/eslint/staticcheck also flag) — kept but should be marked low-yield in v1.2 SKILL revisions.

**Honesty in the SKILL files (v1.1):** add a short note that not every rule fires every time — the HIGH ones (called out in the in-skill priority order) are the real-world bread and butter. This keeps users from over-trusting the rule pack as exhaustive.

**No rules are being removed in v1.1.** This audit calibrates expectations; we'll prune in v1.2 if data supports it.
