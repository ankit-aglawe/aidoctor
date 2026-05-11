---
description: Python coding standards for AI-generated code. Use whenever writing, editing, or reviewing Python — covers async/sync mismatch, dead defenses, hardcoded secrets, fake type hints, stub comments, stale loop patterns. Output should pass `aidoctor scan` with zero violations on the first try, not after a fix-up pass.
---

# aidoctor

## Overview

Rules tuned for AI-generated Python. Output must pass `aidoctor scan` with zero violations on the first try — not after a fix-up pass. Look up any rule with `aidoctor scan --explain <rule_id>`.

## When to use

Every Python file you generate, edit, or refactor. **No exceptions for "small" changes, tests, or "throwaway" scripts.** Secrets, bare excepts, and stub comments leak through all three.

## Read this BEFORE you type a single line of Python

A 30-second pre-flight that prevents most violations:

1. **Secrets**: if you are about to write a string longer than 12 chars assigned to a name like `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `AUTH`, or starting with `AKIA`/`ASIA`/`eyJ` — **STOP**. Use `os.environ[...]` instead. There is no "test value" that is safe; rename the variable or shorten it below 12 chars.
2. **Error handling**: if you are about to write `try:`, decide the specific exception **first**. Never type `except Exception` or bare `except:` as a placeholder.
3. **Types**: if you don't know the type, **find out**. Read the call sites. Do not type `Any` as a synonym for "I'm not sure."
4. **Unfinished work**: if the implementation isn't done, write `raise NotImplementedError("reason")`. Do not write `# implement this`, `# TODO: fill in`, or return a dummy value.
5. **Iteration**: writing `for i in range(len(...))`? Use `enumerate`. Mutating a list while iterating it? Build a new list.

If all five are clear, continue. If any is unclear, resolve it before generating code.

## Anti-rationalization

The following internal monologues all produce violations. Recognize them and stop:

- *"For now I'll just hardcode this and move it later"* — you won't. Use `os.environ` now.
- *"I'll add a TODO to come back to this"* — bare `# TODO` rots. Attach a ticket (`GH-123`, `JIRA-456`, URL) or implement it now.
- *"This is just a test/example/script, the rules don't apply"* — the rules apply. CI runs against tests too.
- *"I'll wrap it in `try: except Exception:` to be safe"* — that is the opposite of safe. It hides the bug you would have fixed.
- *"I don't know the exact type so I'll use `Any`"* — read the code, infer the type, or use a Protocol/TypeVar. `Any` is a last resort, not a default.
- *"It's only a small block, the violation doesn't matter"* — `aidoctor scan` does not grade on size. Zero violations means zero.

## When a rule genuinely can't be followed

There are real exceptions. The escape hatch is **narrow** and **explicit**:

- **Test fixture with a realistic-looking secret** (JWT shape, AWS key shape): mark the exact line with `# aidoctor: disable=<rule_id>` and add a `# reason: fixture for X` comment on the same or previous line. Do not disable file-wide.
- **Vendored / generated code**: place under a path the project excludes (check `pyproject.toml [tool.aidoctor]`). Do not edit it to add disables.
- **Genuinely interfacing with `Any`-typed external code** (e.g., `**kwargs` from a library with no stubs): annotate `object` first; only fall back to `Any` if the call site requires it, and add `# reason: ...`.

If you are reaching for a disable comment more than once per file, you are wrong about the exception — rewrite instead.

## The rules

Each rule has a stable `rule_id`. Headings are imperatives. Bodies show what's forbidden and what's required. **Rules are ordered by blast radius — top categories cause the worst damage if shipped.**
### Hardcoded Secrets
#### `aws-credentials` (error) — AWS access key in source. Rotate the key immediately and move to env or IAM role.

AWS access key IDs starting with AKIA (long-term) or ASIA (temporary STS) are credentials. Once committed, treat them as compromised: rotate the key in IAM, remove from history (git filter-branch / BFG), and migrate to IAM roles or secrets manager. Never use hardcoded AWS creds in application code.

**DON'T**
```python
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
```

**DO**
```python
# Use an IAM role, or read from env / AWS secret manager.
import boto3
client = boto3.client("s3")  # picks up role/env automatically
```
#### `hardcoded-api-key` (error) — Hardcoded secret in source. Move to environment variable or secret manager.

