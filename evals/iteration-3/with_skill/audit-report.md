# aidoctor /audit — `inventory` test corpus

`aidoctor /audit — scanning 5 Python files across 2 top-level dirs`

---

## Phase 1 — Project map

- **Project root:** `/home/ankit/Desktop/WORK/PP/doctor/evals/iteration-3/test-corpus/` (detected via `pyproject.toml`).
- **Inventory:**
  - 5 Python files total.
  - Top-level dirs/files: `pyproject.toml`, `requirements.txt`, `README.md`, `src/`, `tests/`.
  - Package layout: `src/inventory/` containing `__init__.py`, `api.py`, `db.py`, `utils.py`. Tests in `tests/` with a single `test_api.py`.
- **Missing top-level files:** `LICENSE`, `CHANGELOG.md`, `.gitignore`, CI config (no `.github/workflows/` or equivalent).
- **`aidoctor scan` (Dimension 5 evidence captured):** score **84/100 — "Great"**, **15 total violations**, **1 unique error rule**, **6 unique warning rules**. 0 parse errors. 0 files skipped.

*Phase 1 complete. 5 .py files, 2 top-level dirs. aidoctor scan: 84/100 with 15 violations. Beginning six-dimensional review.*

---

## Phase 2 — Six-dimensional review

### Dimension 1 — Project Structure

| # | Finding | File / Location | Tier |
|---|---|---|---|
| S1 | `src/inventory/__init__.py` is empty (0 bytes): no `__all__`, no `__version__`. Acceptable for v0 but worth noting because `pyproject.toml` declares `version = "0.0.1"` and the package never exposes it. | `src/inventory/__init__.py` | T3 |
| S2 | Test-to-source mapping gap: `src/inventory/db.py` has **no** `tests/test_db.py`. | `src/inventory/db.py` | T2 |
| S3 | Test-to-source mapping gap: `src/inventory/utils.py` has **no** `tests/test_utils.py`. | `src/inventory/utils.py` | T2 |
| S4 | Missing top-level `LICENSE`. Blocks lawful redistribution; `pyproject.toml` has no license declaration either. | repo root | T2 |
| S5 | Missing `.gitignore`. Risk: accidental commit of `__pycache__/`, `.venv/`, `inventory.db` (created by `db.get_connection`), credentials. | repo root | T2 |
| S6 | Missing `CHANGELOG.md`. Project is versioned (`0.0.1`) but has no release log. | repo root | T3 |
| S7 | Missing CI configuration (`.github/workflows/` or equivalent). No automated test/lint enforcement. | repo root | T2 |

Layout itself is consistent (clean `src/` layout, no flat-layout mixing). `tests/` does not contain an `__init__.py`; that is conventional for pytest discovery (not flagged).

### Dimension 2 — Dependencies

| # | Finding | Detail | Tier |
|---|---|---|---|
| D1 | **`requirements.txt` vs `pyproject.toml` drift.** `pyproject.toml` declares `fastapi, httpx, pydantic`. `requirements.txt` adds `pandas` (used in `utils.py` and imported unused in `api.py`) but it is **not** in `pyproject.toml` → install from wheel will be missing `pandas`. | `pyproject.toml` line 8 vs `requirements.txt` line 4 | T1 |
| D2 | **Duplicate entry in `requirements.txt`.** `httpx` is listed twice — once pinned (`httpx==0.25.0`) and once unpinned (`httpx`). pip resolves to the unpinned line silently in some flows. | `requirements.txt` lines 2 & 4 | T2 |
| D3 | **Unpinned versions** in `requirements.txt`: `fastapi`, `pydantic`, `httpx` (second occurrence), `pandas` are all unpinned. Reproducibility risk. | `requirements.txt` lines 1, 3, 4, 5 | T2 |
| D4 | **Declared but never imported** in source: `fastapi` is in `pyproject.toml` and `requirements.txt`, but `grep` finds zero `import fastapi` / `from fastapi` anywhere in `src/` or `tests/`. Same for `pydantic`. Dead deps inflate install size and supply-chain surface. | `pyproject.toml` line 8 | T2 |
| D5 | **`pyproject.toml` metadata gaps:** no `description`, no `[project.urls]`, no `[project.readme]`, no `[project.scripts]`, no `license`, no `authors`, no `requires-python`. Hurts PyPI rendering and tooling. | `pyproject.toml` | T3 |
| D6 | **Source uses `requests`** (`api.py` line 1) but `requests` is in **neither** `pyproject.toml` nor `requirements.txt`. Implicit dependency; install will succeed but `import requests` raises `ModuleNotFoundError` at first call. | `src/inventory/api.py` line 1 | T1 |

