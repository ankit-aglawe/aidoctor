"""Tests for OWASP-3 Python security rules.

These live in rules_complex/security.py via the declarative engine's python
escape hatch (detect.kind = "python"). The rules flag syntactic patterns
where a non-constant argument flows into a dangerous Python builtin or
subprocess.run with shell=True.

v1 caveat (per CEO plan + eng review): syntactic-only, no taint analysis.
Constants are explicitly allowed. FP rate is documented in HONESTY_AUDIT.md.
"""

from __future__ import annotations

from pathlib import Path


def _detector(name: str):
    """Import and return the detector function for `name` from rules_complex."""
    from aidoctor.rules_complex import security
    security.register_all()
    from aidoctor.engine.declarative import _PYTHON_DETECTORS
    return _PYTHON_DETECTORS[name]


def _rule(rule_id: str):
    from aidoctor.engine.declarative import Rule

    return Rule(
        id=rule_id,
        severity="warning",
        confidence="HIGH",
        category="security",
        langs=("python",),
        detect={"kind": "python", "fn": rule_id},
        fix=None,
        ref=None,
        message=f"OWASP: {rule_id}",
        help="Move the non-constant argument out of this dangerous sink.",
    )


# --- shell-true-with-variable ---


def test_shell_true_with_variable_caught(tmp_path: Path) -> None:
    fn = _detector("shell-true-with-variable")
    f = tmp_path / "x.py"
    f.write_text(
        "import subprocess\n"
        "cmd = build_command()\n"
        "subprocess.run(cmd, shell=True)\n"
    )
    diags = fn(_rule("shell-true-with-variable"), f, f.read_text())
    assert len(diags) == 1
    assert diags[0].rule_id == "shell-true-with-variable"
    assert diags[0].line == 3


def test_shell_true_with_constant_string_allowed(tmp_path: Path) -> None:
    """Hardcoded shell commands are syntactically safe; only flag non-constants."""
    fn = _detector("shell-true-with-variable")
    f = tmp_path / "x.py"
    f.write_text(
        "import subprocess\n"
        'subprocess.run("ls -la", shell=True)\n'
    )
    diags = fn(_rule("shell-true-with-variable"), f, f.read_text())
    assert diags == []


def test_shell_false_not_flagged(tmp_path: Path) -> None:
    """No shell=True → no finding regardless of arg shape."""
    fn = _detector("shell-true-with-variable")
    f = tmp_path / "x.py"
    f.write_text("import subprocess\nsubprocess.run(cmd, shell=False)\n")
    diags = fn(_rule("shell-true-with-variable"), f, f.read_text())
    assert diags == []


def test_shell_true_subprocess_check_call_also_flagged(tmp_path: Path) -> None:
    fn = _detector("shell-true-with-variable")
    f = tmp_path / "x.py"
    f.write_text("import subprocess\nsubprocess.check_call(cmd, shell=True)\n")
    diags = fn(_rule("shell-true-with-variable"), f, f.read_text())
    assert len(diags) == 1


# --- pickle-loads-on-non-constant ---


def test_pickle_loads_on_variable_caught(tmp_path: Path) -> None:
    fn = _detector("pickle-loads-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text(
        "import pickle\n"
        "data = request.body\n"
        "user = pickle.loads(data)\n"
    )
    diags = fn(_rule("pickle-loads-on-non-constant"), f, f.read_text())
    assert len(diags) == 1
    assert diags[0].line == 3


def test_pickle_loads_on_constant_bytes_allowed(tmp_path: Path) -> None:
    fn = _detector("pickle-loads-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text(
        "import pickle\n"
        "user = pickle.loads(b'\\x80\\x04\\x95')\n"
    )
    diags = fn(_rule("pickle-loads-on-non-constant"), f, f.read_text())
    assert diags == []


def test_loads_alias_also_caught(tmp_path: Path) -> None:
    """`from pickle import loads; loads(x)` is the same risk."""
    fn = _detector("pickle-loads-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text(
        "from pickle import loads\n"
        "user = loads(payload)\n"
    )
    diags = fn(_rule("pickle-loads-on-non-constant"), f, f.read_text())
    assert len(diags) == 1


# --- eval-or-exec-on-non-constant ---


def test_eval_on_variable_caught(tmp_path: Path) -> None:
    fn = _detector("eval-or-exec-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text("result = eval(user_input)\n")
    diags = fn(_rule("eval-or-exec-on-non-constant"), f, f.read_text())
    assert len(diags) == 1


def test_exec_on_variable_caught(tmp_path: Path) -> None:
    fn = _detector("eval-or-exec-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text("exec(snippet)\n")
    diags = fn(_rule("eval-or-exec-on-non-constant"), f, f.read_text())
    assert len(diags) == 1


def test_eval_on_constant_allowed(tmp_path: Path) -> None:
    """eval('1+1') is silly but syntactically safe."""
    fn = _detector("eval-or-exec-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text('result = eval("1+1")\n')
    diags = fn(_rule("eval-or-exec-on-non-constant"), f, f.read_text())
    assert diags == []


def test_eval_with_no_args_is_safe(tmp_path: Path) -> None:
    """Defensive: eval() with no args is a TypeError at runtime; don't crash on it."""
    fn = _detector("eval-or-exec-on-non-constant")
    f = tmp_path / "x.py"
    f.write_text("eval()\n")
    diags = fn(_rule("eval-or-exec-on-non-constant"), f, f.read_text())
    assert diags == []


# --- integration: OWASP manifest loadable ---


def test_owasp_manifest_loadable() -> None:
    """The shipped owasp.jsonl is well-formed and registers all 3 rules."""
    import aidoctor
    from aidoctor.engine.declarative import load_manifest

    manifest = Path(aidoctor.__file__).parent / "rules" / "manifest" / "owasp.jsonl"
    rules = load_manifest(manifest)
    ids = [r.id for r in rules]
    assert "shell-true-with-variable" in ids
    assert "pickle-loads-on-non-constant" in ids
    assert "eval-or-exec-on-non-constant" in ids
    # All three should be severity=warning at v1 per CEO plan
    for r in rules:
        assert r.severity == "warning", f"{r.id} should be warning at v1"
