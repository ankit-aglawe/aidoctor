"""Hardcoded secrets rules.

Catches obvious secret literals in source: API keys, tokens, AWS creds, JWT-shaped strings.
"""

# aidoctor: disable-file=stub-comment,hardcoded-api-key

from __future__ import annotations

import re

import libcst as cst

from aidoctor.rules._base import Category, Rule, Severity

# Names that strongly suggest a secret. Case-insensitive substring match.
SECRET_NAME_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|access[_-]?key|private[_-]?key|auth[_-]?token)",
    re.IGNORECASE,
)

# Minimum string length to flag (avoids flagging empty/placeholder strings).
MIN_SECRET_LEN = 12

# Common placeholder values that aren't real secrets.
PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "todo",
        "fixme",
        "your-api-key-here",
        "your_api_key_here",
        "xxx",
        "xxxx",
        "...",
        "changeme",
        "change-me",
        "change_me",
        "test",
        "example",
    }
)


class HardcodedApiKeyRule(Rule):
    """Detects assignment of long string literals to API_KEY / SECRET / TOKEN-named variables."""

    rule_id = "hardcoded-api-key"
    severity = Severity.ERROR
    category = Category.SECRETS
    message = "Hardcoded secret in source. Move to environment variable or secret manager."
    help = (
        "Variables named API_KEY, SECRET, TOKEN, PASSWORD (or similar) with long string "
        "values are almost always real secrets that leaked into source. Move them to "
        "environment variables (`os.environ['API_KEY']`) or a secret manager. "
        "If this is a test fixture or placeholder, rename the variable or shorten the value."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#hardcoded-api-key"

    def visit_Assign(self, node: cst.Assign) -> None:
        # We care about simple `NAME = "value"` patterns.
        if not isinstance(node.value, cst.SimpleString):
            return
        value = node.value.evaluated_value
        if value is None or not isinstance(value, str):
            return
        if len(value) < MIN_SECRET_LEN:
            return
        if value.lower() in PLACEHOLDER_VALUES:
            return
        for target in node.targets:
            if not isinstance(target.target, cst.Name):
                continue
            name = target.target.value
            if SECRET_NAME_PATTERN.search(name):
                self.report(target.target)
                break

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        # Annotated form: `API_KEY: str = "sk-..."`.
        if node.value is None or not isinstance(node.value, cst.SimpleString):
            return
        value = node.value.evaluated_value
        if value is None or not isinstance(value, str):
            return
        if len(value) < MIN_SECRET_LEN:
            return
        if value.lower() in PLACEHOLDER_VALUES:
            return
        if not isinstance(node.target, cst.Name):
            return
        if SECRET_NAME_PATTERN.search(node.target.value):
            self.report(node.target)


# AWS Access Key ID pattern: AKIA + 16 base32 chars.
AWS_ACCESS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")

# JWT: three dot-separated base64url segments. We match conservatively: header.payload.signature.
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")


class AwsCredentialsRule(Rule):
    """Detects AWS access key IDs (AKIA / ASIA prefixed) in string literals anywhere in source."""

    rule_id = "aws-credentials"
    severity = Severity.ERROR
    category = Category.SECRETS
    message = "AWS access key in source. Rotate the key immediately and move to env or IAM role."
    help = (
        "AWS access key IDs starting with AKIA (long-term) or ASIA (temporary STS) are "
        "credentials. Once committed, treat them as compromised: rotate the key in IAM, "
        "remove from history (git filter-branch / BFG), and migrate to IAM roles or "
        "secrets manager. Never use hardcoded AWS creds in application code."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#aws-credentials"

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        value = node.evaluated_value
        if value is None or not isinstance(value, str):
            return
        if AWS_ACCESS_KEY_RE.search(value):
            self.report(node)


class JwtTokenRule(Rule):
    """Detects JWT-shaped string literals (three dot-separated base64url segments)."""

    rule_id = "jwt-token"
    severity = Severity.ERROR
    category = Category.SECRETS
    message = "JWT-shaped string in source. Move to environment variable or refresh flow."
    help = (
        "Strings matching `eyJ...eyJ...XXX` are almost always JWT tokens. These usually "
        "expire but the embedded claims may still leak user identity, roles, or "
        "permissions. Move to environment variables or use a refresh flow. If this is "
        "a test fixture, mark with `# aidoctor: disable=jwt-token`."
    )
    url = "https://github.com/ankit-aglawe/aidoctor#jwt-token"

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        value = node.evaluated_value
        if value is None or not isinstance(value, str):
            return
        if JWT_RE.search(value):
            self.report(node)