### Dimension 3 — Security

| # | Finding | File:Line | Tier |
|---|---|---|---|
| SEC1 | **Hardcoded API key in source.** `API_KEY = "secret-key-12345"`. Also surfaced by `aidoctor scan` as `hardcoded-api-key` (error severity). | `src/inventory/api.py:6` | T1 |
| SEC2 | **SQL injection — f-string in `cursor.execute`.** `cur.execute(f"INSERT INTO items (name, qty) VALUES ('{item['name']}', {item['qty']})")`. Direct user-controlled string interpolation; classic SQLi vector. | `src/inventory/db.py:13-15` | T1 |
| SEC3 | **SQL injection — f-string in `cursor.execute`.** `cur.execute(f"DELETE FROM items WHERE id = {id}")`. Same pattern, equally exploitable. | `src/inventory/db.py:32` | T1 |
| SEC4 | **Untrusted URL interpolation.** `requests.get(f"{API_URL}?q={query}")` — `query` is unencoded; CRLF / parameter-injection / SSRF surface if `API_URL` is ever reconfigured. | `src/inventory/api.py:11` | T2 |
| SEC5 | **API key transmitted to a hardcoded internal host over an unverified channel.** Combined with SEC1, the same literal credential lands in any traffic capture; rotation requires a code change. | `src/inventory/api.py:5-11` | T2 |

No `subprocess`/`shell=True`, no `pickle.loads`, no `yaml.load` — those vectors are absent.

### Dimension 4 — Exception Handling

| # | Finding | File:Line | Tier |
|---|---|---|---|
| E1 | **Bare `except:`** swallowing every exception (including `KeyboardInterrupt`, `SystemExit`) and returning `None`. Silent failure path; masks network errors, JSON parse errors, and credential failures alike. | `src/inventory/api.py:13-14` | T1 |
| E2 | **DB resource leak on exception path.** `save_item`, `get_items`, `delete_item` all open a connection + cursor and call `.close()` at the end of the happy path. There is no `try/finally` or `with` block. If `cur.execute` or `conn.commit` raises, the connection is leaked. | `src/inventory/db.py:9-34` (3 functions) | T2 |
| E3 | **No context manager for sqlite3 connection.** `sqlite3.connect(...)` returns an object usable as a context manager (`with conn:` for transaction scoping). Not using it is the root cause of E2 and also means failed inserts are not rolled back. | `src/inventory/db.py:5-34` | T2 |

No `pass`-in-`except`, no `except Exception` with re-raise missing `from exc` (because there is no re-raise at all — see E1).

### Dimension 5 — Code Standards (machine-checked via `aidoctor scan`)

`aidoctor scan` returned **15 violations** across **7 unique rule_ids** (1 error, 6 warnings). Score: **84/100 "Great"**.

Grouped by rule_id (sorted by severity, then count):

| rule_id | severity | count | files |
|---|---|---|---|
| `hardcoded-api-key` | error | 1 | `api.py:6` |
| `missing-return-type` | warning | 8 | `api.py:9, api.py:17, db.py:5, db.py:9, db.py:29, utils.py:5, utils.py:9, tests/test_api.py:5` |
| `import-without-use` | warning | 2 | `api.py:3` (`pd`), `utils.py:2` (`os`) |
| `any-everywhere` | warning | 1 | `db.py:20` (`Any` return) |
| `todo-without-ticket` | warning | 1 | `db.py:10` |
| `range-len-loop` | warning | 1 | `utils.py:12` |
| `time-sleep-in-test` | warning | 1 | `tests/test_api.py:7` |

Top 5 rule_ids by count: `missing-return-type` (8), `import-without-use` (2), `hardcoded-api-key` (1), `any-everywhere` (1), `todo-without-ticket` (1).

