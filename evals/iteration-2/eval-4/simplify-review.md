# /aidoctor:simplify — eval-4 stub-out-todo baseline review

## Phase 1 — Identified changes

The entire file (26 lines) is treated as just-written. Two top-level functions, both stubs:

```python
"""Billing module (work in progress).

Stubs for card charging and refunding. Real implementation lands next sprint.
"""

from __future__ import annotations


def charge_card(amount: int) -> None:
    """Charge a card for the given amount (in minor currency units).

    Args:
        amount: Amount to charge, in the smallest currency unit (e.g. cents).
    """
    # TODO(next-sprint): Integrate with payment processor to charge the card.
    raise NotImplementedError("charge_card is not implemented yet")


def refund_card(charge_id: str) -> None:
    """Refund a previously successful charge.

    Args:
        charge_id: Identifier of the charge to refund.
    """
    # TODO(next-sprint): Look up the charge and issue a refund via the processor.
    raise NotImplementedError("refund_card is not implemented yet")
```

Shape: two stub functions, both `-> None`, both raising `NotImplementedError` with a string echoing the function name plus a TODO comment immediately above the raise. Module is described as work-in-progress in the docstring.

## Phase 2 — Three-angle findings

### Reviewer 1: Code Reuse

- **R1.1 — Duplicated stub shape across two functions.** Both bodies are structurally identical: a TODO comment followed by `raise NotImplementedError("<name> is not implemented yet")`. The exception message itself is just a string echo of the function name plus a fixed suffix — Python's default `NotImplementedError()` (no args) already produces an equivalent signal because the traceback names the function. The string adds no information that the traceback does not already carry.
- **R1.2 — `NotImplementedError` message duplication.** If a project convention emerges (e.g. "stub raises with TODO reference"), it should live in a tiny `_stub()` helper or just be left as bare `raise NotImplementedError`. Inlining the exact same string template twice is reuse debt the moment a third stub is added.
- **R1.3 — No existing utility appears to exist for this**, but worth flagging: if `payments/` or `billing/` already has a processor client, these stubs may shadow real code. Cannot verify from the single file — caller should grep before landing.

Severity: low-to-medium. Two stubs is below the threshold where a helper pays off, but the redundancy is visible.

### Reviewer 2: Code Quality

- **Q2.1 — TODO comment is redundant with the docstring + raise.** The module docstring already says "work in progress … real implementation lands next sprint." Each function's body then says the same thing in a TODO and again via `NotImplementedError`. That's three sources of truth for "this is a stub." Per the skill's quality rule 7 ("Unnecessary comments: explaining WHAT … delete; keep only non-obvious WHY"), the TODO line explains WHAT is missing, which the `NotImplementedError` already conveys. The non-obvious WHY (next sprint, integrate with processor) belongs in the issue tracker, not the source.
- **Q2.2 — Stringly-typed self-reference in the exception message.** `"charge_card is not implemented yet"` hard-codes the function name as a string. Rename the function and the message drifts. Bare `raise NotImplementedError` avoids this entirely; if a custom message is wanted, use `f"{__name__}.{<func>.__qualname__}"` — but better to just drop it.
- **Q2.3 — `-> None` return type on stubs that will plausibly return something.** `charge_card` in real life almost always returns a charge ID or a result object; `refund_card` similarly returns a refund record. Locking the return type to `None` now creates a breaking change later. For a stub, either omit the annotation, return `NoReturn` (since it only raises), or annotate with the eventual real type. `NoReturn` is the most honest choice for a function whose entire body is `raise`.
- **Q2.4 — TODO without ticket reference.** The aidoctor rule against unreferenced TODOs typically wants a ticket ID (e.g. `TODO(PAY-123)`), not a vague time hint like `(next-sprint)`. "next-sprint" is unverifiable and rots the moment the sprint ends.
- **Q2.5 — Module-level "work in progress" docstring is also a smell.** WIP markers in source tend to outlive the work. A merged file should not advertise itself as WIP; that state belongs in the PR/branch, not the committed code.

Severity: medium. None of these are bugs (the file does nothing), but every single line is doing duplicate or fragile work.

### Reviewer 3: Efficiency

