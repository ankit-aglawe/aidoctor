---
name: rules
version: 0.2.0
description: Show the user the aidoctor rule catalog or explain a single rule. Use when the user asks "what rules does aidoctor have?", "list all rules", "what does <rule-id> mean?", "explain <rule-id>", or "show me the rule catalog".
triggers:
  - list aidoctor rules
  - show all rules
  - what rules does aidoctor check
  - explain rule
  - what does this rule mean
benefits-from: [scan]
allowed-tools: Bash(aidoctor *), Bash(uvx aidoctor*), Read
---

# aidoctor rules

Show the rule catalog or explain a single rule.

## When to list all rules

User asked for a catalog, an overview, or "what does aidoctor check?". Run:

```bash
aidoctor rules
```

Filter if useful:

```bash
aidoctor rules --severity error       # just the must-fix rules
aidoctor rules --category secrets     # one category
aidoctor rules --json                 # machine-readable
```

Read the output back to the user. Group by category. Highlight severity (errors first).

## When to explain ONE rule

User asked "what does `bare-except-pass` mean?" or "explain hardcoded-api-key". Run:

```bash
aidoctor scan --explain <rule-id>
```

Output includes: severity, category, message, full help text, and the docs URL. Pass it through to the user verbatim, or summarize in 2-3 sentences and link to the URL.

## When the user said a rule-shaped phrase but not a real rule

E.g., user says "explain pep8 violation". That's not an aidoctor rule. Run `aidoctor rules` first, find the closest match by message/category, and suggest it. If no match, tell the user honestly: "aidoctor doesn't have a rule for that. You might want Ruff for general PEP 8."
