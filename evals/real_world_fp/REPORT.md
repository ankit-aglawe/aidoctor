# Real-world false-positive test report

Per-rule occurrence count on well-maintained pre-AI Python codebases.
Any rule with >0 hits across these is producing **false positives**
unless we can manually justify each occurrence as a real AI fingerprint.

Reproduce: `uv run python evals/real_world_fp/run_fp_test.py`


## requests @ `v2.32.3`
Files scanned: **18** · Findings: **62** · Unique rules: **7**

| Rule | Severity | Occurrences |
|---|---|---|
| `import-without-use` | warning | 32 |
| `missing-return-type` | warning | 15 |
| `todo-without-ticket` | warning | 7 |
| `ai-section-divider` | warning | 4 |
| `nested-loop-append` | warning | 2 |
| `stub-comment` | error | 1 |
| `repeated-dict-lookup` | warning | 1 |

## flask @ `3.0.3`
Files scanned: **24** · Findings: **40** · Unique rules: **10**

| Rule | Severity | Occurrences |
|---|---|---|
| `conditional-import-outside-try` | warning | 17 |
| `except-exception-swallowing` | warning | 5 |
| `duplicate-import` | warning | 4 |
| `import-without-use` | warning | 4 |
| `eval-or-exec-on-non-constant` | warning | 2 |
| `pickle-loads-on-non-constant` | warning | 2 |
| `repeated-dict-lookup` | warning | 2 |
| `todo-without-ticket` | warning | 2 |
| `bare-except-pass` | error | 1 |
| `nested-loop-append` | warning | 1 |

## httpx @ `0.27.2`
Files scanned: **24** · Findings: **35** · Unique rules: **12**

| Rule | Severity | Occurrences |
|---|---|---|
| `conditional-import-outside-try` | warning | 8 |
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

## Aggregate across all repos

Total files scanned: **66**

| Rule | Total occurrences across repos |
|---|---|
| `import-without-use` | 38 |
| `conditional-import-outside-try` | 25 |
| `missing-return-type` | 15 |
| `todo-without-ticket` | 10 |
| `duplicate-import` | 9 |
| `except-exception-swallowing` | 8 |
| `ai-section-divider` | 7 |
| `nested-loop-append` | 6 |
| `repeated-dict-lookup` | 5 |
| `any-everywhere` | 4 |
| `stub-comment` | 2 |
| `eval-or-exec-on-non-constant` | 2 |
| `pickle-loads-on-non-constant` | 2 |
| `str-concat-in-loop` | 2 |
| `bare-except-pass` | 1 |
| `ai-emphasis-label` | 1 |
