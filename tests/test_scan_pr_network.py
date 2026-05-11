"""Tests for scan_pr networking paths via mocked httpx.

We patch httpx.Client to avoid real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from aidoctor.scan_pr import (
    GitHubNetworkError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    ParsedPr,
    fetch_pr_files,
    fetch_pr_head_sha,
    fetch_raw_file,
    parse_url,
)


def _mock_response(status_code: int, payload=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or (json.dumps(payload) if payload is not None else "")
    resp.json = MagicMock(return_value=payload if payload is not None else {})
    return resp


def test_fetch_pr_head_sha_returns_sha() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(200, payload={"head": {"sha": "abc123"}})
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        sha = fetch_pr_head_sha(pr)
    assert sha == "abc123"


def test_fetch_pr_files_paginates() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    # Two pages: 100 then 5 items.
    page1 = [{"filename": f"f{i}.py", "status": "modified"} for i in range(100)]
    page2 = [{"filename": f"g{i}.py", "status": "modified"} for i in range(5)]

    responses = [_mock_response(200, payload=page1), _mock_response(200, payload=page2)]
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.side_effect = responses
        files = fetch_pr_files(pr)
    assert len(files) == 105


def test_fetch_raw_file_returns_text() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(200, text="x = 1\n")
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        source = fetch_raw_file(pr, "x.py", "abc123")
    assert source == "x = 1\n"


def test_fetch_pr_head_sha_404_raises_not_found() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(404, text="not found")
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        with pytest.raises(GitHubNotFoundError):
            fetch_pr_head_sha(pr)


def test_fetch_pr_head_sha_429_raises_rate_limit() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(429, text="rate limit exceeded")
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        with pytest.raises(GitHubRateLimitError):
            fetch_pr_head_sha(pr)


def test_fetch_pr_head_sha_403_with_rate_limit_text_raises_rate_limit() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(403, text="API rate limit exceeded for ...")
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        with pytest.raises(GitHubRateLimitError):
            fetch_pr_head_sha(pr)


def test_fetch_pr_head_sha_5xx_raises_network_error() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    response = _mock_response(503, text="service unavailable")
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.return_value = response
        with pytest.raises(GitHubNetworkError):
            fetch_pr_head_sha(pr)


def test_fetch_pr_head_sha_connection_error_retries_then_raises() -> None:
    pr = ParsedPr(owner="o", repo="r", number=1)
    with patch("httpx.Client") as MockClient:
        client = MockClient.return_value
        client.get.side_effect = httpx.ConnectError("boom")
        with pytest.raises(GitHubNetworkError):
            fetch_pr_head_sha(pr)


def test_parse_url_examples() -> None:
    pr = parse_url("https://github.com/octocat/Hello-World/pull/1347")
    assert pr.owner == "octocat"
    assert pr.repo == "Hello-World"
    assert pr.number == 1347
