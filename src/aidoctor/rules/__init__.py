"""Explicit rule registry.

Adding a new rule:
    1. Implement it in the appropriate category file (e.g. rules/secrets.py).
    2. Import it here and append to RULES.

This is intentionally explicit, not auto-discovered. An import error on any rule
fails fast at test collection rather than silently disappearing at scan time.
"""

from __future__ import annotations

from aidoctor.rules._base import (
    CATEGORY_LABELS,
    Category,
    Diagnostic,
    Rule,
    RuleContext,
    Severity,
)
from aidoctor.rules.async_mismatch import (
    AsyncioRunInsideAsyncFnRule,
    BlockingCallInEventLoopRule,
    SyncIoInAsyncFnRule,
)
from aidoctor.rules.dead_defenses import (
    BareExceptPassRule,
    ExceptExceptionSwallowingRule,
    RedundantNullCheckAfterIsinstanceRule,
    UnreachableRaiseRule,
)
from aidoctor.rules.decay import StubCommentRule, TodoWithoutTicketRule
from aidoctor.rules.imports import (
    ConditionalImportOutsideTryRule,
    DuplicateImportRule,
    ImportWithoutUseRule,
    WildcardImportRule,
)
from aidoctor.rules.loops import (
    MutateListDuringIterationRule,
    RangeLenRule,
    TimeSleepInTestRule,
)
from aidoctor.rules.perf import (
    NestedLoopAppendRule,
    RepeatedDictLookupRule,
    StrConcatInLoopRule,
)
from aidoctor.rules.secrets import (
    AwsCredentialsRule,
    HardcodedApiKeyRule,
    JwtTokenRule,
)
from aidoctor.rules.type_hints import (
    AnyEverywhereRule,
    GenericWithoutTypeVarRule,
    MissingReturnTypeRule,
)

RULES: list[type[Rule]] = [
    # Secrets (3)
    HardcodedApiKeyRule,
    AwsCredentialsRule,
    JwtTokenRule,
    # Imports (4)
    WildcardImportRule,
    DuplicateImportRule,
    ConditionalImportOutsideTryRule,
    ImportWithoutUseRule,
    # Dead defenses (4)
    BareExceptPassRule,
    ExceptExceptionSwallowingRule,
    UnreachableRaiseRule,
    RedundantNullCheckAfterIsinstanceRule,
    # Loops (3)
    RangeLenRule,
    MutateListDuringIterationRule,
    TimeSleepInTestRule,
    # Async/Sync Mismatch (3)
    SyncIoInAsyncFnRule,
    AsyncioRunInsideAsyncFnRule,
    BlockingCallInEventLoopRule,
    # Type Hints (3)
    AnyEverywhereRule,
    MissingReturnTypeRule,
    GenericWithoutTypeVarRule,
    # Performance (3)
    NestedLoopAppendRule,
    StrConcatInLoopRule,
    RepeatedDictLookupRule,
    # Decay (2)
    TodoWithoutTicketRule,
    StubCommentRule,
]

# Stable ordering for deterministic scoring.
RULES.sort(key=lambda r: r.rule_id)


__all__ = [
    "CATEGORY_LABELS",
    "Category",
    "Diagnostic",
    "Rule",
    "RuleContext",
    "Severity",
    "RULES",
]
