"""Public API surface tests.

These tests pin the contract that workflow skills (/aidoctor:review,
/aidoctor:ship, /aidoctor:deai) rely on. Per the v2.0 CEO plan, the
following are public and covered by SemVer:

    aidoctor.scan_paths
    aidoctor.ScanResult
    ScanResult.score
    ScanResult.to_dict()
    ScanResult.to_json()
"""

from __future__ import annotations

import json
from pathlib import Path


def test_scan_paths_importable_from_top_level() -> None:
    from aidoctor import scan_paths  # noqa: F401


def test_scan_result_importable_from_top_level() -> None:
    from aidoctor import ScanResult  # noqa: F401


def test_scan_paths_returns_scan_result(tmp_path: Path) -> None:
    from aidoctor import ScanResult, scan_paths

    (tmp_path / "x.py").write_text("x = 1\n")
    result = scan_paths([tmp_path], jobs=1)
    assert isinstance(result, ScanResult)


def test_scan_result_has_score_property(tmp_path: Path) -> None:
    from aidoctor import scan_paths
    from aidoctor.score import Score

    (tmp_path / "x.py").write_text('API_KEY = "sk-prod-1234567890abcdef"\n')
    result = scan_paths([tmp_path], jobs=1)
    assert isinstance(result.score, Score)
    assert result.score.unique_error_rules >= 1


def test_scan_result_score_property_caches(tmp_path: Path) -> None:
    """score is computed once per ScanResult — keeps the API consumer-friendly
    even when called repeatedly inside a workflow skill."""
    from aidoctor import scan_paths

    (tmp_path / "x.py").write_text("x = 1\n")
    result = scan_paths([tmp_path], jobs=1)
    assert result.score is result.score


def test_scan_result_to_dict_shape(tmp_path: Path) -> None:
    """to_dict() returns the v1 JSON schema dict — keys workflow skills rely on."""
    from aidoctor import scan_paths

    (tmp_path / "x.py").write_text("x = 1\n")
    result = scan_paths([tmp_path], jobs=1)
    d = result.to_dict()
    assert d["schema_version"] == 1
    assert "score" in d
    assert "value" in d["score"]
    assert "label" in d["score"]
    assert "files_scanned" in d
    assert "files_skipped" in d
    assert "diagnostics" in d
    assert "parse_errors" in d


def test_scan_result_to_json_round_trips(tmp_path: Path) -> None:
    from aidoctor import scan_paths

    (tmp_path / "x.py").write_text('API_KEY = "sk-prod-1234567890abcdef"\n')
    result = scan_paths([tmp_path], jobs=1)
    parsed = json.loads(result.to_json())
    assert parsed == result.to_dict()


def test_semver_pact_in_init_docstring() -> None:
    """__init__.py advertises the public surface + SemVer contract.

    Per CEO/Eng review Section 1C: workflow skills + external users need a
    stability promise before they pin against scan_paths/ScanResult.
    """
    import aidoctor

    doc = (aidoctor.__doc__ or "").lower()
    assert "scan_paths" in doc
    assert "scanresult" in doc
    assert "semver" in doc
