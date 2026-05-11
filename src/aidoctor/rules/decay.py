"""Comment-Driven Decay rules.

AI assistants leave TODO/FIXME/HACK comments without ticket references, and
stub comments like `# implement this` or `# TODO: implement`. These mark
half-finished code as if it were complete.
"""

# aidoctor: disable-file=stub-comment,hardcoded-api-key,todo-without-ticket

from __future__ import annotations

import re

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity

# Match TODO/FIXME/HACK/XXX/BUG that don't include a ticket reference.
# Ticket patterns: #123, JIRA-456, GH-789, [TICKET-1], or a URL.
TODO_WITHOUT_TICKET_RE = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|BUG)(?!.*(?:#\d+|[A-Z]{2,}-\d+|GH-\d+|https?://))",
    re.IGNORECASE,
)

# Stub-comment patterns: `# implement this`, `# TODO: implement`, `# placeholder`,
# `# not implemented`, `# fill in`, etc.
STUB_COMMENT_RE = re.compile(
    r"(?:implement\s+this|TODO:?\s*implement|placeholder|not\s+implemented"
    r"|fill\s+in|add\s+code\s+here|your\s+code\s+goes\s+here)",
    re.IGNORECASE,
)


class TodoWithoutTicketRule(Rule):
    """Detects TODO/FIXME/HACK comments without a ticket reference."""

    rule_id = "todo-without-ticket"
    severity = Severity.WARNING
    category = Category.DECAY
    message = "TODO without ticket reference. Add a ticket ID or URL so it doesn't rot."
    help = (
        "Bare TODO/FIXME/HACK comments rot in the codebase forever. Pair every TODO "
        "with a ticket reference (`# TODO(JIRA-1234): ...`, `# TODO #456:`, "
        "`# FIXME(https://github.com/...)`) so it's tracked outside the code. If "
        "there's no ticket, decide: fix it now, delete the TODO, or open a ticket. "
        "AI assistants leave bare TODOs when uncertain — those usually mean unfinished "
        "work, not future work."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#todo-without-ticket"

    def visit_Comment(self, node: cst.Comment) -> None:
        text = node.value
        if TODO_WITHOUT_TICKET_RE.search(text):
            self.report(node)


class StubCommentRule(Rule):
    """Detects stub comments like `# implement this` or `# TODO: implement`."""

    rule_id = "stub-comment"
    severity = Severity.ERROR
    category = Category.DECAY
    message = "Stub comment indicates unfinished AI-generated code."
    help = (
        "Comments like `# implement this`, `# placeholder`, or `# your code here` "
        "are AI-assistant artifacts marking unfinished code. Either complete the "
        "implementation, remove the comment, or raise NotImplementedError explicitly "
        "so the failure mode is visible at runtime."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#stub-comment"

    def visit_Comment(self, node: cst.Comment) -> None:
        text = node.value
        if STUB_COMMENT_RE.search(text):
            self.report(node)
