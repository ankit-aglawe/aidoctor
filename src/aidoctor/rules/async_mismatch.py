"""Async/Sync Mismatch rules.

AI assistants frequently mix sync and async incorrectly: blocking calls inside
async functions, asyncio.run inside an already-running event loop, sync I/O
where the function is meant to be awaited.
"""

from __future__ import annotations

from typing import Any

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity

# Sync I/O calls that block. If found inside an `async def`, that's bad.
SYNC_IO_NAMES = frozenset({"open", "input", "print"})
# Sync I/O via known modules.
SYNC_IO_MODULES = {
    "time": frozenset({"sleep"}),
    "requests": frozenset({"get", "post", "put", "delete", "patch", "request", "head"}),
    "urllib": frozenset({"urlopen"}),
    "socket": frozenset({"create_connection"}),
    "subprocess": frozenset({"run", "call", "check_call", "check_output", "Popen"}),
}


class SyncIoInAsyncFnRule(Rule):
    """Detects sync I/O builtins / known-blocking calls inside an `async def`."""

    rule_id = "sync-io-in-async-fn"
    severity = Severity.ERROR
    category = Category.ASYNC_MISMATCH
    message = "Sync I/O inside async function blocks the event loop."
    help = (
        "Calling `time.sleep`, `requests.get`, `open` (sync), or other blocking "
        "I/O inside an `async def` freezes the entire event loop. AI assistants "
        "mix these up when generating async code. Use the async equivalent: "
        "`asyncio.sleep`, `httpx.AsyncClient`, `aiofiles.open`, or wrap blocking "
        "calls in `asyncio.to_thread(...)`."
    )
    url = "https://github.com/aidoctor/aidoctor#sync-io-in-async-fn"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._async_depth = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.asynchronous is not None:
            self._async_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        if original_node.asynchronous is not None:
            self._async_depth -= 1

    def visit_Call(self, node: cst.Call) -> None:
        if self._async_depth <= 0:
            return
        func = node.func
        # Direct name call: `print(...)`, `open(...)`, etc.
        if isinstance(func, cst.Name) and func.value in SYNC_IO_NAMES:
            self.report(node, message=f"Sync `{func.value}` inside async function blocks the event loop.")
            return
        # Attribute call: `time.sleep(...)`, `requests.get(...)`.
        if isinstance(func, cst.Attribute) and isinstance(func.value, cst.Name):
            mod_name = func.value.value
            method = func.attr.value
            mod_methods = SYNC_IO_MODULES.get(mod_name)
            if mod_methods is not None and method in mod_methods:
                self.report(
                    node,
                    message=f"Sync `{mod_name}.{method}` inside async function blocks the event loop.",
                )


class AsyncioRunInsideAsyncFnRule(Rule):
    """Detects `asyncio.run(...)` called from inside an `async def` — common AI mistake."""

    rule_id = "asyncio-run-inside-async-fn"
    severity = Severity.ERROR
    category = Category.ASYNC_MISMATCH
    message = "asyncio.run inside an async function raises RuntimeError at runtime."
    help = (
        "`asyncio.run(...)` creates a new event loop and is intended for the "
        "top-level entry point of a program. Calling it inside another `async def` "
        "raises `RuntimeError: This event loop is already running`. Use "
        "`await coro()` to call the coroutine, or `asyncio.create_task(coro())` "
        "to schedule it. AI assistants reach for `asyncio.run` when they're "
        "uncertain about how to await something."
    )
    url = "https://github.com/aidoctor/aidoctor#asyncio-run-inside-async-fn"

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._async_depth = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.asynchronous is not None:
            self._async_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        if original_node.asynchronous is not None:
            self._async_depth -= 1

    def visit_Call(self, node: cst.Call) -> None:
        if self._async_depth <= 0:
            return
        func = node.func
        if (
            isinstance(func, cst.Attribute)
            and isinstance(func.value, cst.Name)
            and func.value.value == "asyncio"
            and func.attr.value == "run"
        ):
            self.report(node)


class BlockingCallInEventLoopRule(Rule):
    """HEURISTIC: detects suspiciously-named blocking calls inside async functions.

    Flagged as heuristic — false-positive prone but still useful as a warning.
    """

    rule_id = "blocking-call-in-event-loop"
    severity = Severity.WARNING
    category = Category.ASYNC_MISMATCH
    message = "Suspicious blocking call inside async function."
    help = (
        "HEURISTIC RULE — may have false positives. Calls whose names end in "
        "`_sync` or `_blocking`, or that match common-blocking patterns like "
        "`sleep`, `wait`, `recv`, found inside `async def` are flagged. If "
        "this is intentional (e.g., the call is non-blocking in your context), "
        "suppress with `# aidoctor: disable=blocking-call-in-event-loop`."
    )
    url = "https://github.com/aidoctor/aidoctor#blocking-call-in-event-loop"

    SUSPECT_SUFFIXES = ("_sync", "_blocking")
    SUSPECT_NAMES = frozenset({"sleep", "wait_for", "recv", "recv_into", "read", "readline"})

    def __init__(self, context: Any) -> None:
        super().__init__(context)
        self._async_depth = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if node.asynchronous is not None:
            self._async_depth += 1

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        if original_node.asynchronous is not None:
            self._async_depth -= 1

    def visit_Call(self, node: cst.Call) -> None:
        if self._async_depth <= 0:
            return
        func = node.func
        name: str | None = None
        if isinstance(func, cst.Name):
            name = func.value
        elif isinstance(func, cst.Attribute):
            name = func.attr.value
        if name is None:
            return
        if name.endswith(self.SUSPECT_SUFFIXES):
            self.report(node)
            return
        # Whitelist asyncio.sleep / asyncio.wait_for / asyncio.recv — those are async.
        if name in self.SUSPECT_NAMES:
            if (
                isinstance(func, cst.Attribute)
                and isinstance(func.value, cst.Name)
                and func.value.value in {"asyncio", "trio", "anyio"}
            ):
                return
            # io.read/readline on a sync stream inside async is bad.
            # Plain `read` / `readline` as method calls are ambiguous, so warn.
            self.report(node)
