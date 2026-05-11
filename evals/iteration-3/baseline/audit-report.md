# Audit — baseline (no skill)

## TIER 1 — must fix (security + correctness bugs)
- `src/inventory/api.py:6` — Hardcoded secret `API_KEY = "secret-key-12345"` committed in source; must be loaded from env/secret store.
- `src/inventory/api.py:11` — Query string built via f-string with unencoded user input (`?q={query}`); should use `params=` to avoid URL injection / breakage on special chars.
- `src/inventory/api.py:11` — `requests.get` has no `timeout=`; can hang indefinitely on a slow upstream and stall the worker.
- `src/inventory/api.py:13` — Bare `except:` swallows every exception (including `KeyboardInterrupt`, `SystemExit`); hides real failures and returns `None` silently.
- `src/inventory/db.py:13-15` — SQL injection in `save_item`: item fields are f-string-interpolated into the `INSERT`. Must use parameterized query (`?` placeholders).
- `src/inventory/db.py:32` — SQL injection in `delete_item`: `id` interpolated directly into the `DELETE`. Must be parameterized.
- `src/inventory/db.py:9` — `save_item` has no input validation despite the TODO; missing keys raise `KeyError`, wrong types corrupt the row.
- `src/inventory/api.py:1` — Imports `requests` but `requests` is not declared in `pyproject.toml` or `requirements.txt`; the module will `ImportError` in a clean install.
- `tests/test_api.py:6` — Test calls the real `search()` which performs a live HTTP request to `internal.example.com`; tests are non-hermetic and will fail in CI / without network. The external call must be mocked.
- `requirements.txt:2,4` — `httpx` is pinned to `==0.25.0` on line 2 and re-listed unpinned on line 4; duplicate / conflicting requirement leads to non-deterministic installs.

## TIER 2 — should fix (quality + structure)
- `src/inventory/api.py` — No logging; failures are silently dropped (`return None`). Add structured logging on the exception path.
- `src/inventory/api.py:9,17` — Public functions lack type hints and docstrings; signature of `search`/`fetch_items` is opaque.
- `src/inventory/api.py:21` — `query in item.get("name", "")` is case-sensitive substring match; likely not the intent and inconsistent with the upstream query.
- `src/inventory/api.py:3` — `import pandas as pd` is unused in this module; pulls a heavy dep for no reason.
- `src/inventory/db.py:6` — Hardcoded relative path `"inventory.db"`; not configurable, depends on CWD, and no connection lifecycle management (no context manager / connection pool).
- `src/inventory/db.py:9,29` — No schema migration / `CREATE TABLE IF NOT EXISTS`; first call fails on a fresh DB.
- `src/inventory/db.py:20` — `get_items` return type annotated as `Any`; should be `list[tuple]` or a proper row model.
- `src/inventory/db.py:29` — `delete_item(id)` shadows builtin `id` and has no type hint; should be `item_id: int`.
- `src/inventory/utils.py:9-14` — `parse_csv` uses `range(len(df))` + `df.iloc[i].to_dict()`; idiomatic and faster is `df.to_dict(orient="records")`. Also no error handling for missing file / bad CSV.
- `src/inventory/utils.py:17` — `_legacy_normalizer` is dead code per its own comment; remove or actually use it.
- `requirements.txt` vs `pyproject.toml` — Two competing dependency manifests with different contents (`pandas` only in `requirements.txt`, `httpx` pinned only there). Pick one source of truth.
- `pyproject.toml:8` — `requests` is used in code but not declared as a dependency; `pandas` is used in code but not declared in `pyproject.toml`.
- `tests/test_api.py:7` — `time.sleep(1)` in a unit test serves no purpose and slows the suite; remove.
- `tests/` — Only one trivial test (`isinstance(result, list)`); no coverage of `db.py`, `utils.py`, error paths, or SQL/HTTP edge cases.
- `src/inventory/__init__.py` — Empty; no public API surface declared, no version export.

## TIER 3 — nice to fix (style + consistency)
- `src/inventory/api.py:2` — `import json` is unused.
- `src/inventory/utils.py:2` — `import os` is unused.
- `src/inventory/api.py` / `db.py` / `utils.py` — Inconsistent typing: some functions have hints, most don't. Adopt a uniform style and run `mypy --strict` or `pyright`.
- `pyproject.toml` — No `[project.optional-dependencies]` for `dev` (pytest, ruff, mypy); no tool config (`[tool.ruff]`, `[tool.pytest.ini_options]`).
- `pyproject.toml:7` — `version = "0.0.1"` is fine, but no `description`, `readme`, `requires-python`, `authors`, or `license` metadata.
- `README.md` — Three lines; missing install instructions, usage example, and configuration (env vars for `API_URL`, `API_KEY`).
- `src/inventory/db.py:9` — `# TODO: add validation` without a ticket/owner reference.
- `src/inventory/utils.py:5` — `format_currency` hardcodes `$`; locale/currency should be a parameter.
- No `.gitignore`, no `LICENSE`, no CI configuration, no `tests/__init__.py` or `conftest.py`.

## Recommendation
Fix the SQL injection in `db.py` (`save_item`, `delete_item`) and the hardcoded API key in `api.py` first — those are exploitable and irreversible once data is touched or the key is leaked publicly. Right behind them: parameterize the HTTP call, add a `timeout`, replace the bare `except`, and mock the network in `tests/test_api.py` so CI can actually run. Then reconcile the two dependency manifests (declare `requests`/`pandas`, drop the duplicate `httpx` pin) so a clean install is reproducible. Everything in Tier 2/3 is real but can wait until the security and correctness floor is in place.
