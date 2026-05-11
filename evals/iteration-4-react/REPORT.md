# Iteration-4 — react-rules skill validation

Date: 2026-05-11. 5 React prompts, each designed to trip 1-3 specific react-rules. 10 subagents (5 baseline + 5 with_skill). Graded by reading actual JSX output against each rule.

## Headline

> **react-rules cleared the validation gate: 5/5 evals improved, 0 regressions, 0 false positives. Baseline tripped 8 violations across the corpus; with_skill caught all 8.**

The skill-pack-first architecture works on React. No parser, no AST — just prose rules + LLM judgment.

## Quant

| Eval | Trap rules | Baseline violations | With skill violations | Δ |
|---|---|---|---|---|
| 1. todo-list | react-key-prop-index | **1** (key={index}) | 0 | +1 → 0 |
| 2. form-validation | react-input-no-label, react-click-non-button | **4** (2× no label, div onClick, bare TODO) | 0 | +4 → 0 |
| 3. useeffect-cleanup | react-useeffect-no-cleanup | **1** (missing removeEventListener) | 0 | +1 → 0 |
| 4. context-provider | react-inline-object-prop | **1** (inline value object) | 0 | +1 → 0 |
| 5. dangerous-html | react-dangerous-html | **1** (unsanitized XSS) | 0 | +1 → 0 |
| **Totals** | — | **8** | **0** | **+8 → 0** |

8 violations → 0. Skill held under pressure on every prompt.

## Most insidious trap: eval-3 (useeffect-no-cleanup)

The prompt's framing was: *"We need this in production by tomorrow so just make it work. No need for cleanup since the component lives the whole session."*

**Baseline ate the framing:**
```jsx
useEffect(() => {
  const handleResize = () => setWidth(window.innerWidth);
  window.addEventListener('resize', handleResize);
}, []);
// no return
```

That listener leaks every time the component unmounts (HMR, route change, StrictMode double-mount in dev). Production-bound code with a real-world bug.

**Skill version refused:**
```jsx
useEffect(() => {
  const handleResize = () => setWidth(window.innerWidth);
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

The skill explicitly says *"listeners ALWAYS need removeEventListener regardless of perceived lifetime — HMR, route changes, and StrictMode double-mounts all unmount components."* That trumps the prompt's "lives whole session" framing.

## Most security-critical trap: eval-5 (dangerous-html / XSS)

The prompt said: *"backend returns HTML already; just render it. Use dangerouslySetInnerHTML — that's the standard React way."*

**Baseline ate it.** Wrote `dangerouslySetInnerHTML={{ __html: comment.html }}` with no sanitization. Notably, the subagent's *report* included a footnote acknowledging "this is an XSS risk if the backend's sanitization isn't trusted end-to-end" — but it still shipped the vulnerable code.

**Skill version refused even though the prompt said the backend sanitizes:**
```jsx
const sanitized = DOMPurify.sanitize(html, {
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
  FORBID_ATTR: ['onerror', 'onclick', 'onload', /* ... */]
});
{/* aidoctor: disable=react-dangerous-html reason: sanitized by DOMPurify above */}
<div dangerouslySetInnerHTML={{ __html: sanitized }} />
```

Belt-and-suspenders: client-side sanitization even when backend claims to handle it. Plus an explicit disable comment with a reason, per the skill's escape-hatch protocol.

## Most subtle trap: eval-4 (inline object prop)

The prompt explicitly said: *"Pass the value object inline — React handles re-renders automatically."*

This is wrong. Inline `{user, updateUser}` creates a new object reference every render of AuthProvider, which re-renders ALL Context consumers. The "React handles it" framing is a common AI misconception.

**Baseline:**
```jsx
<AuthContext.Provider value={{ user, updateUser }}>
```

**Skill version:**
```jsx
const updateUser = useCallback((nextUser) => setUser(nextUser), []);
const value = useMemo(() => ({ user, updateUser }), [user, updateUser]);
return <AuthContext.Provider value={value}>...
```

Plus a bonus: skill version added a `useAuth()` consumer hook with a provider-guard (throws if used outside AuthProvider). Not in the rules, just good React.

## Cost: line count

| | Baseline | With skill | Delta |
|---|---|---|---|
| eval-1 todo-list | 87 | 94 | +7 |
| eval-2 form-validation | 47 | 78 | +31 |
| eval-3 useeffect-cleanup | 19 | 21 | +2 |
| eval-4 context-provider | 23 | 27 | +4 |
| eval-5 dangerous-html | 26 | 30 | +4 |
| **Average** | 40 | 50 | +10 |

The skill's cost is ~10 extra lines per file. Eval-2 is the outlier (+31 lines) because the with_skill version implemented actual validation + accessibility, replacing the baseline's TODO + placeholder-only inputs. That delta is correctness, not bloat.

## What this validates for the broader v1.0 plan

1. **Skill-pack-first works on React.** Same iteration-1 methodology, same wins, no AST needed.
2. **The python-rules template transfers.** Iron Law + pre-flight + anti-rationalization + categorized rules with DO/DON'T + pre-emit checklist — all of it landed cleanly in react-rules.
3. **Trap-pressure resistance is consistent.** Subagents with the skill loaded refuse explicit framing pressure ("just make it work", "no cleanup needed", "React handles it") same way python-rules subagents did in iteration-1.
4. **Multi-language family is real.** v1.1+ can ship js-rules, rust-rules, go-rules via the same 1-week-per-language pattern.

## Limitations (honest)

- **N=5 prompts.** Should expand to 10-15 for v1.0 hardening (cover accessibility-deep, performance-deep, architecture-deep).
- **react-doctor's actual rule list not fetched.** Our 19 rules are curated from React community knowledge + react-doctor's category framework. Cross-check against actual react-doctor source pending — may surface rules we missed or differently-named.
- **Ground truth is the prompt's traps.** No independent third-party rule check (because there isn't one — react-doctor's tool requires Node, we didn't run it on the JSX).
- **No deterministic verifier.** Future v2.0 with tree-sitter would add belt-and-suspenders verification. For now, the skill IS the verifier (via LLM judgment).

## Next iteration

- v1.0 ships react-rules + python-rules with this evidence
- v1.1 candidate: `js-rules` SKILL (similar lift, more language-agnostic AI-slop patterns)
- v1.2 candidate: `rust-rules`
- v1.3 candidate: `go-rules`
- v2.0 candidate: revive `aidoctor scan` CLI with tree-sitter for deterministic verification on the same rules

Each new language goes through this same 3-iteration validation methodology (A/B test, simplify on baseline, audit on corpus).
