"""Real-world false-positive test harness.

Clones a set of popular, well-maintained Python repos (which by assumption
contain ~0 actual AI fingerprints since they predate AI coding tools or are
human-written by domain experts), runs `aidoctor scan` against each, and
reports the unique-rules-tripped count + per-rule occurrence count.

Any rule that fires heavily on these repos is suspect: it's either too loose
or genuinely catching style we shouldn't flag. We use this to set + revisit
severity (warning vs error) per rule.

Run:
    uv run python evals/real_world_fp/run_fp_test.py

Output:
    evals/real_world_fp/REPORT.md   (committed)
    /tmp/aidoctor-fp-cache/<repo>/  (clone cache, gitignored)
"""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

# Pinned to specific tags/commits for reproducibility. Bump when re-running.
TARGETS = [
    {
        "name": "requests",
        "url": "https://github.com/psf/requests.git",
        "commit": "v2.32.3",
        "scan_path": "src/requests",
    },
    {
        "name": "flask",
        "url": "https://github.com/pallets/flask.git",
        "commit": "3.0.3",
        "scan_path": "src/flask",
    },
    {
        "name": "httpx",
        "url": "https://github.com/encode/httpx.git",
        "commit": "0.27.2",
        "scan_path": "httpx",
    },
]

CACHE = Path("/tmp/aidoctor-fp-cache")
REPORT = Path(__file__).parent / "REPORT.md"


def ensure_clone(target: dict) -> Path:
    """Clone the target repo at the pinned commit. Returns the scan path."""
    repo_dir = CACHE / target["name"]
    if not repo_dir.exists():
        print(f"  cloning {target['url']} @ {target['commit']}")
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git", "clone", "--depth", "1",
                "--branch", target["commit"],
                target["url"], str(repo_dir),
            ],
            check=True,
            capture_output=True,
        )
    return repo_dir / target["scan_path"]


def scan(path: Path) -> tuple[int, dict[str, list[dict]]]:
    """Return (files_scanned, findings_by_rule_id)."""
    proc = subprocess.run(
        ["uv", "run", "aidoctor", "scan", str(path), "--jsonl", "--fail-on=none"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    by_rule: dict[str, list[dict]] = defaultdict(list)
    files_scanned = 0
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("type") == "finding":
            by_rule[rec["rule_id"]].append(rec)
        elif rec.get("type") == "summary":
            files_scanned = rec["files_scanned"]
    return files_scanned, dict(by_rule)


def main() -> None:
    lines = [
        "# Real-world false-positive test report\n",
        "Per-rule occurrence count on well-maintained pre-AI Python codebases.",
        "Any rule with >0 hits across these is producing **false positives**",
        "unless we can manually justify each occurrence as a real AI fingerprint.\n",
        "Reproduce: `uv run python evals/real_world_fp/run_fp_test.py`\n",
    ]

    grand_total_by_rule: dict[str, int] = defaultdict(int)
    grand_total_files = 0

    for target in TARGETS:
        print(f"\n=== {target['name']} ({target['commit']}) ===")
        scan_path = ensure_clone(target)
        files_scanned, by_rule = scan(scan_path)
        grand_total_files += files_scanned

        total = sum(len(v) for v in by_rule.values())
        print(f"  {files_scanned} files, {total} findings, {len(by_rule)} unique rules")

        lines.append(f"\n## {target['name']} @ `{target['commit']}`")
        lines.append(
            f"Files scanned: **{files_scanned}** · "
            f"Findings: **{total}** · "
            f"Unique rules: **{len(by_rule)}**\n"
        )
        if not by_rule:
            lines.append("No findings. Clean run.")
            continue
        lines.append("| Rule | Severity | Occurrences |")
        lines.append("|---|---|---|")
        for rid, locs in sorted(by_rule.items(), key=lambda x: -len(x[1])):
            sev = locs[0]["severity"]
            lines.append(f"| `{rid}` | {sev} | {len(locs)} |")
            grand_total_by_rule[rid] += len(locs)

    lines.append("\n## Aggregate across all repos\n")
    lines.append(f"Total files scanned: **{grand_total_files}**\n")
    lines.append("| Rule | Total occurrences across repos |")
    lines.append("|---|---|")
    for rid, count in sorted(grand_total_by_rule.items(), key=lambda x: -x[1]):
        lines.append(f"| `{rid}` | {count} |")

    REPORT.write_text("\n".join(lines) + "\n")
    print(f"\nReport written: {REPORT}")
    print(
        f"Grand total: {sum(grand_total_by_rule.values())} findings "
        f"across {grand_total_files} files"
    )


if __name__ == "__main__":
    main()
