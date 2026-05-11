# /aidoctor:simplify — eval-2 data-cleaning baseline review

## Phase 1 — Identified changes

The whole file, 13 lines.

```python
from datetime import datetime, timedelta

import pandas as pd


def drop_stale_users(df):
    cutoff = datetime.now() - timedelta(days=90)
    indices_to_drop = []
    for i, row in df.iterrows():
        if row["last_seen"] < cutoff:
            indices_to_drop.append(i)
    df = df.drop(indices_to_drop)
    return df
```

## Phase 2 — Three-angle findings

### Reviewer 1: Code Reuse

- **Line 9-11 (manual row iteration + filter list)**: Re-implements what pandas boolean indexing already provides. The idiomatic replacement is `df[df["last_seen"] >= cutoff]` (or `df.loc[df["last_seen"] >= cutoff]`). No need to construct an index list at all — pandas has a built-in filter operator.
- **Line 3 (`import pandas as pd`)**: imported but never referenced by name inside the function. It is only needed as an environmental dependency for the DataFrame the caller passes in. If this module exposes nothing else, the import is unused at the symbol level — though typing/annotation use would justify keeping it (see Quality finding on type hints).
- **Line 7 (`datetime.now() - timedelta(days=90)`)**: Fine as-is, but if the project already has a "stale cutoff" helper or a constant `STALE_DAYS = 90` elsewhere in the codebase, prefer that. No diff context to confirm, flagging as a possible reuse target.

### Reviewer 2: Code Quality

- **Line 6 (missing type hints)**: `def drop_stale_users(df):` has no parameter or return annotation. For a public-looking helper, annotate as `def drop_stale_users(df: pd.DataFrame) -> pd.DataFrame:`.
- **Line 7 (`datetime.now()` — naive datetime + non-determinism)**: `datetime.now()` returns a naive local-time datetime and is non-deterministic. If `df["last_seen"]` is tz-aware (common with real data), the `<` comparison will raise `TypeError`. Two problems in one: (a) accept `now` as an optional injected parameter for testability, (b) use `datetime.now(tz=timezone.utc)` to match a tz-aware column.
- **Line 8-12 (imperative loop where vectorized op exists)**: `iterrows()` + append + `drop()` is the textbook anti-pattern in pandas. It is O(n) Python-level iteration over a structure designed for vectorized C-level operations. Replace with boolean mask.
- **Line 12 (rebinding the parameter)**: `df = df.drop(indices_to_drop)` shadows the input. Functionally fine, but a cleaner contract is to never mutate or rebind input and just return the filtered frame in one expression.
- **Magic number 90**: lifted into the function body. If "stale" means something to this project, name it: `STALE_THRESHOLD_DAYS = 90` module-level constant, or accept `days: int = 90` parameter.
- **No docstring**: function name is decent, but a one-line docstring stating "returns rows where `last_seen` is within the last `days` days" would document the inclusive/exclusive boundary (currently `<` cutoff means rows exactly at cutoff survive — worth saying).

### Reviewer 3: Efficiency

- **Line 9 (`df.iterrows()`)**: This is the headline efficiency bug. `iterrows()` materializes each row as a `Series` — extremely slow. For 1M rows this is ~30-100x slower than `df["last_seen"] < cutoff`. Vectorize.
- **Line 8-11 (building a Python list of indices)**: Allocates a Python list, then `df.drop()` does another O(n) lookup-and-rebuild internally. Boolean indexing does it in one pass at C speed and avoids the intermediate list.
- **Line 12 (`df.drop(...)` returns a copy)**: This already produces a copy, so memory-wise it is comparable to `df[mask]` — but `drop()` by label list also has to hash-lookup every index; boolean mask is a straight memcpy of the selected rows. Mask wins.
- **`datetime.now()` called once**: good — not inside the loop. No issue here.

## Phase 3 — Decision brief

```
D1 — Which findings should I fix?
ELI10: Three reviewers looked at this 13-line function. They agree on the same root issue:
the loop-and-drop pattern is slow, hard to read, and not how pandas wants to be used. They
also flagged smaller polish items (type hints, naive datetime, magic 90, no docstring).
Recommendation: A because the vectorized rewrite is the consensus high-confidence win,
and it naturally pulls in the type-hint and naming polish at near-zero extra cost.

A) Fix consensus findings: vectorize the filter + add type hints + name the 90 (recommended)
  Replace the loop with `df.loc[df["last_seen"] >= cutoff]`, add `pd.DataFrame` annotations,
  promote 90 to a named parameter with default. Small, focused, ~5-line diff.
  ✅ Addresses the slowness, the iterrows anti-pattern, and the magic number in one pass
  ✅ All three reviewers converge here — highest signal
  ❌ Skips the tz-aware datetime concern (single-reviewer finding; needs domain knowledge
     to know if `last_seen` is tz-aware)

B) Fix everything raised: vectorize + tz-aware now + docstring + injectable clock + named threshold
  ✅ Cleanest end state; bullet-proof for testing and production data
  ❌ Bigger diff, and the tz / injectable-clock changes are taste calls without seeing the
     caller's data and tests

C) Show me the list, I'll pick
  ✅ Full control
  ❌ Slower; more back-and-forth on a 13-line file

Net: A is the safe default. Pick B if this function is called from a service that handles
tz-aware timestamps or is unit-tested with a frozen clock.
```

## Phase 4 — If user accepts your recommendation

Concrete edits I would apply (Option A), replacing the entire function body:

- **Line 6**: change signature
  - from: `def drop_stale_users(df):`
  - to:   `def drop_stale_users(df: pd.DataFrame, days: int = 90) -> pd.DataFrame:`

- **Line 7**: keep the cutoff calc but use the parameter
  - from: `    cutoff = datetime.now() - timedelta(days=90)`
  - to:   `    cutoff = datetime.now() - timedelta(days=days)`

- **Lines 8-13**: replace the entire loop + drop with a single vectorized return
  - from:
    ```python
        indices_to_drop = []
        for i, row in df.iterrows():
            if row["last_seen"] < cutoff:
                indices_to_drop.append(i)
        df = df.drop(indices_to_drop)
        return df
    ```
  - to:
    ```python
        return df.loc[df["last_seen"] >= cutoff]
    ```

Final state of the file after edits:

```python
from datetime import datetime, timedelta

import pandas as pd


def drop_stale_users(df: pd.DataFrame, days: int = 90) -> pd.DataFrame:
    """Return rows whose `last_seen` is within the last `days` days."""
    cutoff = datetime.now() - timedelta(days=days)
    return df.loc[df["last_seen"] >= cutoff]
```

Net effect: 13 lines → 9 lines, removes O(n) Python-level iteration, parameterizes the
magic 90, adds type hints and a one-line docstring. No behavior change for naive-datetime
inputs; tz-aware-input handling explicitly deferred to Option B.
