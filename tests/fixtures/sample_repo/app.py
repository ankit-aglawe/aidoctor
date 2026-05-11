"""Sample Python file used as a fixture for end-to-end aidoctor scans."""

import os

# This is a leaked secret. aidoctor should flag this.
API_KEY = "sk-prod-1234567890abcdefghij"

# Annotated form too.
ACCESS_TOKEN: str = "tok_realsecretvaluehere"


def safe_load(name: str) -> str:
    """Loading a value from env. No violation."""
    return os.environ[name]


def placeholder_example() -> str:
    """The placeholder value should NOT be flagged."""
    api_key = "your-api-key-here"
    return api_key