- **E3.1 — Nothing to flag on runtime efficiency.** Both functions raise unconditionally; there is no hot path, no loop, no I/O, no allocation worth measuring.
- **E3.2 — Cognitive efficiency, however, is low.** A stub file should be the smallest possible thing. The current file spends 26 lines saying "two unimplemented functions exist." A leaner version conveys the same contract in roughly half the lines and is faster to scan during review. This isn't runtime efficiency but it is the spirit of "unnecessary work" applied to the reader.
- **E3.3 — `from __future__ import annotations` is unused.** Neither signature uses a forward reference, a string-quoted type, or a `|`-style union that would need it on older Python. On 3.10+ it's a no-op for these signatures. Harmless but cargo-cult.

Severity: low. Pure stub, no runtime cost. The `__future__` import is dead weight.

## Phase 3 — Decision brief

Phase 2 complete. Reuse: 3 findings. Quality: 5 findings. Efficiency: 3 findings. Total unique after dedup: 7 (Q2.1 + R1.1 + E3.2 collapse to one "the file is over-explained" finding; the rest stand alone).

Consensus (2+ reviewers): **the file repeats itself**. Reuse, Quality, and Efficiency all hit the same nerve — the TODO comment, the `NotImplementedError` string, and the module docstring are three echoes of one fact. That is the highest-signal fix.

Single-source but worth fixing:
- Q2.3 (`-> None` vs `NoReturn`) — small, correct, prevents future churn.
- Q2.4 (TODO without ticket) — aidoctor-rule-shaped; cheap to fix.
- E3.3 (unused `from __future__`) — one-line delete.

Single-source taste calls:
- Q2.5 (drop the WIP docstring) — opinion-shaped; some teams want the marker.
- R1.2 (extract `_stub()` helper) — premature at N=2 functions; revisit at N=3.

D1 — Which findings should I fix?
ELI10: Three reviewers flagged 7 unique issues. The big one all three agree on is that the file says "this is a stub" three different times. Several small ones are easy wins. Two are taste calls.
Recommendation: **A** — fix the consensus finding plus the cheap single-source wins (Q2.3, Q2.4, E3.3). Skip the taste calls.

A) Fix consensus + cheap wins (recommended)
   - Collapse the triple-echo (drop TODO comments, drop self-naming exception strings)
   - Switch `-> None` to `NoReturn`
   - Add a ticket ID to any TODO that survives, or remove it
   - Drop unused `from __future__ import annotations`
   ✅ Smallest reviewable diff, addresses every issue 2+ reviewers raised
   ❌ Leaves the WIP docstring and does not extract a helper

B) Fix all 7 findings
   ✅ Cleanest end state
   ❌ Includes taste calls (`_stub()` helper, WIP docstring removal) that may be premature

C) Show me the list, I'll pick
   ✅ Full control
   ❌ Slower

Net: A. The consensus finding plus the three one-liners are unambiguous wins; the helper and the WIP-docstring debate can wait for a third stub or a team convention.

## Phase 4 — If user accepts your recommendation

Apply, one isolated edit per finding, in this order:

1. **Drop `from __future__ import annotations`** — unused. One-line delete.
2. **Change return type to `NoReturn`** — import `from typing import NoReturn`, change both signatures from `-> None` to `-> NoReturn`. Honest about the function's actual behavior (it only raises) and leaves the eventual real return type unconstrained.
3. **Collapse the triple-echo** — remove the `# TODO(next-sprint): ...` comment from each body and shorten the raise to bare `raise NotImplementedError`. The module docstring is enough context; the traceback names the function.
4. **Decide on the TODO** — if the team wants a TODO at all, it goes in the tracker, not the source. If a source TODO is required, give it a ticket ID: `# TODO(PAY-123): ...`. Recommend dropping entirely since the `NotImplementedError` already signals "not done."
5. **Run `aidoctor scan`** on `main.py` and confirm the score moved up. If not, re-read the output — likely candidates that did not improve: the WIP module docstring (Q2.5, deliberately skipped) and any aidoctor rule about empty function bodies.

Expected post-fix shape (≈14 lines vs original 26):

```python
"""Billing: card charge and refund (stubs)."""

from typing import NoReturn


def charge_card(amount: int) -> NoReturn:
    """Charge a card for the given amount (in minor currency units)."""
    raise NotImplementedError


def refund_card(charge_id: str) -> NoReturn:
    """Refund a previously successful charge."""
    raise NotImplementedError
```

Skipped and why:
- **Q2.5 (WIP docstring)** — taste call; leaving the one-liner "stubs" marker is enough and does not date itself the way "work in progress, lands next sprint" does. Already softened in the proposed shape.
- **R1.2 (`_stub()` helper)** — YAGNI at N=2. Revisit when a third stub lands.
