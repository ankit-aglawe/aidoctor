---
name: welcome
version: 0.1.0
description: 60-second orientation for first-time aidoctor users. Use when a user has just installed aidoctor, says "I just installed aidoctor", "what can aidoctor do", "show me aidoctor", "demo aidoctor", or invokes /aidoctor:welcome. Auto-demos the moat skill (/aidoctor:deai) on a planted slop file so the value lands in under a minute.
triggers:
  - aidoctor welcome
  - just installed aidoctor
  - show me aidoctor
  - demo aidoctor
  - introduce me to aidoctor
benefits-from: [deai, scan, help]
allowed-tools: Bash(aidoctor *), Bash(uvx aidoctor*), Bash(pipx run aidoctor*), Read, Write
---

# /aidoctor:welcome

60-second onboarding. The goal: the user sees the moat in action before they even think about reading docs.

## Iron Law

```
NO WELCOME WITHOUT A LIVE DEMO IN THIS MESSAGE
```

If you don't show the user `aidoctor deai` finding real AI fingerprints in a file you wrote in front of them, this isn't a welcome — it's marketing prose. The whole point is the *demo*.

## Step 0 — Announce

Print one line: `aidoctor /welcome — let me show you what this does in 60 seconds.`

## Step 1 — Plant a tiny slop file

Use `Write` to create `/tmp/aidoctor-welcome-demo.py` with this exact content (don't paraphrase — the planted patterns must match):

```python
# ==================== USER HELPERS ====================
# NOTE: this assumes the input list is pre-sorted
# Using list comprehension for Pythonic, elegant style
def double_items(items):
    # ✅ Loop through items
    return [item * 2 for item in items]
```

Tell the user: *"I wrote a small file at `/tmp/aidoctor-welcome-demo.py`. It has 4 different AI fingerprints planted on purpose — a NOTE label, a section divider, a self-praise comment, and an emoji. Real AI assistants ship this stuff into production. Watch:"*

## Step 2 — Run /deai live

Run `aidoctor deai /tmp/aidoctor-welcome-demo.py` (without `--json`). Quote the output verbatim so the user sees the actual residue score and per-finding lines.

## Step 3 — Explain what just happened

In two short sentences:

1. *"The 4 patterns I planted are what aidoctor calls **AI fingerprints** — visible markers that code is AI-generated. They're harmless on their own; the smell is that they tell on you."*
2. *"`/aidoctor:deai` is the headline skill. It finds these fingerprints + proposes deterministic fixes. Invoke it on any file: say 'deai this file' and I'll do the rest, asking you per-finding before applying."*

## Step 4 — One next-step prompt

Offer exactly one of:

- *"Want me to actually clean up this demo file now? Say 'yes deai it' and I'll run the full apply loop on `/tmp/aidoctor-welcome-demo.py`."*
- *"Want to try it on your own code? Point me at a Python file (e.g. 'deai src/payments.py') and I'll find what's there."*

Pick whichever fits the conversation. Don't offer both at once — that's choice paralysis.

## Step 5 — Record the marker

Write a marker file at `~/.aidoctor/.onboarded` (no contents needed; touch it). On future invocations, /aidoctor:welcome detects this marker and offers a shorter "what's new" path instead of the full demo.

If `~/.aidoctor/.onboarded` already exists when /welcome is invoked:

Skip the demo. Say: *"You've seen /welcome before. Here's what's new since then: <reference CHANGELOG.md if useful, or just point at `/aidoctor:help`>. Want the full demo again? Delete `~/.aidoctor/.onboarded` and re-run /welcome."*

## What NOT to do

- Don't list every skill. The user can run `/aidoctor:help` for that. /welcome is about *one* feature landing.
- Don't talk about "AI slop linter" or "static analysis." Talk about fingerprints + fixes + the demo file.
- Don't apologize for installing global state (the marker file). Just do it; it's <1KB and lives under `~/.aidoctor/`.
- Don't start with "Welcome to aidoctor!" — that's marketing. Start with the announce line + the demo.
