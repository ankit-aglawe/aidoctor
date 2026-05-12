"""Declarative fix kinds for the JSONL rule engine.

Produces a RewriteResult given a rule + source + diagnostic. /aidoctor:deai
calls propose_fix() per HIGH-confidence finding to decide what code to
replace; the apply step then writes the replacement and re-scans.

Locked API contract (eng-review finding 1B):

    @dataclass(frozen=True)
    class RewriteResult:
        ok: bool
        original_code: str
        replacement_code: str
        line_range: tuple[int, int]
        reason_if_failed: str | None = None

Supported fix kinds:
    strip_label             — strip an emphasis prefix (NOTE/IMPORTANT/...)
    delete_emoji            — remove unicode emojis (Symbol-Other category)
    strip_comment           — delete the comment entirely (preserve any code on the same line)
    template_replacement    — substitute placeholders in a template string
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RewriteResult:
    ok: bool
    original_code: str
    replacement_code: str
    line_range: tuple[int, int]
    reason_if_failed: str | None = None


# Matches the emphasis-label prefix inside a comment.
# Captures: (1) leading "#" + whitespace, (2) the rest.
_EMPHASIS_LABEL_RE = re.compile(
    r"^(#\s*)(NOTE|IMPORTANT|CAREFUL|CRITICAL|TIP|HACK|FIXME|TODO|WARNING):\s*(.*)$"
)


def propose_fix(rule, source: str, diagnostic) -> RewriteResult:
    """Produce a rewrite for one diagnostic. Never raises; returns ok=False on failure.

    /aidoctor:deai loops over many findings; failure of one fix must not
    abort the loop. The caller decides whether to skip, prompt, or revert.
    """
    if rule.fix is None:
        return _failure("rule has no fix block; detect-only", diagnostic.line)

    kind = rule.fix.get("kind")
    line_no = diagnostic.line
    lines = source.splitlines()

    if line_no < 1 or line_no > len(lines):
        return _failure(f"line {line_no} out of range (file has {len(lines)} lines)", line_no)
    original_line = lines[line_no - 1]

    if kind == "strip_label":
        return _fix_strip_label(original_line, line_no)
    if kind == "delete_emoji":
        return _fix_delete_emoji(original_line, line_no)
    if kind == "strip_comment":
        return _fix_strip_comment(original_line, line_no)
    if kind == "template_replacement":
        return _fix_template_replacement(rule.fix, original_line, line_no)
    return _failure(f"unknown fix kind: {kind!r}", line_no)


def _failure(reason: str, line_no: int) -> RewriteResult:
    return RewriteResult(
        ok=False,
        original_code="",
        replacement_code="",
        line_range=(line_no, line_no),
        reason_if_failed=reason,
    )


def _fix_strip_label(line: str, line_no: int) -> RewriteResult:
    """Convert `# NOTE: x` → `# x`. Keeps the comment, drops the label."""
    m = _EMPHASIS_LABEL_RE.match(line.strip())
    if not m:
        return _failure("line does not match an emphasis-label pattern", line_no)
    prefix, _label, rest = m.groups()
    return RewriteResult(
        ok=True,
        original_code=line.strip(),
        replacement_code=f"{prefix}{rest}".rstrip(),
        line_range=(line_no, line_no),
    )


def _fix_delete_emoji(line: str, line_no: int) -> RewriteResult:
    """Remove characters in Unicode 'So' category (emojis like ✓ ✨ 🎉).

    `Sk` (Symbol, Modifier) was dropped after real-world testing on aidoctor's
    own source revealed all 90 'emoji' findings were the backtick character
    (U+0060 GRAVE ACCENT, Sk) used in code-style comments like `# Form: \\`...\\``.
    """
    cleaned = "".join(ch for ch in line if unicodedata.category(ch) != "So")
    # Collapse runs of internal whitespace introduced by emoji removal.
    cleaned = re.sub(r"  +", " ", cleaned).rstrip()
    if cleaned == line.rstrip():
        return _failure("no emoji to delete on this line", line_no)
    return RewriteResult(
        ok=True,
        original_code=line.rstrip(),
        replacement_code=cleaned,
        line_range=(line_no, line_no),
    )


def _fix_strip_comment(line: str, line_no: int) -> RewriteResult:
    """Strip the comment tail from a line.

    * Pure comment line (`# foo`) → replacement is empty.
    * Inline comment (`x = 1  # foo`) → keep `x = 1`, drop the `# foo`.
    """
    # Find the comment start, accounting for `#` inside strings via a naive scan.
    in_string: str | None = None
    for i, ch in enumerate(line):
        if in_string is not None:
            if ch == in_string and (i == 0 or line[i - 1] != "\\"):
                in_string = None
            continue
        if ch in ('"', "'"):
            in_string = ch
            continue
        if ch == "#":
            code_part = line[:i].rstrip()
            return RewriteResult(
                ok=True,
                original_code=line.rstrip(),
                replacement_code=code_part,
                line_range=(line_no, line_no),
            )
    return _failure("no comment on this line", line_no)


def _fix_template_replacement(spec: dict, line: str, line_no: int) -> RewriteResult:
    """Render `template` with `bindings` filled in.

    Template uses single-brace placeholders: `{NAME}`. Double braces escape
    a literal `{` / `}`. Bindings are applied as a single .format() call so
    every f-string `{x}` in user code stays intact via the double-brace escape.
    """
    template = spec.get("template")
    if not template:
        return _failure("template_replacement requires a 'template' field", line_no)
    bindings = spec.get("bindings", {})
    try:
        rendered = template.format(**bindings)
    except (KeyError, IndexError) as e:
        return _failure(f"template binding missing: {e}", line_no)
    return RewriteResult(
        ok=True,
        original_code=line.rstrip(),
        replacement_code=rendered,
        line_range=(line_no, line_no),
    )
