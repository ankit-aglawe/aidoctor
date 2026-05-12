# Real-world false-positive test report (v2.0, multi-language)

Per-rule occurrence count on well-maintained pre-AI codebases across
all 5 supported languages (Python, Rust, Go, JavaScript, TypeScript).
Any rule with >0 hits across these is producing **false positives**
unless we can manually justify each occurrence as a real AI fingerprint.

Reproduce: `uv run python evals/real_world_fp/run_fp_test.py`


## requests @ `v2.32.3`
Files scanned: **18** · Findings: **70** · Unique rules: **9**

| Rule | Severity | Occurrences |
|---|---|---|
| `import-without-use` | warning | 32 |
| `missing-return-type` | warning | 15 |
| `todo-without-ticket` | warning | 7 |
| `ai-useless-docstring` | warning | 5 |
| `ai-section-divider` | warning | 4 |
| `ai-generic-vars-in-long-fn` | warning | 3 |
| `nested-loop-append` | warning | 2 |
| `stub-comment` | error | 1 |
| `repeated-dict-lookup` | warning | 1 |

## flask @ `3.0.3`
Files scanned: **24** · Findings: **44** · Unique rules: **12**

| Rule | Severity | Occurrences |
|---|---|---|
| `conditional-import-outside-try` | warning | 17 |
| `except-exception-swallowing` | warning | 5 |
| `duplicate-import` | warning | 4 |
| `import-without-use` | warning | 4 |
| `ai-useless-docstring` | warning | 3 |
| `eval-or-exec-on-non-constant` | warning | 2 |
| `pickle-loads-on-non-constant` | warning | 2 |
| `repeated-dict-lookup` | warning | 2 |
| `todo-without-ticket` | warning | 2 |
| `bare-except-pass` | error | 1 |
| `nested-loop-append` | warning | 1 |
| `ai-obvious-type-annotation` | warning | 1 |

## httpx @ `0.27.2`
Files scanned: **24** · Findings: **44** · Unique rules: **16**

| Rule | Severity | Occurrences |
|---|---|---|
| `conditional-import-outside-try` | warning | 8 |
| `ai-useless-docstring` | warning | 6 |
| `duplicate-import` | warning | 5 |
| `any-everywhere` | warning | 4 |
| `nested-loop-append` | warning | 3 |
| `except-exception-swallowing` | warning | 3 |
| `ai-section-divider` | warning | 3 |
| `str-concat-in-loop` | warning | 2 |
| `import-without-use` | warning | 2 |
| `repeated-dict-lookup` | warning | 2 |
| `stub-comment` | error | 1 |
| `todo-without-ticket` | warning | 1 |
| `ai-emphasis-label` | warning | 1 |
| `ai-obvious-type-annotation` | warning | 1 |
| `ai-generic-vars-in-long-fn` | warning | 1 |
| `ai-rule-of-three-padding` | warning | 1 |

## ripgrep @ `14.1.1`
Files scanned: **20** · Findings: **3** · Unique rules: **2**

| Rule | Severity | Occurrences |
|---|---|---|
| `ai-conjunctive-opener` | warning | 2 |
| `rust-unsafe-without-safety-comment` | warning | 1 |

## cobra @ `v1.8.1`
Files scanned: **36** · Findings: **7** · Unique rules: **4**

| Rule | Severity | Occurrences |
|---|---|---|
| `ai-todo-without-ticket-multilang` | warning | 4 |
| `ai-section-divider` | warning | 1 |
| `ai-emphasis-label` | warning | 1 |
| `ai-rule-of-three-padding` | warning | 1 |

## express @ `4.19.2`
Files scanned: **11** · Findings: **1** · Unique rules: **1**

| Rule | Severity | Occurrences |
|---|---|---|
| `ai-todo-without-ticket-multilang` | warning | 1 |

## Aggregate across all repos

Total files scanned: **133**

| Rule | Total occurrences across repos |
|---|---|
| `import-without-use` | 38 |
| `conditional-import-outside-try` | 25 |
| `missing-return-type` | 15 |
| `ai-useless-docstring` | 14 |
| `todo-without-ticket` | 10 |
| `duplicate-import` | 9 |
| `ai-section-divider` | 8 |
| `except-exception-swallowing` | 8 |
| `nested-loop-append` | 6 |
| `repeated-dict-lookup` | 5 |
| `ai-todo-without-ticket-multilang` | 5 |
| `ai-generic-vars-in-long-fn` | 4 |
| `any-everywhere` | 4 |
| `stub-comment` | 2 |
| `eval-or-exec-on-non-constant` | 2 |
| `pickle-loads-on-non-constant` | 2 |
| `ai-obvious-type-annotation` | 2 |
| `str-concat-in-loop` | 2 |
| `ai-emphasis-label` | 2 |
| `ai-rule-of-three-padding` | 2 |
| `ai-conjunctive-opener` | 2 |
| `bare-except-pass` | 1 |
| `rust-unsafe-without-safety-comment` | 1 |
