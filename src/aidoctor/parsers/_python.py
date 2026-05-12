"""Python parser wrapper.

Uses libcst (already a project dependency; powers v1.1 rules). For comment
extraction we use the stdlib `tokenize` module — cheaper than building a
full CST when all we need are comment positions, and matches Python's own
parser semantics (no chance of catching `#` inside a string literal).
"""

from __future__ import annotations

import io
import tokenize
from typing import Iterator

from aidoctor.parsers import CommentNode


def extract_comments(source: bytes | str) -> Iterator[CommentNode]:
    """Yield every Python comment via stdlib tokenize.

    Strings containing `#` are NOT comments and won't be yielded.
    """
    if isinstance(source, bytes):
        source = source.decode("utf-8", errors="replace")
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.COMMENT:
                continue
            line, column = tok.start
            # tok.string is e.g. "# NOTE: x" — strip the "#"
            text = tok.string
            if text.startswith("#"):
                text = text[1:]
            # Trim one optional leading space ("# x" → "x", "#x" → "x")
            if text.startswith(" "):
                text = text[1:]
            yield CommentNode(line=line, column=column, text=text)
    except tokenize.TokenizeError:
        return
