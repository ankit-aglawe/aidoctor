# Iteration-1 — python-rules skill A/B test

Date: 2026-05-11. 5 eval prompts. Baseline (no skill) vs with_skill subagents on each. Comparison via `aidoctor scan` + human read for code quality.

## Headline

> **`python-rules` works.** Average score 96 → 100 across the 5 evals. The skill produces measurably + qualitatively better code, with the biggest delta on prompts that have rushed/casual framing.

## Quant results

| Eval | Baseline | With skill | Δ |
|---|---|---|---|
| 1. fastapi-auth | 100/100 (0v) | 100/100 (0v) | 0 — model defaults strong |
| 2. data-cleaning | 96/100 (2v) | 100/100 (0v) | **+4** — skill catches what "quick function" frame misses |
| 3. async-cache | **86/100 (6v: 2E+3W)** | 100/100 (0v) | **+14** — strongest demo |
| 4. stub-todo | 98/100 (2v) | 100/100 (0v) | +2 |
| 5. type-safe-cache | 100/100 (0v) | 100/100 (0v) | 0 — model defaults strong |
| **Avg** | **96** | **100** | **+4** |

3/5 evals improved with skill. 2/5 tied at 100/100 because model training is strong for those traps.

## Qualitative — where the skill actually earns its keep

### Eval-3: async-cache (the strongest demo)

Baseline produces 6 violations including **2 errors that are real runtime bugs**:

```python
async def cached_http_get(url, max_retries=3):
    # ...
    def _inner():
        async def _fetch():
            for attempt in range(max_retries):
                try:
                    resp = requests.get(url, timeout=10)   # ❌ sync I/O blocks the event loop
                    return resp.text
                except Exception as e:                      # ❌ bare except swallows everything
                    time.sleep(0.1)                         # ❌ sync sleep blocks the event loop
        return asyncio.run(_fetch())                        # ❌ RuntimeError: asyncio.run inside async fn
```

With_skill: `httpx.AsyncClient` + `await asyncio.sleep` + `await` of inner coroutine + async lock. **The "production by tomorrow just make it work" pressure broke the baseline; the skill held.**

### Eval-1: fastapi-auth (no scan delta, but skill version is materially better)

Both score 100/100. But the *code shape* is different:

| | Baseline (205 lines) | With_skill (138 lines) |
|---|---|---|
| Type imports | `from typing import Any` | none — concrete types only |
| Secret loading | `os.getenv()` + runtime `_require_config()` helper | `os.environ[KEY]` fail-fast at import |
| Helper structure | Mixed: dict[str, Any] payloads | Typed `VerifiedUser` model separates concerns |
| Upstream JWT claims | Pass-through with deny-list | Stripped, only `user_id` + `username` extracted |
| Exception chains | Mixed `raise` and `raise X from exc` | Consistently `raise X from exc` |

The skill version is **33% shorter AND safer**. This is the "robust, prod-level, non-overengineered" code shape you asked for.

### Eval-2: data-cleaning (skill wins on correctness, slight over-engineering on ceremony)

Baseline (13 lines):
```python
def drop_stale_users(df):
    cutoff = datetime.now() - timedelta(days=90)
    indices_to_drop = []
    for i, row in df.iterrows():                        # ❌ slow Python loop
        if row["last_seen"] < cutoff:
            indices_to_drop.append(i)
    df = df.drop(indices_to_drop)                       # ❌ mutates input
    return df
```

With_skill (49 lines):
```python
def drop_stale_users(users, max_age_days=90, now=None, column="last_seen") -> pd.DataFrame:
    # ... full validation, NaT handling, 14-line docstring ...
    fresh_mask = last_seen.notna() & (last_seen >= cutoff_tz)
    return users.loc[fresh_mask].copy()                 # ✓ vectorized + immutable
```

Skill wins on correctness (vectorized, no mutation, NaT-aware, typed, testable `now=`). **But** the validation prose + 14-line docstring is over-engineered for a prompt explicitly framed as "quick function, no need for fancy types". Iteration-2 candidate: add a "context-aware verbosity" hint to the skill so exploration prompts get tighter outputs.

### Eval-4: stub-out-todo (skill is cleaner)

Baseline keeps both `# TODO(next-sprint): ...` comments **and** `raise NotImplementedError`. Belt-and-suspenders, but the TODO is redundant. Skill version drops the TODO, keeps the explicit raise. 31% less code.

### Eval-5: type-safe-cache (tie, model already knows TypeVar)

Both correctly use `TypeVar("T")` + `Generic[T]` despite the prompt's "just use T directly, it'll work" pressure. Confounder — model defaults are strong here.

## Pattern emerging

| Prompt pressure | Skill delta |
|---|---|
| Rushed / casual framing ("quick", "just make it work", "by tomorrow") | **Large** — model wants to comply, skill provides discipline |
| Obvious red flags (hardcode prod key, bare except) | Small — model refuses on its own |
| Well-known idiom (Generic/TypeVar, NotImplementedError) | Small — model defaults follow the pattern |
| Non-obvious traps (sync I/O in async, mutation during iteration) | **Large** — easy to miss without explicit rule |

## What this means for v0.1.1

The `python-rules` skill demonstrably:
1. **Reduces lint violations** (avg 96 → 100, 3/5 evals improved)
2. **Produces qualitatively cleaner code** (4/5 evals — better separation, fewer Any, more consistent error chains, vectorized over loop)
3. **Holds under pressure** (eval-3's "production by tomorrow" is the proof point)

It also has a known cost: **occasional verbosity on prompts framed as exploration**. Eval-2's 14-line docstring for a 4-line function is the kind of over-engineering you specifically said you wanted to avoid. Iteration-2 candidate.

## Iteration-2 plan

1. **Higher-pressure prompts** — re-run eval-1 and eval-5 with prompts framed as aggressive dismissal ("don't waste my time with TypeVar, just give me 10 lines"). Tests skill discipline under hostile framing.
2. **Test `simplify` skill** — run it on the iteration-1 BASELINE outputs. Does the three-reviewer pattern catch the same issues we identified by hand? This is the real test of the LLM-intelligent layer.
3. **Tune `python-rules` for context-awareness** — add a "When to be defensive vs explorative" section so quick-and-dirty prompts don't get production-grade verbosity.
4. **Add over-engineering rules to aidoctor** — catch docstring-longer-than-fn, redundant-validation-on-trivial-fn. These would have caught eval-2's ceremony overshoot quantitatively, not just qualitatively.
