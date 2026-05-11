"""Fixture: a file that violates rules in every category. The 'AI slop' demo file."""

# TODO: implement this properly
# FIXME: hack to get tests passing
# placeholder
from os import *  # wildcard import
import json
import json  # duplicate
import sys

if sys.version_info < (3, 11):
    import tomli  # conditional import outside try

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
