"""Scan a GitHub PR by URL.

Usage:
    aidoctor scan-pr https://github.com/owner/repo/pull/123

Fetches the PR's changed files via the GitHub REST API, downloads each .py file
at the PR's head SHA, and scans them. Auth via GITHUB_TOKEN env var when set
(required for private repos and to avoid 60/hour anonymous rate limit).
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from aidoctor.scan import ScanResult, scan_file

logger = logging.getLogger(__name__)

PR_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+)/pull/(?P<num>\d+)/?$"
)

GITHUB_API = "https://api.github.com"
USER_AGENT = "aidoctor (https://github.com/ankit-aglawe/aidoctor)"


class ScanPrError(Exception):
    """Base error for scan-pr operations."""


class BadPrUrlError(ScanPrError):
    """The provided URL is not a valid GitHub PR URL."""


class GitHubNotFoundError(ScanPrError):
    """The PR (or repo) is not found, or is private and no GITHUB_TOKEN was set."""


class GitHubRateLimitError(ScanPrError):
    """We hit GitHub's rate limit."""


class GitHubNetworkError(ScanPrError):
    """Network failure talking to GitHub."""


@dataclass(slots=True, frozen=True)
class ParsedPr:
    owner: str
    repo: str
    number: int


def parse_url(url: str) -> ParsedPr:
    """Parse a GitHub PR URL into its parts. Raises BadPrUrlError on invalid input."""
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise BadPrUrlError(
            f"Not a valid GitHub PR URL: {url!r}. "
            f"Expected: https://github.com/<owner>/<repo>/pull/<num>"
        )
    return ParsedPr(
        owner=match.group("owner"),
        repo=match.group("repo"),
        number=int(match.group("num")),
    )


def _auth_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_get(client: httpx.Client, url: str, *, retries: int = 2) -> httpx.Response:
    """GET a URL with single-backoff retry on 429 and 2x retry on network errors.

    Raises GitHubRateLimitError / GitHubNotFoundError / GitHubNetworkError as appropriate.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = client.get(url, follow_redirects=True)
        except httpx.HTTPError as e:
            last_exc = e
            logger.debug("network error on %s (attempt %d): %s", url, attempt + 1, e)
            continue
        if response.status_code == 404:
            raise GitHubNotFoundError(
                f"GitHub returned 404 for {url}. "
                f"The PR may be private (set GITHUB_TOKEN) or the URL is wrong."
            )
        if response.status_code == 429 or (
            response.status_code == 403 and "rate limit" in response.text.lower()
        ):
            if attempt < retries:
                logger.debug("rate limited, retrying once")
                continue
            raise GitHubRateLimitError(
                f"GitHub rate limited. "
                f"Set GITHUB_TOKEN (https://github.com/settings/tokens) to raise the limit."
            )
        if response.status_code >= 400:
            raise GitHubNetworkError(
                f"GitHub returned {response.status_code} for {url}: {response.text[:200]}"
            )
        return response
    raise GitHubNetworkError(f"network error talking to {url}: {last_exc}")


def fetch_pr_files(pr: ParsedPr, client: httpx.Client | None = None) -> list[dict]:
    """Fetch the list of files changed in a PR. Returns the raw GitHub API response items."""
    own_client = client is None
    if own_client:
        client = httpx.Client(headers=_auth_headers(), timeout=15.0)
    try:
        url = f"{GITHUB_API}/repos/{pr.owner}/{pr.repo}/pulls/{pr.number}/files"
        files: list[dict] = []
        page = 1
        while True:
            paged = f"{url}?per_page=100&page={page}"
            resp = _http_get(client, paged)
            batch = resp.json()
            if not batch:
                break
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            if page > 10:  # safety cap
                logger.warning("PR has more than 1000 changed files; truncating")
                break
        return files
    finally:
        if own_client:
            client.close()


def fetch_pr_head_sha(pr: ParsedPr, client: httpx.Client | None = None) -> str:
    """Fetch the head SHA of the PR's head branch."""
    own_client = client is None
    if own_client:
        client = httpx.Client(headers=_auth_headers(), timeout=15.0)
    try:
        url = f"{GITHUB_API}/repos/{pr.owner}/{pr.repo}/pulls/{pr.number}"
        resp = _http_get(client, url)
        return resp.json()["head"]["sha"]
    finally:
        if own_client:
            client.close()


def fetch_raw_file(
    pr: ParsedPr, path: str, sha: str, client: httpx.Client | None = None
) -> str:
    """Fetch a single file's full source at the given commit SHA via raw.githubusercontent.com."""
    own_client = client is None
    if own_client:
        client = httpx.Client(headers=_auth_headers(), timeout=15.0)
    try:
        url = f"https://raw.githubusercontent.com/{pr.owner}/{pr.repo}/{sha}/{path}"
        resp = _http_get(client, url)
        return resp.text
    finally:
        if own_client:
            client.close()


def scan_pr(url: str) -> ScanResult:
    """Scan a GitHub PR URL. Returns a ScanResult covering only the changed .py files."""
    pr = parse_url(url)
    with httpx.Client(headers=_auth_headers(), timeout=15.0) as client:
        sha = fetch_pr_head_sha(pr, client=client)
        files = fetch_pr_files(pr, client=client)
        py_files = [
            f for f in files if f.get("filename", "").endswith(".py") and f.get("status") != "removed"
        ]

        result = ScanResult()
        with tempfile.TemporaryDirectory(prefix="aidoctor-pr-") as tmpdir:
            tmp_root = Path(tmpdir)
            for f in py_files:
                rel = f["filename"]
                try:
                    source = fetch_raw_file(pr, rel, sha, client=client)
                except ScanPrError as e:
                    result.parse_errors.append((Path(rel), str(e)))
                    result.files_skipped += 1
                    continue
                local = tmp_root / rel
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_text(source, encoding="utf-8")
                diagnostics, parse_err = scan_file(local)
                if parse_err is not None:
                    result.parse_errors.append((local, parse_err))
                    result.files_skipped += 1
                    continue
                # Rebind diagnostics' file to the repo-relative path for display.
                rebound = [
                    type(d)(
                        rule_id=d.rule_id,
                        severity=d.severity,
                        category=d.category,
                        file=Path(rel),
                        line=d.line,
                        column=d.column,
                        message=d.message,
                        help=d.help,
                        url=d.url,
                        suppression_hint=d.suppression_hint,
                    )
                    for d in diagnostics
                ]
                result.diagnostics.extend(rebound)
                result.files_scanned += 1
    return result


def cli_run(url: str, json_output: bool, fail_on: str) -> int:
    """Entry point for `aidoctor scan-pr URL`. Returns exit code."""
    import json as _json

    import click
    from rich.console import Console

    from aidoctor.render import render_terminal
    from aidoctor.scan import build_json_payload, compute_exit_code
    from aidoctor.score import compute_score

    try:
        result = scan_pr(url)
    except ScanPrError as e:
        click.echo(f"aidoctor: {e}", err=True)
        return 3

    score = compute_score(result.diagnostics)

    if json_output:
        click.echo(_json.dumps(build_json_payload(result, score), indent=2))
    else:
        render_terminal(result, score, console=Console())

    return compute_exit_code(score, fail_on)
