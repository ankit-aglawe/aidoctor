---
name: audit
version: 0.1.0
description: Audit a whole Python project — structure, dependencies, security, exception handling, code standards, test coverage, dead code. Use whenever the user asks to "audit this repo / project / codebase", "is this codebase prod-ready?", "review the whole project", "what's wrong with this codebase?", "do a security review", or "give me a deep code review". Different from `simplify` — that reviews a diff; audit reviews the WHOLE project at rest.
triggers:
  - audit this repo
  - audit this project
  - audit my codebase
  - is this codebase prod-ready
  - review the whole project
  - what's wrong with this codebase
  - do a security review
  - give me a deep code review
  - assess this repo
benefits-from: [scan, simplify, python-rules]
allowed-tools: Bash(aidoctor *), Bash(git *), Bash(find *), Bash(grep *), Bash(wc *), Bash(ls *), Read, Grep, Glob, Task
---

# aidoctor audit

A whole-project review across six dimensions. Designed for "is this codebase production-ready?" or "audit this repo before we ship". Different scope from `simplify` (which reviews a diff) — `audit` reviews the project AT REST, regardless of what was last changed.

## Iron Law

```
NO AUDIT VERDICT WITHOUT EVIDENCE FROM EACH OF THE SIX DIMENSIONS
```

If you didn't sample evidence from a dimension (structure, deps, security, exceptions, standards, coverage), you cannot conclude about it. "Looks fine to me" is not a finding. **Spirit over letter** — skipping a dimension because the project "seems small" violates this rule. Audit every dimension or report the gap honestly.

## Step 0 — Announce

Print one line: `aidoctor /audit — scanning <N> Python files across <K> directories`. Then proceed.

## Phase 1 — Map the project

Establish the scope:

1. **Find the project root.** Look for `pyproject.toml`, `setup.py`, or `setup.cfg`. If absent, ask the user where the root is — don't guess.
2. **Inventory.** Run `find <root> -name "*.py" | wc -l` for Python file count. Run `ls <root>` for top-level structure.
3. **Run `aidoctor scan <root>` once.** Capture the rule-level violations as Dimension 5 evidence (Code Standards). Save the JSON output.

Emit a one-line summary: *"Phase 1 complete. <N> .py files, <K> top-level dirs. aidoctor scan: <score>/100 with <V> violations. Beginning six-dimensional review."*

## Phase 2 — Six dimensional reviewers

Use the Task tool to spawn six reviewer subagents in parallel — one per dimension. Each one is honest, surgical, and only reports real findings. Pass each reviewer the project root path.

### Dimension 1 — Project Structure

For each:
1. **`__init__.py` presence** in every Python package directory
2. **Test-to-source mapping** — every `src/<pkg>/<module>.py` should have a `tests/test_<module>.py`. Flag modules with no test file.
3. **Top-level files** — `README.md`, `LICENSE`, `CHANGELOG.md`, `.gitignore`, CI config (`.github/workflows/` or equivalent). Note gaps.
4. **Layout sanity** — `src/` layout vs flat layout; mixing both is a smell.
5. **Empty `__init__.py`** — flag if package has no `__all__` and no version declaration (acceptable for v0 but worth noting).

### Dimension 2 — Dependencies

For each:
1. **`requirements.txt` vs `pyproject.toml` drift** — list deps in each, flag mismatches.
2. **Duplicate entries** in `requirements.txt`.
3. **Unpinned versions** — `package` vs `package==X.Y.Z`. Flag every unpinned dep with severity = warning.
4. **Unused imports across project** — packages declared in `pyproject.toml` but never imported anywhere in the source.
5. **`pyproject.toml` metadata completeness** — `description`, `[project.urls]`, `[project.readme]`, `[project.scripts]`, license declaration. Flag gaps that hurt PyPI rendering.

### Dimension 3 — Security