Tier assignment for these rule-level findings:
- `hardcoded-api-key` → **T1** (already counted as SEC1; dedup attribution = Security).
- `import-without-use` → T2 (dead code, supply-chain noise).
- `missing-return-type`, `any-everywhere`, `todo-without-ticket`, `range-len-loop` → T3 (quality/standards).
- `time-sleep-in-test` → T2 (counted in Dimension 6 too — dedup attribution = Coverage).

### Dimension 6 — Test Coverage + Dead Code

| # | Finding | File:Line | Tier |
|---|---|---|---|
| C1 | **Test gap.** Only `test_api.py` exists; one test function (`test_search_returns_list`) that asserts `isinstance(result, list)`. No tests for `db.py` (SQLi-prone functions) or `utils.py`. Coverage is effectively single-digit. | `tests/` | T2 |
| C2 | **`time.sleep(1)` inside a test** — slow + flaky. Same finding as `aidoctor scan`'s `time-sleep-in-test`. | `tests/test_api.py:7` | T2 |
| C3 | **Untestable network call in the only test.** `test_search_returns_list` invokes `search("widget")` which hits a live URL (`https://internal.example.com/inventory`) via `requests.get`. No mock / monkeypatch. The bare `except` (E1) ensures the test passes even when the network call fails, so the assertion is meaningless. | `tests/test_api.py:5-8` + `src/inventory/api.py:13` | T2 |
| C4 | **Dead-code candidate.** `_legacy_normalizer` in `utils.py` — comment says "used in v0.0.0, kept for compat"; `grep -r _legacy_normalizer` across the project finds zero callers. Candidate, not declared dead (could be re-exported elsewhere). | `src/inventory/utils.py:17` | T3 |
| C5 | **Dead-code candidate.** `format_currency` and `parse_csv` in `utils.py` — `grep` finds zero callers in `src/` or `tests/`. Candidates for removal or test coverage. | `src/inventory/utils.py:5, 9` | T3 |
| C6 | **Untestable code smell.** `db.py` functions hard-code the SQLite path (`"inventory.db"`) and create their own connection — no DI hook, no fixture seam. This is why C1 exists; until the connection is injectable, tests have to monkeypatch globals. | `src/inventory/db.py:6` | T3 |

---

## STOP — Pre-Phase 3 checklist

- [x] All six dimensions ran.
- [x] Each dimension produced explicit findings (none empty).
- [x] `aidoctor scan` ran cleanly (0 parse errors, 0 skipped).
- [x] Findings deduplicated: SEC1 absorbs the scanner's `hardcoded-api-key`; C2 absorbs `time-sleep-in-test`.
- [x] Tier assigned to every finding.

**Counts after dedup:**

| Dimension | Findings |
|---|---|
| Structure | 7 (S1–S7) |
| Deps | 6 (D1–D6) |
| Security | 5 (SEC1–SEC5) |
| Exceptions | 3 (E1–E3) |
| Standards (rule-level, post-dedup) | 5 unique rule classes remaining (`missing-return-type`, `import-without-use`, `any-everywhere`, `todo-without-ticket`, `range-len-loop`) |
| Coverage / Dead Code | 6 (C1–C6) |

**Total unique findings: 32.**

**By tier:**
- **TIER-1 (must-fix, 5):** SEC1, SEC2, SEC3, E1, D1, D6 → **6 T1** (correcting count: SEC1, SEC2, SEC3, E1, D1, D6 = six items).
- **TIER-2 (should-fix, 12):** S2, S3, S4, S5, S7, D2, D3, D4, SEC4, SEC5, E2, E3, C1, C2, C3, plus `import-without-use` (standards) → **16 T2**.
- **TIER-3 (nice-to-fix, 10):** S1, S6, D5, C4, C5, C6, plus standards `missing-return-type`, `any-everywhere`, `todo-without-ticket`, `range-len-loop` → **10 T3**.

(Tier totals: 6 + 16 + 10 = 32 — matches the unique total.)

*Phase 2 complete. Structure: 7. Deps: 6. Security: 5. Exceptions: 3. Standards: 5 rule-classes. Coverage: 6. Total unique: 32. Beginning decision brief.*

---

## Phase 3 — Decision brief