Variables named API_KEY, SECRET, TOKEN, PASSWORD (or similar) with long string values are almost always real secrets that leaked into source. Move them to environment variables (`os.environ['API_KEY']`) or a secret manager. If this is a test fixture or placeholder, rename the variable or shorten the value.

**DON'T**
```python
API_KEY = "sk-proj-9f8e7d6c5b4a3210"  # 'I'll move it later' — you won't
```

**DO**
```python
import os
API_KEY = os.environ["OPENAI_API_KEY"]
```
#### `jwt-token` (error) — JWT-shaped string in source. Move to environment variable or refresh flow.

Strings matching `eyJ...eyJ...XXX` are almost always JWT tokens. These usually expire but the embedded claims may still leak user identity, roles, or permissions. Move to environment variables or use a refresh flow. If this is a test fixture, mark with `# aidoctor: disable=jwt-token`.

**DON'T**
```python
AUTH = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.dummysignature1234"
```

**DO**
```python
import os
AUTH = os.environ["SERVICE_JWT"]
```
### Dead Defenses
#### `bare-except-pass` (error) — Bare except + pass silently swallows all exceptions including SystemExit and KeyboardInterrupt.

`except: pass` or `except Exception: pass` swallows every exception silently, including SystemExit and KeyboardInterrupt. AI assistants generate this when they want to 'be safe.' It hides real bugs. Either name the specific exception you expect (`except ValueError:`), log the error before continuing, or remove the try block entirely.

**DON'T**
```python
try:
    payload = json.loads(raw)
except Exception:
    pass  # 'just in case' — silently eats real bugs
```

**DO**
```python
try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    logger.warning("bad payload: %s", exc)
    payload = {}
```
#### `except-exception-swallowing` (warning) — Catching `Exception` without re-raising masks real bugs.

`except Exception:` catches almost everything. AI assistants reach for it as a catch-all. Even when you log inside, swallowing means callers can't react. Catch the specific exception you can handle. If you want a top-level safety net, place it once at the program boundary and either log+exit or re-raise.

**DON'T**
```python
try:
    result = call_api()
except Exception as exc:
    logger.error("failed: %s", exc)
    # logged, but caller silently gets None — they think it worked
```

**DO**
```python
try:
    result = call_api()
except requests.HTTPError as exc:
    logger.error("api failed: %s", exc)
    raise
```
#### `redundant-null-check-after-isinstance` (warning) — `x is not None and isinstance(x, T)` is redundant. isinstance handles None.

