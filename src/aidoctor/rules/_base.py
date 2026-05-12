"""Core data model for aidoctor rules.

Every rule violation produces a Diagnostic. The score formula penalizes
unique rules tripped, not violation count.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst
from libcst.metadata import PositionProvider


class Severity(str, enum.Enum):
    ERROR = "error"
    WARNING = "warning"


class Category(str, enum.Enum):
    IMPORTS = "imports"
    DEAD_DEFENSES = "dead-defenses"
    ASYNC_MISMATCH = "async-mismatch"
    SECRETS = "secrets"
    TYPE_HINTS = "type-hints"
    LOOPS = "loops"
    PERF = "perf"
    DECAY = "decay"
    AI_STYLE = "ai-style"
    SECURITY = "security"


CATEGORY_LABELS: dict[Category, str] = {
    Category.IMPORTS: "AI-Slop Imports",
    Category.DEAD_DEFENSES: "Dead Defenses",
    Category.ASYNC_MISMATCH: "Async/Sync Mismatch",
    Category.SECRETS: "Hardcoded Secrets",
    Category.TYPE_HINTS: "Fake Type Hints",
    Category.LOOPS: "Stale Loop Patterns",
    Category.PERF: "N+1 / Performance",
    Category.DECAY: "Comment-Driven Decay",
    Category.AI_STYLE: "AI Style Fingerprints",
    Category.SECURITY: "Security",
}


@dataclass(slots=True, frozen=True)
class Diagnostic:
    """A single rule violation. Flows from rules to scan to score to render."""

    rule_id: str
    severity: Severity
    category: Category
    file: Path
    line: int
    column: int
    message: str
    help: str
    url: str = ""
    suppression_hint: str | None = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "category": self.category.value,
            "file": str(self.file),
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "help": self.help,
            "url": self.url,
            "suppression_hint": self.suppression_hint,
        }


@dataclass
class RuleContext:
    """State passed to a rule visitor for one file scan."""

    file: Path
    source: str
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def emit(
        self,
        rule_id: str,
        severity: Severity,
        category: Category,
        line: int,
        column: int,
        message: str,
        help: str,
        url: str = "",
    ) -> None:
        self.diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity=severity,
                category=category,
                file=self.file,
                line=line,
                column=column,
                message=message,
                help=help,
                url=url,
            )
        )


class Rule(cst.CSTVisitor):
    """Base class for all rules.

    Subclass contract (set as class attributes):
        rule_id:    kebab-case unique identifier (e.g. "hardcoded-api-key")
        severity:   Severity.ERROR or Severity.WARNING
        category:   one of the Category enum values
        message:    one-line violation message shown in the report
        help:       ~100 word explanation shown via `aidoctor scan --explain RULE`
        url:        link to extended docs (optional)

    Subclasses override libcst visit_* methods to walk the CST and call self.report(node).
    Must be invoked via `wrapper.visit(rule_instance)` so PositionProvider metadata resolves.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    rule_id: str = ""
    severity: Severity = Severity.WARNING
    category: Category = Category.IMPORTS
    message: str = ""
    help: str = ""
    url: str = ""

    def __init__(self, context: RuleContext) -> None:
        super().__init__()
        self.context = context

    def report(self, node: cst.CSTNode, message: str | None = None) -> None:
        """Emit a diagnostic at the position of `node` for this rule."""
        try:
            pos = self.get_metadata(PositionProvider, node)
            line = pos.start.line
            col = pos.start.column
        except KeyError:
            line, col = 1, 0
        self.context.emit(
            rule_id=self.rule_id,
            severity=self.severity,
            category=self.category,
            line=line,
            column=col,
            message=message or self.message,
            help=self.help,
            url=self.url,
        )
