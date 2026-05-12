# AI-slop pattern inventory — multi-language research

**Method:** 10 parallel subagents researched AI-slop patterns specific to their
assigned language (or cross-language universal). Each produced a structured
inventory with rule_id, evidence source, confidence, example, fix, and FP risk
notes. Sources include canonical lints (clippy, ESLint, RuboCop, SwiftLint,
SpotBugs/PMD/ErrorProne, gosec, ShellCheck, clang-tidy), academic papers
(arxiv 2409.19182), industry reports (Veracode, Pangram, CodeRabbit), and the
Wikipedia "Signs of AI writing" canonical reference.

**Date:** 2026-05-12
**Subagents:** Python, Rust, Go, JS/TS, React/JSX, Java, Swift, Ruby, C/C++, Shell, Universal

---

## High-confidence refinements to EXISTING aidoctor rules

These rules have known FP risk validated by real-world testing. Refine before
shipping v2.0:

### Python (v1.1, 25 rules)

| Rule | Action | Reason |
|---|---|---|
| `missing-return-type` | REFINE | Only fire if file is typing-aware (any other annotation present). 172 FPs in `requests` confirms current rule too aggressive. |
| `import-without-use` | REFINE | Respect `__all__` re-exports. 73 FPs in real-world test. |
| `conditional-import-outside-try` | REFINE | Skip if any sibling `try/except ImportError` exists in file. 34 FPs in flask. |
| `any-everywhere` | REFINE | Only when `Any` is the SOLE annotation in a fn signature, not mixed. 17 FPs in httpx. |
| `wildcard-import` | REFINE | Exempt `__init__.py` files (canonical re-export idiom). 16 FPs. |
| `generic-without-typevar` | CONSIDER DROP | LOW yield; AI rarely reflexively hits this. |
| `repeated-dict-lookup`, `nested-loop-append` | Note LOW-yield | Not strongly AI-specific; humans hit equally. |

### Rust (22 rules)

| Rule | Action | Reason |
|---|---|---|
| `rust-unwrap-in-prod` | REFINE | Gate to non-binary crates + non-test code. Allow when preceded by a `// SAFETY:`-style justification comment. Currently flags ripgrep's legitimate uses. |
| `rust-trait-object-when-generic-works` | DOWNGRADE to LOW | AI doesn't reflexively pick `Box<dyn>` over `impl Trait`. |
| `rust-derive-omission` | REFINE | Only enforce `Debug` on `pub` items. Many types intentionally aren't `Clone`/`PartialEq`. |
| `rust-needless-return` | CONSIDER DROP | Clippy-style territory, not AI-slop. |

### Go (20 rules)

| Rule | Action | Reason |
|---|---|---|
| `go-loop-var-capture` | REFINE | Gate on module's `go` directive. Skip silently on Go 1.22+ (language fixed the bug). Currently FPs on modern code. |
| `go-slice-append-aliasing` | REFINE | Split: keep "discarded append" half (HIGH). Drop "shared-cap aliasing" half (not detectable syntactically without taint analysis). |
| `go-context-not-propagated` | REFINE | Narrow to functions that call I/O packages (`net/http`, `database/sql`, `os/exec`, `io.*`). Otherwise FPs on data-struct helpers. |
| `go-init-abuse`, `go-make-without-capacity` | Note LOW-yield | Real but rarely AI-reflexive. |
| `go-time-now-in-test` | REFINE | Only fire in `_test.go` adjacent prod paths. |

### JavaScript/TypeScript (21 rules)

| Rule | Action | Reason |
|---|---|---|
| `js-default-export-mixed` | DROP | Next.js page/layout/route files REQUIRE default export. Current rule FPs on every Next.js app. |
| `js-magic-string-import-path` | DROP | Project-specific, not an AI reflex (HONESTY_AUDIT already flagged as LOW). |
| `js-await-in-loop` | REFINE | Exempt sequential dependent loops (rate-limited APIs, cursor pagination). |
| `js-console-log-shipped` | REFINE | Exempt `bin/`, `scripts/`, `cli/` paths where stdout IS the API. |
| `js-enum-instead-of-union` | REFINE | NestJS + Prisma idiomatically use `enum`; high FP without exemption. |

### React (19 rules)

