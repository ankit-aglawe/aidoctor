---
name: help
version: 0.2.0
description: Print the aidoctor catalog and decision tree. Use when the user types `/aidoctor:help` or asks "help me with aidoctor", "what aidoctor commands exist?", "how do I get started?".
triggers:
  - aidoctor help
  - help me with aidoctor
  - aidoctor commands
  - how do I use aidoctor
disable-model-invocation: true
---

# /aidoctor:help

Print the catalog and a decision tree. This is the explicit entry point — users who don't know what to invoke type `/aidoctor:help` and get oriented.

## Output

Print this exactly (in plain Markdown):

```
aidoctor — the coding harness that catches what your AI agent writes badly.

THE MOAT
─────────────────────────────────── ────────────────────────────────────
Remove visible AI fingerprints      /aidoctor:deai          (headline)
   (NOTE labels, emojis in code,
    section dividers, self-praise,
    hedge leakage)

EVERYTHING ELSE
─────────────────────────────────── ────────────────────────────────────
Write Python (no action needed)     python-rules auto-loads
Review your last changed code       /aidoctor:simplify
One-file or one-path lint check     /aidoctor:scan
Whole-project deep audit            /aidoctor:audit
Browse rules                        /aidoctor:rules
Set up pre-commit hook              aidoctor install --pre-commit
Explain one rule                    aidoctor scan --explain <rule-id>
CI / pre-commit lint                aidoctor scan . in your pipeline

NATURAL LANGUAGE ALSO WORKS
─────────────────────────────────── ────────────────────────────────────
"deai this file" / "remove AI tells"  triggers /aidoctor:deai
"audit this repo"                     triggers /aidoctor:audit
"simplify what I just changed"        triggers /aidoctor:simplify
"scan this"                           triggers /aidoctor:scan

FIRST-TIME USE
─────────────────────────────────── ────────────────────────────────────
1. Say "deai this file" on any AI-generated Python — watch the
   NOTE labels, emojis, and section dividers disappear.
2. Say "audit this repo" for the full six-dimensional review.
3. Say "install pre-commit" to wire aidoctor into your git workflow.
```

Then stop. Do not offer to run any of them. The user picks next.
