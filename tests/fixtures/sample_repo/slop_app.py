"""Fixture: a file that violates rules in every category. The 'AI slop' demo file."""

# TODO: implement this properly
# FIXME: hack to get tests passing
# placeholder
import json
import sys
from os import *  # wildcard import

if sys.version_info < (3, 11):
    pass  # conditional import outside try

# Hardcoded secrets across the file.
API_KEY = "sk-prod-1234567890abcdefghij"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpMeJf"


def process(items):
    """Mutates list during iteration + range(len(x))."""
    for i in range(len(items)):  # range-len-loop
        print(items[i])
    for x in items:
        items.append(x * 2)  # mutate-list-during-iteration


def fetch():
    """Bare except + return then raise."""
    try:
        return json.loads("{}")
    except:  # bare-except-pass
        pass
    return None
    raise RuntimeError("unreachable")  # unreachable-raise


def swallow(data):
    """Swallows Exception with a log instead of re-raising."""
    try:
        return data.get("x")
    except Exception:  # except-exception-swallowing
        print("oh well")
        return None


def check(x):
    """Redundant null check."""
    if x is not None and isinstance(x, str):  # redundant-null-check-after-isinstance
        return x
    return ""


def unused_import_user():
    """References only json, leaves tomli/sys nominally used."""
    return json.dumps({"ok": True})


# --- async/sync mismatch ---
import asyncio
import time

import requests


async def bad_async():
    """Triggers sync-io-in-async-fn, asyncio-run-inside-async-fn, blocking-call-in-event-loop."""
    time.sleep(1)  # sync-io-in-async-fn
    requests.get("http://x")  # sync-io-in-async-fn (different builtin)
    asyncio.run(other())  # asyncio-run-inside-async-fn
    legacy_fetch_sync()  # blocking-call-in-event-loop


async def other():
    pass


def legacy_fetch_sync():
    return None


# --- fake type hints ---
from typing import Any, Generic  # noqa


def opaque_api(data: Any) -> Any:  # any-everywhere
    return data


class Cache(Generic[T]):  # generic-without-typevar (T is undefined)
    pass


# --- perf rules ---
def nested_accum(xs, ys):
    """nested-loop-append + str-concat-in-loop + repeated-dict-lookup."""
    out = []
    s = ""
    for x in xs:
        for y in ys:
            out.append((x, y))  # nested-loop-append
        s += "tick\n"  # str-concat-in-loop


def repeated_lookup(config):
    """repeated-dict-lookup (same key 3+ times)."""
    config["host"] = config["host"].lower()
    if config["host"] == "localhost":
        config["host"] = "127.0.0.1"


# --- time.sleep in tests is covered by test files, not here ---
