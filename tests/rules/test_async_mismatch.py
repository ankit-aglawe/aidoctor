"""Tests for Async/Sync Mismatch rules."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from aidoctor.rules._base import RuleContext
from aidoctor.rules.async_mismatch import (
    AsyncioRunInsideAsyncFnRule,
    BlockingCallInEventLoopRule,
    SyncIoInAsyncFnRule,
)


def _run(rule_cls, source: str) -> list:
    ctx = RuleContext(file=Path("/tmp/x.py"), source=source)
    wrapper = cst.MetadataWrapper(cst.parse_module(source))
    wrapper.visit(rule_cls(ctx))
    return ctx.diagnostics


def test_sync_io_print_in_async_fires() -> None:
    src = "async def f():\n    print('blocked')\n"
    assert len(_run(SyncIoInAsyncFnRule, src)) == 1


def test_sync_io_open_in_async_fires() -> None:
    src = "async def f():\n    open('/tmp/x')\n"
    assert len(_run(SyncIoInAsyncFnRule, src)) == 1


def test_time_sleep_in_async_fires() -> None:
    src = "import time\nasync def f():\n    time.sleep(1)\n"
    assert len(_run(SyncIoInAsyncFnRule, src)) == 1


def test_requests_get_in_async_fires() -> None:
    src = "import requests\nasync def f():\n    requests.get('http://x')\n"
    assert len(_run(SyncIoInAsyncFnRule, src)) == 1


def test_subprocess_run_in_async_fires() -> None:
    src = "import subprocess\nasync def f():\n    subprocess.run(['ls'])\n"
    assert len(_run(SyncIoInAsyncFnRule, src)) == 1


def test_sync_io_in_sync_function_clean() -> None:
    src = "import time\ndef f():\n    time.sleep(1)\n"
    assert _run(SyncIoInAsyncFnRule, src) == []


def test_asyncio_run_inside_async_fires() -> None:
    src = "import asyncio\nasync def f():\n    asyncio.run(g())\n"
    assert len(_run(AsyncioRunInsideAsyncFnRule, src)) == 1


def test_asyncio_run_in_sync_function_clean() -> None:
    src = "import asyncio\ndef main():\n    asyncio.run(g())\n"
    assert _run(AsyncioRunInsideAsyncFnRule, src) == []


def test_blocking_call_suffix_in_async_fires() -> None:
    src = "async def f():\n    fetch_sync()\n"
    assert len(_run(BlockingCallInEventLoopRule, src)) >= 1


def test_blocking_call_blocking_suffix_fires() -> None:
    src = "async def f():\n    legacy.do_blocking()\n"
    assert len(_run(BlockingCallInEventLoopRule, src)) >= 1


def test_asyncio_sleep_is_clean() -> None:
    src = "import asyncio\nasync def f():\n    await asyncio.sleep(1)\n"
    diags = _run(BlockingCallInEventLoopRule, src)
    # asyncio.sleep is whitelisted; should NOT fire.
    assert all("asyncio.sleep" not in d.message for d in diags)


def test_blocking_call_in_sync_function_clean() -> None:
    src = "def f():\n    fetch_sync()\n"
    assert _run(BlockingCallInEventLoopRule, src) == []
