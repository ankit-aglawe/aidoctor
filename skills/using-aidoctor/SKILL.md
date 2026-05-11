---
name: using-aidoctor
version: 0.2.0
description: Orientation for the aidoctor plugin. Use the first time the user touches a Python file in a session where aidoctor is installed, or when the user asks "what does aidoctor do?", "what skills are available?", "how do I use aidoctor?", "give me a tour", or seems uncertain which aidoctor skill to invoke.
triggers:
  - what does aidoctor do
  - how do I use aidoctor
  - what aidoctor skills are available
  - give me a tour
  - what's in aidoctor
benefits-from: [scan, simplify, audit, python-rules]
---

# Using aidoctor

aidoctor catches Python that AI agents tend to write badly. Four skills, four time-points:

| When you | Skill | Trigger |
|---|---|---|
| Write Python | **`python-rules`** | auto-loads (never invoke directly) |
| Just changed code | **`/aidoctor:simplify`** | "simplify what I just changed" |
| Want a one-file scan | **`/aidoctor:scan`** | "scan this", "lint my Python" |
| Audit the whole repo | **`/aidoctor:audit`** | "audit this repo", "is this prod-ready?" |

Plus one CLI:

```bash
aidoctor scan .                          # CI lint
aidoctor scan --diff                     # only your changes
aidoctor scan --explain <rule-id>        # what does this rule mean?
aidoctor rules                           # list all 25 rules
```

## When to use what

- **Writing fresh Python?** Nothing to do. `python-rules` auto-loads when relevant; the agent reads the 25 rules before generating code.
- **Just edited a file and want a check?** `/aidoctor:simplify` reviews your diff across reuse, quality, and efficiency. Asks before fixing.
- **One file or path you want lint-checked?** `/aidoctor:scan` runs the CLI and summarizes. Fastest.
- **Whole codebase audit?** `/aidoctor:audit` does a six-dimensional review: structure, deps, security, exceptions, standards, coverage. Slowest, deepest.

## How to talk to it

Plain English works because all four skills are model-invoked:

- "scan this project for AI slop"
- "review what I just changed"
- "is this repo production-ready?"
- "what does `bare-except-pass` mean?"

The slash forms (`/aidoctor:scan`, `/aidoctor:simplify`, `/aidoctor:audit`, `/aidoctor:rules`, `/aidoctor:help`) also work for explicit invocation.

## Where to start

If this is your first time and you have a Python project:

1. Say "audit this repo" (or `/aidoctor:audit`). Get the lay of the land across all six dimensions.
2. Say "fix tier 1 only" when it asks.
3. Re-run audit. Watch the score move.

That's the magical moment.
