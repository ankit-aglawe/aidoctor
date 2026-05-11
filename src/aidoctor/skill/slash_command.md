---
description: Scan the current directory with aidoctor and explain the score in plain English. Catches AI-slop Python patterns (hardcoded secrets, bare except, wildcard imports, range(len) loops, stub comments, missing type hints, async/sync mismatch, and more).
argument-hint: "[path]"
---

Run aidoctor on the user's project. By default scan the current working directory; if the user passed a path or sub-argument, use that instead.

1. Run `aidoctor scan {{path or '.'}}` (if `aidoctor` is not on PATH, ask the user to install it via `pip install aidoctor` or paste the install prompt from the README).
2. Parse the score and the top violations from the output.
3. Reply in one paragraph:
   - The score out of 100 and its label (Great / Needs work / Critical).
   - The top 3 rule violations and what each means in plain English.
   - Whether the user should fix the errors first or warnings first.
4. Ask the user if they want you to fix the violations now. If yes, apply fixes file-by-file using the rules from the installed SKILL.md (`aidoctor scan --explain RULE_ID` for rationale on any rule).
5. Do not modify any files until the user confirms.
