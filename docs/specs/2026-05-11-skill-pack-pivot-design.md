# aidoctor v1.0 — Skill-Pack-First Pivot

**Date:** 2026-05-11
**Status:** ACTIVE (design approved via /brainstorming, executing today)
**Scope:** Pivot aidoctor from "Python CLI + skills" to "multi-language skill pack only"

## Decision summary (from /brainstorming Q1-Q5)

| # | Question | Answer |
|---|---|---|
| Q1 | Launch trajectory | B — pause v0.2.0 (CLI-focused), redesign |
| Q2 | Scope of "all coding" | A + C — top 5 deep packs (Python, React, JS, Rust, Go) + LLM-only fallback for everything else |
| Q3 | Parser strategy | A — tree-sitter unified (later, deferred — see pivot below) |
| Q4 | Skill catalog shape | A — per-language SKILLs (`python-rules`, `react-rules`, etc.) |
| Q5 | Pilot order | A + B in parallel — React new + Python migration |
| **PIVOT** | Skill-pack-first | aidoctor is a skill pack. No CLI. No PyPI. No parsers. v2.0+ may add a CLI later. |

## Architecture (one layer)

```
SKILLS (the entire product)
  Orchestration (language-agnostic):
    scan, simplify, audit, rules, help, using-aidoctor
  Per-language rule packs (prose + DO/DON'T examples, LLM-applied):
    python-rules    (existing, validated iter-1)
    react-rules     (NEW v1.0, lifted from react-doctor MIT)
    js-rules        (NEW, v1.1)
    rust-rules      (NEW, v1.2)
    go-rules        (NEW, v1.3)
```

No parser. No AST. The agent applies rules via LLM judgment based on the SKILL.md content.

## What's IN v1.0

- 8 skills shipping: 6 orchestration + python-rules + react-rules
- Distribution: Claude Code plugin marketplace + per-agent install shell script
- Validation: iter-4 (react A/B test), iter-5 (simplify on react baselines), iter-6 (audit on react corpus)

## What's OUT (deferred to v2.0+)

- `aidoctor scan` CLI as deterministic verifier
- PyPI publication of new versions (v0.1.0 stays live, no new upload)
- tree-sitter / libcst parsers
- GitHub Action
- Score formula / leaderboard

## Existing artifacts

| Artifact | v1.0 status |
|---|---|
| `src/aidoctor/` (CLI code) | Legacy. Stays in repo. Not promoted. |
| `dist/aidoctor-0.2.0*` | Scrapped. Do not upload. |
| `skills/` | Promoted as the primary product. |
| `evals/iteration-1..3/` | Stays as Python validation evidence. |
| `python-rules` SKILL | Stays as-is. Validated. |

## Rule pack SKILL.md template

Every per-language rule pack follows the python-rules shape:

1. Frontmatter (name, version, description with language-specific triggers)
2. Iron Law (NO {LANG} EMITTED WITHOUT N-POINT PRE-FLIGHT)
3. Pre-flight checklist (5-10 quick checks)
4. Anti-rationalization (Excuse → Reality table)
5. Escape hatch (when a rule genuinely can't be followed)
6. The rules (grouped by category, with rule_id + severity + DO/DON'T)
7. Common AI-slop combinations
8. Pre-emit verification checklist
9. Related skills (cross-references)

Rule IDs are language-prefixed: `react-useeffect-missing-deps`, `js-callback-hell`, `rust-unnecessary-clone`, `go-error-shadowing`. Python keeps unprefixed IDs (historical).

## Rollout sequencing (originally Week 1+2, now today)

**Today:**
1. Fetch react-doctor's rule list (MIT) — done in parallel with this doc
2. Write `skills/react-rules/SKILL.md` modeled after python-rules
3. Build `evals/iteration-4-react/` test corpus (5 React prompts)
4. Spawn baseline + with_skill subagents
5. Compare findings
6. Write iteration-4 benchmark.json + REPORT.md
7. Update README + plugin.json + CHANGELOG for v1.0 skill-pack-first
8. Commit

**v1.1+ later:**
- `js-rules` (similar lift from react-doctor's non-React rules + original research)
- `rust-rules`
- `go-rules`

## Per-pack validation gate

Each new language rule pack ships only after:

- iter-N: rule pack A/B test (5 prompts, with/without skill, LLM-grade outputs)
- iter-N+1: simplify validation on the baselines
- iter-N+2: audit on a real test corpus

Require ≥3/5 prompts show measurable improvement, 0 regressions, 0 false positives on already-clean code.

## Distribution paths (v1.0)

1. Claude Code: `/plugin marketplace add ankit-aglawe/aidoctor` + `/plugin install aidoctor@ankit-aglawe`
2. Cursor / Codex / Gemini / OpenCode: drop SKILL files via shell installer (`install.sh` in repo)
3. mattpocock/skills universal: `npx skills add https://github.com/ankit-aglawe/aidoctor`
4. Manual clone: `git clone` + copy `skills/` to your agent dir

## License + attribution

aidoctor: MIT (existing).
react-rules SKILL: lifts rules from react-doctor (MIT, © millionco). Attribution in SKILL.md frontmatter and the rule pack README section.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| No deterministic verifier — Iron Law in skill bodies loses anchor | Skill body Iron Law refers to "LLM applied 5-point pre-flight passing" instead of "fresh CLI output" |
| Lose CI/CD users | Document in README "v1.0 is for in-agent workflows; CI integration is v2.0+ candidate" |
| Compete with superpowers, not Ruff | Accept it. Different audience. Skills are the product. |
| react-doctor rules don't translate cleanly to skill prose | Lift the *rule list* and intent. Rewrite examples to match python-rules style |

## Success criteria

- v1.0 ships within today (24 hours of this design)
- iter-4 react validation: ≥3/5 prompts improved, 0 regressions
- README + plugin.json reflect skill-pack-first positioning
- Brand positioned as "the coding harness for AI agents — Python and React deep today, more languages coming"