`isinstance(x, T)` returns False if `x` is None (None isn't an instance of any type except NoneType). AI assistants add the `is not None` check defensively. Remove the redundant check: just write `if isinstance(x, T):`.

**DON'T**
```python
if x is not None and isinstance(x, int):
    return x + 1
```

**DO**
```python
if isinstance(x, int):  # isinstance(None, int) is already False
    return x + 1
```
#### `unreachable-raise` (error) — Raise after unconditional return is unreachable code.

AI assistants sometimes stitch fragments where a `return` is immediately followed by a `raise`. The raise never executes. Remove the dead code. If you intended a conditional, restructure with an explicit `if` before the raise.

**DON'T**
```python
def parse(raw: str) -> dict:
    return json.loads(raw)
    raise ValueError("bad input")  # never runs
```

**DO**
```python
def parse(raw: str) -> dict:
    if not raw:
        raise ValueError("empty input")
    return json.loads(raw)
```
### Comment-Driven Decay
#### `stub-comment` (error) — Stub comment indicates unfinished AI-generated code.

Comments like `# implement this`, `# placeholder`, or `# your code here` are AI-assistant artifacts marking unfinished code. Either complete the implementation, remove the comment, or raise NotImplementedError explicitly so the failure mode is visible at runtime.

**DON'T**
```python
def charge_card(amount: int) -> None:
    # implement this  # ships as a silent no-op
```

**DO**
```python
def charge_card(amount: int) -> None:
    raise NotImplementedError("charge_card pending PSP integration")
```
#### `todo-without-ticket` (warning) — TODO without ticket reference. Add a ticket ID or URL so it doesn't rot.

Bare TODO/FIXME/HACK comments rot in the codebase forever. Pair every TODO with a ticket reference (`# TODO(JIRA-1234): ...`, `# TODO #456:`, `# FIXME(https://github.com/...)`) so it's tracked outside the code. If there's no ticket, decide: fix it now, delete the TODO, or open a ticket. AI assistants leave bare TODOs when uncertain — those usually mean unfinished work, not future work.

**DON'T**
```python
# TODO: handle pagination  # you will forget. it will rot.
```

**DO**
```python
# TODO(GH-123): handle pagination once the API supports cursors
```
### Async/Sync Mismatch
#### `asyncio-run-inside-async-fn` (error) — asyncio.run inside an async function raises RuntimeError at runtime.

`asyncio.run(...)` creates a new event loop and is intended for the top-level entry point of a program. Calling it inside another `async def` raises `RuntimeError: This event loop is already running`. Use `await coro()` to call the coroutine, or `asyncio.create_task(coro())` to schedule it. AI assistants reach for `asyncio.run` when they're uncertain about how to await something.

**DON'T**
```python
async def orchestrate():
    asyncio.run(do_work())  # RuntimeError: loop already running
```

**DO**
```python
async def orchestrate():
    await do_work()  # or: asyncio.create_task(do_work())
```
#### `blocking-call-in-event-loop` (warning) — Suspicious blocking call inside async function.

HEURISTIC RULE — may have false positives. Calls whose names end in `_sync` or `_blocking`, or that match common-blocking patterns like `sleep`, `wait`, `recv`, found inside `async def` are flagged. If this is intentional (e.g., the call is non-blocking in your context), suppress with `# aidoctor: disable=blocking-call-in-event-loop`.

**DON'T**
```python
async def main():
    result = legacy_lib.fetch_blocking()
```

**DO**
```python
async def main():
    result = await asyncio.to_thread(legacy_lib.fetch_blocking)
```
#### `sync-io-in-async-fn` (error) — Sync I/O inside async function blocks the event loop.

Calling `time.sleep`, `requests.get`, `open` (sync), or other blocking I/O inside an `async def` freezes the entire event loop. AI assistants mix these up when generating async code. Use the async equivalent: `asyncio.sleep`, `httpx.AsyncClient`, `aiofiles.open`, or wrap blocking calls in `asyncio.to_thread(...)`.

**DON'T**
```python
async def fetch_user(id: int) -> dict:
    time.sleep(1)  # blocks the entire event loop
    return requests.get(f"/users/{id}").json()
```

**DO**
```python
async def fetch_user(id: int) -> dict:
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        r = await client.get(f"/users/{id}")
        return r.json()
```
### AI-Slop Imports
#### `conditional-import-outside-try` (warning) — Conditional import outside try/except. Wrap in try/except ImportError.

AI assistants often write `if sys.version_info < (3, 11): import tomli` without a try/except guard. If the import fails on an unexpected system, the error is cryptic and uncatchable. Wrap conditional imports in try/except ImportError to fail loudly with a useful message, or restructure to use importlib.util.find_spec for capability checks.

**DON'T**
```python
import sys
if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
```

**DO**
```python
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # py<3.11
```
#### `duplicate-import` (warning) — Same module imported twice in this file.

Importing the same module multiple times in a file is dead code that AI assistants often produce when stitching together snippets. Remove the duplicate. If aliases differ intentionally (e.g. `import numpy as np` and `import numpy.linalg as nla`), the rule won't fire because the dotted module names differ.

**DON'T**
```python
import json
from typing import Any
import json  # duplicate
```

**DO**
```python
import json
from typing import Any
```
#### `import-without-use` (warning) — Imported but never used.

Unused imports are the most common AI slop pattern: AI assistants import things they think they'll need, then change their mind. Remove the import. If you intentionally export it for re-import elsewhere, add it to `__all__`. If it's for type-checking only, move it under `if TYPE_CHECKING:`.

**DON'T**
```python
import json
import os

def cwd() -> str:
    return os.getcwd()  # json is never used
```

**DO**
```python
import os

def cwd() -> str:
    return os.getcwd()
```
#### `wildcard-import` (warning) — Wildcard import obscures what's in scope. Import names explicitly.

`from module import *` makes it impossible to tell where a name comes from and breaks tools (linters, type checkers, IDE autocomplete) that need to resolve names statically. AI assistants often generate this when they're uncertain what to import. Import names explicitly: `from module import a, b, c`.

**DON'T**
```python
from os import *

cwd = getcwd()  # where did this name come from?
```

**DO**
```python
from os import getcwd, environ

cwd = getcwd()
```
### Stale Loop Patterns
#### `mutate-list-during-iteration` (error) — Mutating a list while iterating it produces unpredictable results.

`for x in lst: lst.append(...)` (or remove/pop) gives unpredictable behavior in Python: items may be skipped, duplicated, or trigger IndexError. AI assistants generate this when implementing filters or batched operations. Iterate over a copy (`for x in lst[:]`), build a new list with comprehension, or collect deletions for a post-loop sweep.

**DON'T**
```python
for item in items:
    if item.stale:
        items.remove(item)  # iterator skips the next element
```

**DO**
```python
items = [item for item in items if not item.stale]
```
#### `range-len-loop` (warning) — Use `enumerate(x)` instead of `range(len(x))`.

`for i in range(len(x)):` is a Python-2 idiom. In Python 3, use `for i, item in enumerate(x):` to get both index and value, or `for item in x:` if you only need the value. AI assistants produce this pattern when translating from older code or when uncertain.

**DON'T**
```python
for i in range(len(items)):
    print(i, items[i])
```

**DO**
```python
for i, item in enumerate(items):
    print(i, item)
```
#### `time-sleep-in-test` (warning) — time.sleep in tests makes the suite slow and flaky. Use mocks or freezegun.

Real `time.sleep` in test code makes the suite slow and dependent on wall clock. AI assistants generate this to 'wait for' async or network operations. Use proper synchronization primitives (Event, asyncio.wait), mock the clock with freezegun or pytest-mock, or use `asyncio.sleep` inside async tests (which test runners can fast-forward).

**DON'T**
```python
def test_eventual_consistency():
    publish(event)
    time.sleep(2)  # slow, flaky, and hides the real timing bug
    assert store.has(event.id)
```

**DO**
```python
def test_eventual_consistency():
    publish(event)
    wait_until(lambda: store.has(event.id), timeout=2)
```
### N+1 / Performance
#### `nested-loop-append` (warning) — Nested for-loop with .append builds a list O(N*M) one item at a time.

AI assistants often write `for x in xs: for y in ys: out.append(f(x, y))` when a list comprehension or `itertools.product` is clearer and faster. Prefer `out = [f(x, y) for x in xs for y in ys]` or `list(itertools.chain.from_iterable(...))`. Comprehensions allocate once; .append in a tight loop incurs repeated method-lookup and list-resize overhead.

**DON'T**
```python
result = []
for x in xs:
    for y in ys:
        result.append(combine(x, y))
```

**DO**
```python
result = [combine(x, y) for x in xs for y in ys]
```
#### `repeated-dict-lookup` (warning) — Same dict key looked up 3+ times in one block. Bind to a local.

Repeated `d["key"]` lookups within one block read the dict each time. Bind the value to a local variable once at the top of the block: `x = d["key"]` then reference `x`. AI assistants generate this pattern when they're stitching independently-generated lines that all reach into the same dict. Three or more lookups of the same literal key is the threshold.

**DON'T**
```python
def normalize(config: dict) -> None:
    config["host"] = config["host"].lower()
    if config["host"] == "localhost":
        config["host"] = "127.0.0.1"
```

**DO**
```python
def normalize(config: dict) -> None:
    host = config["host"].lower()
    if host == "localhost":
        host = "127.0.0.1"
    config["host"] = host
```
#### `str-concat-in-loop` (warning) — String concatenation inside a loop is O(N^2). Use .join() or io.StringIO.

Each `s += other` copies the entire current string into a new object — O(N^2) total work for N iterations. CPython has a special case that sometimes optimizes this, but it's brittle and breaks under refactoring. Collect parts in a list and call `''.join(parts)` once, or use `io.StringIO()` + `.write(...)` + `.getvalue()`.

**DON'T**
```python
out = ""
for row in rows:
    out += row + "\n"  # O(N^2)
```

**DO**
```python
out = "\n".join(rows)  # one allocation
```
### Fake Type Hints
#### `any-everywhere` (warning) — `Any` on a public function parameter or return type disables type-checking.

AI assistants annotate parameters with `Any` when uncertain about the real type. This silently disables type-checking at the boundary. Replace `Any` with the specific type, a Union, a Protocol, or a TypeVar. If you genuinely need an opaque type, use `object` (forces explicit downcasting) or document why `Any` is correct.

**DON'T**
```python
def process(data: Any) -> Any:  # 'I'm not sure of the type' — figure it out
    return data["value"]
```

**DO**
```python
def process(data: dict[str, int]) -> int:
    return data["value"]
```
#### `generic-without-typevar` (warning) — `Generic[X]` requires X to be a TypeVar declared with TypeVar().

Using `Generic[T]` without declaring `T = TypeVar('T')` makes the class non-generic at runtime (T is treated as a regular name). AI assistants produce this pattern when faking parameterized types. Declare the TypeVar at module scope: `T = TypeVar('T')` (or `from typing import TypeVar`) before the class.

**DON'T**
```python
class Cache(Generic[T]):  # T is undefined
    ...
```

**DO**
```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Cache(Generic[T]):
    ...
```
#### `missing-return-type` (warning) — Public function missing return type annotation.

Every public function should declare its return type. AI assistants often skip return annotations when generating quickly. Add `-> T` where T is the actual return type. For procedures that return nothing, use `-> None`. For private functions (leading underscore), this rule does not apply.

**DON'T**
```python
def total(items):
    return sum(items)
```

**DO**
```python
def total(items: list[int]) -> int:
    return sum(items)
```
Run `aidoctor scan --explain <rule_id>` for the full rationale on any rule.

## Common AI-slop combinations

Slop travels in packs. If you spot one, scan for the others — patching individual lines won't fix the underlying pattern. **Delete and rewrite the block.**

```python
# "defensive stub" — fake types + bare except + stub
def fetch_data(source: Any) -> Any:    # any-everywhere
    try:
        # TODO: implement              # stub-comment + todo-without-ticket
        return None
    except Exception:                  # except-exception-swallowing
        pass                           # bare-except-pass

# "loop slop" — range(len) + str-concat + mutate-while-iter
out = ""
for i in range(len(rows)):             # range-len-loop
    if rows[i].stale:
        rows.remove(rows[i])           # mutate-list-during-iteration
    out += rows[i].name + "\n"         # str-concat-in-loop

# "leaked credentials" — secret literal + swallowed auth error
API_KEY = "sk-proj-9f8e7d6c5b4a3210"  # hardcoded-api-key
try:
    client.auth(API_KEY)
except Exception:                      # except-exception-swallowing
    logger.error("auth failed")        # caller never knows
```

## Pre-emit verification checklist

After drafting, before emitting. Every box must check. If any fails, **rewrite — do not annotate-and-ship.**

- [ ] No secret-shaped literal (`AKIA*`, `ASIA*`, `eyJ*.eyJ*.*`, `sk-*`, ≥12 chars on `KEY`/`TOKEN`/`SECRET`/`PASSWORD`/`AUTH`).
- [ ] Every `except` names a specific class. Top-level `except Exception` re-raises.
- [ ] No `from X import *`, duplicate imports, or conditional imports outside `try/except ImportError`.
- [ ] Every import is used (or under `if TYPE_CHECKING:` / in `__all__`).
- [ ] No `range(len(...))`. No list mutation during iteration of the same list.
- [ ] No `time.sleep` in `tests/` or `test_*.py`. Use `wait_until` / fake clocks.
- [ ] No stub comments (`# implement this`, `# placeholder`, `# your code here`). Use `raise NotImplementedError("...")`.
- [ ] Every `TODO`/`FIXME`/`HACK` carries a ticket ref or URL.
- [ ] No `raise` after unconditional `return`.
- [ ] No `x is not None and isinstance(x, T)`.
- [ ] Public functions have return annotations (`-> T` or `-> None`).
- [ ] No `Any` on public types without a `# reason:` justification.
- [ ] No sync I/O (`time.sleep`, `requests.*`) inside `async def`. Use `asyncio.sleep` / `httpx` / `asyncio.to_thread`.
- [ ] Every `# aidoctor: disable=` has a `# reason:` neighbor.

Any unchecked? Fix, then respond. `aidoctor scan` is the source of truth — the user will run it.

## Related

- `aidoctor scan .` — verify after generating.
- `aidoctor scan --explain <rule_id>` — long-form rationale for a single rule.
- `aidoctor score` — composite penalty across unique rules tripped.
- https://github.com/ankit-aglawe/aidoctor — rule source.