| Rule | Action | Reason |
|---|---|---|
| `react-inline-object-prop` | REFINE | Scope to memo'd children, Context.Provider `value`, or hot-list children. Current ban-all form FPs on every Next.js docs example. |
| `react-mixed-concerns` | REFINE → advisory | Subjective. Never flag components < 100 LOC. |
| `react-god-component` | REFINE | Raise threshold to 300 LOC or gate on cyclomatic complexity. |

---

## High-confidence NEW patterns to add

These are NEW patterns NOT currently in any aidoctor rule pack, each with
documented evidence and clear detection feasibility.

### Universal cross-language (target: 5/5 supported langs + future langs)

| ID | Pattern | Confidence | Evidence |
|---|---|---|---|
| `ai-marketing-vocab` | Marketing/promo adjectives in comments (`comprehensive`, `leverage`, `seamless`, `robust`, `delve`, `showcase`, `vibrant`, `intricate`, `pivotal`, `underscore`, `tapestry`, `meticulous`, `boasts`) | HIGH | Wikipedia signs-of-AI |
| `ai-conjunctive-opener` | Comments starting `Furthermore,` / `Moreover,` / `Additionally,` / `Notably,` / `In conclusion,` | HIGH | Wikipedia signs-of-AI |
| `ai-em-dash-overuse` | 2+ em-dashes in a single comment | HIGH | Wikipedia signs-of-AI |
| `ai-broad-catch-trivial` | try/except wrapping ≤2 simple statements with broad catch | HIGH | arxiv 2409.19182; Pangram |
| `ai-test-credential` | Literal `sk-test-`, `sk-ant-`, `AKIA`, `ghp_`, `xoxb-`, `password = "password123"`, `API_KEY = "your-key-here"` | HIGH | aviator slop guide |
| `ai-todo-without-ticket` | `TODO`/`FIXME`/`XXX`/`HACK` without `(name)`/`#123`/`JIRA-`/URL within ~40 chars | HIGH | aviator |
| `ai-stub-body-comment` | `// your code here`, `# implement this`, `// placeholder`, `// fill in`, `pass  # TODO` | HIGH | already partial in aidoctor; expand cross-lang |
| `ai-inflated-test-name` | Test identifiers >60 chars with `should`/`correctly`/`successfully`/`properly`/`for_all_` | MED | dev.to 164-signals |
| `ai-rule-of-three-padding` | Comma-separated adjective triplets in comments (`fast, reliable, and scalable`) | MED | agent-style RULE-9 |
| `ai-negative-parallelism` | `// not just X, but Y` / `// rather than X, we Y` patterns | MED | Wikipedia signs-of-AI |

### Python new (beyond existing 25)

| ID | Confidence | Evidence | Notes |
|---|---|---|---|
| `ai-useless-docstring` | HIGH | pydocstyle D401/D205 | Lexical-overlap heuristic; docstring vs signature words |
| `ai-mutable-default-arg` | HIGH | ruff B006 | The canonical Python footgun AI still emits |
| `ai-unused-fstring` | HIGH | ruff F541 | Near-zero FPs |
| `ai-print-traceback-instead-of-raise` | HIGH | bandit B110 adjacent | Notebook habit leaking into prod |
| `ai-assert-in-prod` | HIGH | bandit B101 | Stripped by `python -O`; not safety |
| `ai-overzealous-typing-import` | HIGH | ruff UP006/UP007/UP035 | Pre-3.9 stdlib generics; gate on `requires-python` |
| `ai-getter-setter-pythonic` | HIGH | Effective Python | Java/C# habit; use `@property` |
| `ai-overcatch-then-reraise` | HIGH | ruff TRY201/TRY302 | `raise e` with no context added |
| `ai-datetime-now-no-tz` | HIGH | flake8-datetimez DTZ005 | Tutorial code; needs tz-aware |
| `ai-pip-install-in-code` | HIGH | own observation | Notebook-cell habit |
| `ai-dict-keys-iter` | HIGH | ruff SIM118 | `for k in d.keys()` when value not used |
| `ai-logger-print-mix` | MED | own observation | Module mixes `print()` + `logger.info` |
| `ai-overengineered-init` | MED | own observation | 10+ Optional params; should be dataclass |
| `ai-magic-number-retry` | HIGH | own observation | Hardcoded retry loops; use tenacity |

### Rust new (beyond existing 22)

