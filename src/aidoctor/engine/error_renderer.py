"""Central error renderer for aidoctor.

Every rescue site in the codebase routes its user-facing error message
through `render_error()` so error UX stays consistent: classname,
what-was-attempted, file:line, and a fix hint. Drift between rescue sites
is exactly the failure mode CEO Section 2 calls out.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ErrorContext:
    attempting: str
    file: Path | None = None
    line: int | None = None
    remediation: str | None = None

    def __post_init__(self) -> None:
        if not self.attempting:
            raise ValueError(
                "ErrorContext.attempting is mandatory — every error must say "
                "what was being tried (per CEO Section 2 rescue policy)"
            )


def render_error(exc: BaseException, ctx: ErrorContext) -> str:
    """Render an exception as a single-string user-facing message.

    Output shape (stable; tests pin it):

        ERROR <Classname>: <message>
          while: <what was being attempted>
          at:    <file>:<line>           (when file given; line optional)
          fix:   <remediation hint>      (when given)
    """
    lines = [f"ERROR {type(exc).__name__}: {exc}"]
    lines.append(f"  while: {ctx.attempting}")
    if ctx.file is not None:
        location = f"{ctx.file}:{ctx.line}" if ctx.line is not None else str(ctx.file)
        lines.append(f"  at:    {location}")
    if ctx.remediation:
        lines.append(f"  fix:   {ctx.remediation}")
    return "\n".join(lines)
