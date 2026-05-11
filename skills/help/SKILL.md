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
aidoctor — 4 skills + 1 CLI, for Python that AI agents tend to write badly.

WHAT YOU WANT                       WHAT TO INVOKE
─────────────────────────────────── ────────────────────────────────────
Write Python (no action needed)     python-rules auto-loads
Review your last changed code       /aidoctor:simplify
One-file or one-path lint check     /aidoctor:scan
Whole-project deep audit            /aidoctor:audit
Browse all 25 rules                 /aidoctor:rules
Explain one rule                    aidoctor scan --explain <rule-id>
CI / pre-commit lint                aidoctor scan . in your pipeline

NATURAL LANGUAGE ALSO WORKS
─────────────────────────────────── ────────────────────────────────────
"audit this repo"                   triggers /aidoctor:audit
"simplify what I just changed"      triggers /aidoctor:simplify
"scan this"                         triggers /aidoctor:scan
"list aidoctor rules"               triggers /aidoctor:rules

FIRST-TIME USE
─────────────────────────────────── ────────────────────────────────────
1. Say "audit this repo" to get a six-dimensional review.
2. Pick "fix tier 1 only" when prompted.
3. Re-audit. Watch the score move.
```

Then stop. Do not offer to run any of them. The user picks next.