| ID | Confidence | Evidence | Notes |
|---|---|---|---|
| `rust-mutex-guard-held-across-await` | HIGH | clippy `await_holding_lock` | Sync mutex + .await = deadlock or !Send |
| `rust-box-dyn-error-in-library` | HIGH | Effective Rust Item 4 | Dodges typed-error design |
| `rust-anyhow-in-library-api` | MED | anyhow README | Copy-paste app→lib mistake |
| `rust-let-underscore-on-result` | HIGH | clippy `let_underscore_must_use` | Silently swallowed Result |
| `rust-question-mark-on-option-in-result-fn` | MED | community | Assumes `?` "just works" |

### Go new (beyond existing 20)

| ID | Confidence | Evidence | Notes |
|---|---|---|---|
| `go-defer-in-loop` | HIGH | gocritic deferInLoop | Defer doesn't fire per iteration → fd leak |
| `go-defer-before-err-check` | HIGH | golang/go#17780 | `defer resp.Body.Close()` before checking err → nil-deref panic |
| `go-http-body-not-closed` | HIGH | golangci-lint bodyclose | Goroutine + conn leak |
| `go-fmt-errorf-verb-v` | HIGH | golangci-lint errorlint | `%v` instead of `%w` breaks errors.Is/As |
| `go-context-background-midchain` | MED-HIGH | contextcheck | Reach for Background() instead of propagating ctx |
| `go-weak-crypto` | HIGH | gosec G401, G501-G505 | md5 for password hashing |
| `go-rand-without-crypto` | HIGH | gosec G404 | math/rand for tokens/IDs/sessions |
| `go-sql-string-format` | HIGH | gosec G201/G202 | SQL string concatenation = SQLi |
| `go-log-fatal-in-library` | HIGH | revive `deep-exit` | log.Fatal outside main pkg |
| `go-filepath-tainted` | MED | gosec G304 | Path traversal from req params |

### JavaScript/TypeScript new (beyond existing 21)

| ID | Confidence | Evidence | Notes |
|---|---|---|---|
| `ts-async-array-method` | HIGH | typescript-eslint no-misused-promises | `arr.forEach(async x => ...)` discards |
| `ts-async-condition` | HIGH | typescript-eslint | `if (somePromise) {...}` always truthy |
| `js-mutate-then-return` | MED | functional / no-param-reassign | Silent state corruption (React) |
| `ts-return-promise-any` | HIGH | iter-6 baseline | `Promise<any>` hedge when type uncertain |
| `js-async-iife-fire-and-forget` | MED | eslint-plugin-promise | Top-level async without .catch |
| `js-zero-runtime-validation` | HIGH | community zod pressure | `as SignupReq` on req.body |

### React new (beyond existing 19)

| ID | Confidence | Evidence | Notes |
|---|---|---|---|
| `react-conditional-hook` | HIGH | rules-of-hooks | Hook inside if/early-return |
| `react-onclick-invocation` | HIGH | react.dev events | `onClick={handler()}` fires on every render |
| `react-server-client-mixed` | HIGH | @next/next | Importing client API without `"use client"` |
| `react-async-client-component` | HIGH | @next/next/no-async-client-component | `async function Page()` with `"use client"` |
| `react-state-any` | HIGH | typescript-eslint | `useState<any>([])` or untyped `useState([])` |
| `react-effect-as-event-handler` | HIGH | react.dev "You Might Not Need an Effect" | useEffect responding to event, not state |
| `react-usestate-for-ref-value` | MED | react.dev refs | useState for timer IDs / DOM refs |
| `react-direct-dom-manipulation` | MED | react/no-direct-mutation | `document.querySelector` in component body |
| `react-children-prop-any` | MED | @types/react | `children: any` instead of ReactNode |
| `react-fragment-shorthand` | LOW | react/jsx-fragments | `<React.Fragment>` when `<>` works |

---

## New-language verdicts

Which languages should aidoctor add support for after the v2.0 multi-lang core ships?

