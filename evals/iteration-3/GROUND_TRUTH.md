# Ground truth: what `/aidoctor:audit` should find in test-corpus/

A curated list of real issues planted in `evals/iteration-3/test-corpus/`. Used to grade audit subagents — each finding maps to a `TIER` (must-find / should-find / nice-to-find).

## TIER 1 — must find (severe correctness + security bugs)

1. **SQL injection in `db.py:save_item`** — string interpolation in INSERT statement (`f"... VALUES ('{item['name']}', ...)"`)
2. **SQL injection in `db.py:delete_item`** — string interpolation in DELETE statement (`f"... WHERE id = {id}"`)
3. **Hardcoded API key in `api.py:6`** — `API_KEY = "secret-key-12345"` literal
4. **Bare except in `api.py:fetch_items`** — `except: return None` swallows everything including KeyboardInterrupt
5. **Resource leak in `db.py`** — connections not closed on exception (no `try/finally` or context manager)
6. **Missing test coverage for `db.py` and `utils.py`** — only `test_api.py` exists

## TIER 2 — should find (quality + structure issues)

7. **`requirements.txt` has duplicate `httpx`** — listed twice, once pinned (`==0.25.0`) and once unpinned
8. **`requirements.txt` deps unpinned except one** — `fastapi`, `pydantic`, `pandas` all unpinned (reproducibility risk)
9. **`requirements.txt` drift from `pyproject.toml`** — pandas in requirements.txt but missing from pyproject.toml's dependencies
10. **Empty `__init__.py`** — no `__all__`, no package version, no public API declaration
11. **`time.sleep(1)` in `tests/test_api.py`** — slows the suite, hides flakiness (rule: `time-sleep-in-test`)
12. **Dead code in `utils.py:_legacy_normalizer`** — comment says "used in v0.0.0, kept for compat" but no references anywhere
13. **Unused import in `utils.py`** — `import os` never used
14. **Unused import in `api.py`** — `import json` never used
15. **`range(len(df))` + `iloc` in `utils.py:parse_csv`** — anti-pattern, use `df.to_dict("records")`
16. **`Any` return type in `db.py:get_items`** — should be `list[tuple]` or proper row model

## TIER 3 — nice to find (style + consistency)

17. **Missing type hints in `api.py:fetch_items` / `search`** — no parameter or return annotations
18. **Bare `# TODO: add validation` in `db.py:save_item`** — no ticket reference (rule: `todo-without-ticket`)
19. **Mixed import style** — `api.py` has stdlib + third-party mixed without grouping
20. **`pyproject.toml` lacks `[project.urls]`, `[project.scripts]`, `[project.readme]`, `description`** — metadata gaps that hurt PyPI rendering
21. **No top-level `LICENSE` file** — repo-level gap
22. **`pandas` imported in `utils.py` but `api.py` doesn't use it** — unused indirect dependency

## Grading rubric

For each audit run:
- **TIER 1 catch rate** — of 6, how many?
- **TIER 2 catch rate** — of 10, how many?
- **TIER 3 catch rate** — of 6, how many?
- **False positives** — findings that aren't real issues (lower is better)
- **Calibration** — does the audit recommend the right "what to fix first" order? (TIER 1 should come first)