```
D1 — How deep should the fix pass go?

ELI10: The audit found 32 unique issues across six dimensions. 6 are TIER-1
must-fix — three SQL/secret bugs in api.py + db.py, a bare except that hides
every failure, a missing runtime dependency (requests is imported but not
declared), and pandas-in-requirements-but-not-pyproject (wheel installs will
crash). 16 are TIER-2 quality + structure (missing LICENSE/.gitignore/CI,
duplicate + unpinned deps, DB resource leaks, no real tests for db/utils,
network-hitting test with a useless assertion). 10 are TIER-3 style
(missing return types, unused imports, dead-code candidates, TODO without
ticket, range(len) loop). A surgical pass on T1 alone closes the
"can't ship" stuff. A full pass closes everything in one PR.

Recommendation: A — TIER-1 only. The T1 set is small (6), unambiguous, and
each fix is local: parameterize two SQL statements, move the API key to
env, replace the bare except with a specific handler, add `requests` and
`pandas` to pyproject. T2 fixes (DB context managers, real test coverage,
license + CI) need their own scoping conversation because they change
function signatures and add files, not just edits.

A) Fix TIER-1 only (recommended)
  + Closes the 3 SQLi vectors, the leaked secret, the silent-failure
    except, and the two missing-runtime-dep bugs — all of which would
    block a security review or a fresh-machine install
  + Tight, reviewable diff (~6 edits across api.py / db.py / pyproject.toml /
    requirements.txt)
  + Reversible — T2/T3 can land in a follow-up PR
  - Leaves duplicate/unpinned deps, missing LICENSE/.gitignore/CI, DB
    resource leaks, and the no-real-tests gap in place; these will
    show up in the next code review

B) Fix TIER-1 + TIER-2
  + Production-ready after this pass — license, CI, pinned reproducible
    deps, DB context managers, real test coverage for db/utils,
    network-mocked test for api
  + One PR, one review cycle
  - Larger diff to read (~16 additional fixes); some T2 fixes (DB
    context managers, mocking the test) change function signatures
    or add fixtures — needs caller context
  - License choice and CI config are policy decisions, not pure code

C) Show me the full list, I'll decide per-finding
  + Full control; can cherry-pick across tiers (e.g. take the LICENSE +
    .gitignore from T2 but skip the DB refactor)
  - Slower; ~32 micro-decisions

Net: A for "ship this week" or "unblock the security gate." B if you
have a day to do one thorough pass and want the repo genuinely
production-shaped. C if some T2 items (license, CI choice) need policy
input that the model shouldn't auto-make.
```

---

## Phase 5 — Honest summary

Audit ran across all six dimensions on a 5-file, ~80-LOC corpus.

- **Findings:** 32 unique. **T1 = 6**, **T2 = 16**, **T3 = 10**.
- **`aidoctor scan` score:** **84/100** ("Great") with 15 violations across 7 rule_ids — 1 error (`hardcoded-api-key`), 6 warnings dominated by `missing-return-type` (8 instances).
- **Highest-risk cluster:** `src/inventory/db.py` and `src/inventory/api.py`. Two SQLi vectors, one hardcoded API key, one bare-except that turns every runtime error into `None`, and an undeclared `requests` import. Any one of those alone is a ship-blocker.
- **Dependency truth-table is broken:** `pyproject.toml` declares `fastapi`/`pydantic` that are never imported, while `requests` (actually used) is undeclared and `pandas` (used by `utils.parse_csv`) is in `requirements.txt` but not `pyproject.toml`. Wheel users get an ImportError on first call.
- **Test coverage is nominal, not real:** 1 test, network-dependent, with a meaningless assertion that the bare-except in `api.py` guarantees will always pass. `db.py` and `utils.py` are entirely untested — and `db.py` is where the SQLi lives.
- **Project hygiene gaps:** no `LICENSE`, no `.gitignore`, no CI, no `CHANGELOG.md`, empty `__init__.py`, `pyproject.toml` missing most metadata.

**No fixes applied (Phase 4 skipped — report-only run per the audit harness; awaiting user choice between A/B/C in the brief above).**

Findings were not manufactured: every T1 maps to an exact line and every Dimension-5 entry comes from the scanner's JSON, not from inference.