| Language | Priority | Verdict |
|---|---|---|
| **Java** | **TOP** | Veracode 2025: Java AI-slop has 70%+ failure rate (worst of any language tested). tree-sitter-java mature (ABI 14, Jan 2025 update). SpotBugs/PMD/ErrorProne provide oracle for A/B validation. Spring Boot ecosystem widely AI-assisted. ~20-25 high-quality rules feasible. |
| **C/C++** | **HIGH** | Worst blast radius (UB, RCE, memory corruption). clang-tidy provides strong oracle. tree-sitter-cpp/c mature. Caveats: need C-vs-C++ file mode, standard-version awareness, `--profile=embedded` toggle. |
| **Ruby** | MED | Declining greenfield but huge installed base (Shopify/GitLab/Stripe/Discourse/Mastodon). tree-sitter-ruby mature. Rails-context FPs need carve-outs. |
| **Shell/Bash** | MED | AI is genuinely bad at shell (SC2086 the most-fired ShellCheck warning). High blast radius on `rm -rf $var` / `sudo eval`. ShellCheck exists — aidoctor's edge is AI-slop layered ON TOP (stub comments, hardcoded paths, missing strict mode). tree-sitter-bash mature. |
| **Swift** | MED-LOW | iOS dev population smaller. Xcode+SwiftLint cover 70% in-IDE. High-value rules (Keychain for secrets, MainActor migration, force-unwrap) NOT in default SwiftLint — could be genuine differentiators. tree-sitter-swift mature. Defer unless iOS users appear in adoption telemetry. |

---

## What this research changes for the v2.0 plan

The CEO plan at `~/.gstack/projects/doctor/ceo-plans/2026-05-12-multilang-v2.md`
already covers:
- Multi-language scanner via tree-sitter
- 5 ai_style rules ported across 5 langs
- Per-language OWASP-flavored security pack

This research adds:

1. **Refinement work BEFORE shipping v2.0 multi-lang.** ~12 existing rules across all 5 packs have known FP issues that need targeted fixes. Estimated effort: ~1.5 CC days.

2. **New universal rules.** ~10 cross-language AI fingerprints (marketing vocab, em-dash overuse, broad catch on trivial, conjunctive openers, etc.) that work on any language. Each is ~1 JSONL entry + per-language comment-syntax adapter.

3. **New per-language HIGH-confidence rules.** ~30-40 new rules across Python/Rust/Go/JS/TS/React backed by canonical lint evidence. Each ships with HONESTY_AUDIT entry + A/B eval.

4. **Future-language roadmap.** Java + C/C++ are the next priorities after v2.0 ships. tree-sitter parsers exist for both. Defer beyond v2.0.

---

## Sources (consolidated)

**Universal AI-writing patterns:**
- Wikipedia: Signs of AI writing (`https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing`)
- TechCrunch: best guide to spotting AI writing (2025)
- Pangram: AI Code Detector blog

**Academic / industry:**
- arxiv 2409.19182: AI-Generated Code Considered Harmful
- arxiv 2512.05239: A Survey of Bugs in AI-Generated Code
- Veracode 2025 GenAI report (Java 70%+ failure rate)
- CodeRabbit: State of AI vs Human Code Generation
- Ardura Consulting: AI-generated code security analysis

**Canonical linter catalogs:**
- ruff (Python) — rule database
- pylint, bandit, flake8 + ecosystem plugins
- clippy (Rust) — lint groups + nursery
- golangci-lint, gosec, staticcheck (Go)
- typescript-eslint, eslint-plugin-react, eslint-plugin-react-hooks
- @next/next eslint plugin
- SpotBugs, PMD, ErrorProne, Checkstyle (Java)
- SwiftLint (Swift)
- RuboCop, Brakeman (Ruby)
- clang-tidy, cppcheck (C/C++)
- ShellCheck (Shell)

**Community / blogs:**
- aviator.co — how-to-avoid-ai-code-slop
- variantsystems.io — 10 anti-patterns in AI-generated codebases
- Hacking with Swift — what to fix in AI-generated Swift
- gigamind.dev — AI breaking Rails code
- simplermachines.com — how to write better Bash than ChatGPT

---

## Methodology disclosure

Each subagent had ~15 minutes (~600 word output cap) to:
- Skim aidoctor's existing rules for their language
- WebSearch for AI-slop in that language
- Cross-reference canonical lints
- Produce verdicts on existing rules + new patterns + new-language consideration

Limitations: no real-world A/B testing was performed in this research phase
(that happens in Phase 4 of the plan). Confidence ratings are subagent
assessments based on evidence + community signal, not yet validated against
real codebases. Real-world FP testing per language is mandatory before any
new rule ships.