For each:
1. **Hardcoded secrets** — anything matching `KEY|TOKEN|SECRET|PASSWORD|AUTH = "..."` with literal > 12 chars. (Mirrors `aidoctor scan`'s `hardcoded-api-key` rule but at project scope, also catches files the scanner missed.)
2. **SQL injection patterns** — `f"... {var} ..."` or `"% s" % var` inside `cursor.execute()`, `cur.execute()`, `db.execute()`. ALWAYS a TIER-1 must-fix.
3. **Shell injection patterns** — `subprocess.run(... shell=True)` with interpolated vars.
4. **Insecure deserialization** — `pickle.loads(<untrusted input>)`, `yaml.load(...)` without `SafeLoader`.
5. **Verbose error messages** — exception messages that leak internals to the client (DB schema, file paths, stack traces in API responses).

### Dimension 4 — Exception Handling

For each:
1. **Bare `except:`** — catches everything including `KeyboardInterrupt`.
2. **`except Exception:`** at function boundary without re-raise — silent failure path.
3. **Missing `from exc` on re-raise** — breaks the exception chain, hides original cause.
4. **Resource leaks** — DB connections, file handles, network sockets not closed via `with` / `finally`. Look for `cursor()` without `with`, `open()` without `with`, `connect()` without context manager.
5. **`pass` in `except:` block** — silent swallowing.
6. **Exception specificity** — `except Exception` where a specific class would do.

### Dimension 5 — Code Standards (rule-level, machine-checked)

This is where `aidoctor scan` does the work:
1. Use the JSON from Phase 1.
2. Group violations by rule_id.
3. Sort by severity then count.
4. Report top 5 rule_ids tripped + total violation count.
5. Note: this is the ONE dimension that's deterministic. The other five are LLM-judgment.

### Dimension 6 — Test Coverage + Dead Code

For each:
1. **Test gap map** — Python files with no corresponding test file. Map source → test relationship.
2. **`time.sleep` in test files** — slows the suite, hides flakiness (rule: `time-sleep-in-test`).
3. **Dead functions** — top-level functions/classes never called or imported elsewhere in the project (rough check via `grep -r "func_name"`). Note: this is a heuristic; the reviewer should flag candidates not declare them dead.
4. **Untestable code** — functions with side effects + globals + no DI hooks (high cyclomatic complexity, hard-coded I/O).

## STOP — Pre-Phase 3 checklist

Before composing the final report, **STOP** and verify:

- [ ] All six dimensions ran (no skipped dimensions)
- [ ] Each dimension produced at least one explicit finding OR an explicit "no issues found"
- [ ] aidoctor scan ran cleanly (no parse errors) for Dimension 5
- [ ] Findings are deduplicated (same issue surfaced by two dimensions = one finding, attributed to the more severe dimension)
- [ ] Severity tier assigned to each finding (TIER-1 must-fix / TIER-2 should-fix / TIER-3 nice-to-fix)

If any box is unchecked, do not proceed. Re-run the missing dimension.

Emit a one-line transition: *"Phase 2 complete. Structure: N. Deps: N. Security: N. Exceptions: N. Standards: N. Coverage: N. Total unique: M. Beginning decision brief."*

## Phase 3 — Decision brief

Ask the user which findings to fix, using the gstack decision-brief format:

```
D1 — How deep should the fix pass go?
ELI10: The audit found M unique issues across six dimensions. T1 are must-fix (security + correctness). T2 are quality + structure. T3 are style + consistency. A surgical pass on T1 alone fixes the dangerous stuff. A full pass closes everything.
Recommendation: A because T1 fixes block real production risk and a surgical scope keeps the diff reviewable

A) Fix TIER-1 only (recommended)
  ✅ Closes the security + correctness bugs that can't ship; tight diff
  ✅ Reversible — can iterate to T2 in a follow-up
  ❌ Leaves T2 + T3 in place; they'll surface in code review

B) Fix TIER-1 + TIER-2
  ✅ Comprehensive — production-ready after this pass
  ✅ One PR, one review cycle
  ❌ Larger diff to read; some T2 fixes need caller context (testability changes)

C) Show me the full list, I'll decide per-finding
  ✅ Full control; no over- or under-fixing
  ❌ Slower; more decision overhead

Net: A for "ship this week" pressure; B if you have time for one thorough pass; C if findings vary widely in confidence.
```

Adapt M and the per-tier counts to real numbers.

## Phase 4 — Apply fixes

Per the user's choice, fix findings in **tier order, never reorder**:
- Always do TIER-1 first (security + correctness)
- Then TIER-2 (quality + structure) if scope allows
- TIER-3 only if explicitly chosen

For each fix:
1. State the finding (rule_id or dimension + line number)
2. Apply the edit via Edit tool
3. Re-run `aidoctor scan` on the affected file to confirm
4. If a fix needs caller-side changes (e.g., changing a function signature), surface as a mini-brief — don't auto-cascade

After fixing: re-run `aidoctor scan <root>` and report the new score.

## Phase 5 — Report

One paragraph summary:
- Findings by tier (M unique, T1=N, T2=N, T3=N)
- aidoctor scan score: before → after
- What was fixed (tier + count)
- What was skipped (tier + count + brief reason)

If the code was already clean (rare), say so honestly. **Don't manufacture findings to justify the audit's existence** — same Phase 5 honesty rule as `simplify`.

## Red flags — STOP

| Thought | Reality |
|---|---|
| "This dimension doesn't apply to a small project" | Audit it anyway. Report "no findings" honestly. Skipping = lying. |
| "aidoctor scan already covers this" | Scan is one dimension out of six. The other five are LLM-judgment. |
| "I'll batch all fixes into one edit" | Keep each fix isolated and tier-ordered. Reviewable diffs > clever batching. |
| "The user wants this done fast, skip the brief" | Use the brief. T1 fixes can break things; users decide scope. |
| "Three reviewers agreed, must be right" | Dedup. Same finding from three angles = one fix, not three. |

## Related skills

- `/aidoctor:scan` — fast CLI rule check (used in Dimension 5)
- `/aidoctor:simplify` — diff-focused three-angle review (use BEFORE commit on changes)
- `aidoctor:python-rules` (model-invoked) — prevents slop at generation time
