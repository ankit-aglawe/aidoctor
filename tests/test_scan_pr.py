"""Tests for scan_pr URL parsing + error mapping. Network paths are mocked."""

from __future__ import annotations

import pytest

from aidoctor.scan_pr import BadPrUrlError, ParsedPr, parse_url


def test_parse_url_happy_path() -> None:
    pr = parse_url("https://github.com/ankit-aglawe/aidoctor/pull/123")
    assert pr == ParsedPr(owner="ankit-aglawe", repo="aidoctor", number=123)


def test_parse_url_trailing_slash() -> None:
    pr = parse_url("https://github.com/ankit-aglawe/aidoctor/pull/123/")
    assert pr.number == 123


def test_parse_url_with_dotted_org() -> None:
    pr = parse_url("https://github.com/my.org/my-repo/pull/9")
    assert pr.owner == "my.org"
    assert pr.repo == "my-repo"


@pytest.mark.parametrize(
    "bad",
    [
        "https://github.com/ankit-aglawe/aidoctor",  # missing /pull/N
        "https://gitlab.com/foo/bar/pull/1",  # wrong host
        "http://example.com",
        "not a url at all",
        "https://github.com/ankit-aglawe/aidoctor/pull/abc",  # non-numeric PR
        "",
    ],
)
def test_parse_url_rejects_bad_input(bad: str) -> None:
    with pytest.raises(BadPrUrlError):
        parse_url(bad)
