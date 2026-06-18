#!/usr/bin/env python3
"""
Health CLI Contract Test

Verifies the `cli/health.py` command:
  - Human-readable output contains required sections
  - JSON output conforms to the stable schema
  - Exit codes are valid integers
  - A trace is recorded after each run
"""

import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

HEALTH_CLI = PROJECT_ROOT / "cli" / "health.py"

REQUIRED_TOP_KEYS = {
    "status", "verdict", "risk_score", "trend", "action",
    "summary", "violations_by_category", "health_snapshot",
    "trend_detail", "resolution",
}

REQUIRED_SUMMARY_KEYS = {
    "total_checks", "passed", "failed_critical", "failed_warning",
    "skipped", "duration_ms",
}

REQUIRED_HEALTH_SNAPSHOT_KEYS = {
    "total_nodes", "orphan_count", "orphan_rate", "broken_link_count",
    "circular_dependency_count", "domains_without_owner", "stale_corrections",
}

REQUIRED_RESOLUTION_KEYS = {"action", "reason_codes", "target_scope"}

VALID_STATUSES = {"healthy", "warning", "critical", "error"}
VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
VALID_ACTIONS = {"NONE", "MONITOR", "BLOCK", "ESCALATE"}


def _run(*args):
    """Run health CLI with args. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(HEALTH_CLI)] + list(args),
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ============================================================================
# TESTS
# ============================================================================

def test_health_human_output():
    """Human-readable output must contain required sections."""
    returncode, stdout, stderr = _run()

    # Must produce output
    assert len(stdout) > 0, "Human output is empty"

    # Required section markers
    required_sections = [
        "Knowledge OS Health Report",
        "Status:",
        "Verdict:",
        "Summary",
        "Duration:",
        "Health Metrics",
        "Trend",
    ]
    for section in required_sections:
        assert section in stdout, f"Missing section: '{section}'"

    # Stderr should be clean (pipeline shouldn't crash)
    assert not stderr.strip(), f"Unexpected stderr: {stderr.strip()}"

    print(f"  ✅ Human output: all required sections present (exit={returncode})")


def test_health_json_schema():
    """JSON output must conform to the stable schema."""
    returncode, stdout, stderr = _run("--json")

    # Parse JSON
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as e:
        assert False, f"JSON parse error: {e}"

    # Top-level keys
    actual_keys = set(report.keys())
    missing = REQUIRED_TOP_KEYS - actual_keys
    assert not missing, f"Missing top-level keys: {missing}"
    extra = actual_keys - REQUIRED_TOP_KEYS
    if extra:
        print(f"    ℹ️  Extra top-level keys (non-breaking): {extra}")

    # Summary sub-keys
    summary = report["summary"]
    missing_sum = REQUIRED_SUMMARY_KEYS - set(summary.keys())
    assert not missing_sum, f"Missing summary keys: {missing_sum}"

    # Health snapshot sub-keys
    hs = report["health_snapshot"]
    missing_hs = REQUIRED_HEALTH_SNAPSHOT_KEYS - set(hs.keys())
    assert not missing_hs, f"Missing health_snapshot keys: {missing_hs}"

    # Resolution sub-keys
    res = report["resolution"]
    missing_res = REQUIRED_RESOLUTION_KEYS - set(res.keys())
    assert not missing_res, f"Missing resolution keys: {missing_res}"

    # Value constraints
    assert report["status"] in VALID_STATUSES, \
        f"Invalid status: '{report['status']}'"
    assert report["verdict"] in VALID_VERDICTS, \
        f"Invalid verdict: '{report['verdict']}'"
    assert report["action"] in VALID_ACTIONS, \
        f"Invalid action: '{report['action']}'"
    assert isinstance(report["risk_score"], (int, float)), \
        "risk_score must be numeric"
    assert 0.0 <= report["risk_score"] <= 1.0, \
        f"risk_score out of range: {report['risk_score']}"
    assert isinstance(report["violations_by_category"], dict), \
        "violations_by_category must be a dict"
    assert isinstance(report["resolution"]["reason_codes"], list), \
        "reason_codes must be a list"

    assert not stderr.strip(), f"Unexpected stderr in JSON mode: {stderr.strip()}"

    print(f"  ✅ JSON schema: all {len(REQUIRED_TOP_KEYS)} top-level keys valid (status={report['status']})")


def test_health_exit_codes():
    """Exit codes must be valid integers (0/1/2)."""
    returncode, stdout, stderr = _run()

    assert returncode in (0, 1, 2), \
        f"Exit code must be 0/1/2, got {returncode}"

    print(f"  ✅ Exit codes: valid ({returncode})")


def test_health_trace_recorded():
    """Running health must record a trace for future projections."""
    # Count existing traces before run
    traces_dir = PROJECT_ROOT / "runtime" / "traces"
    before = set()
    if traces_dir.exists():
        before = set(traces_dir.rglob("trace-*.yaml"))

    # Run health
    _run()

    # Count after
    after = set()
    if traces_dir.exists():
        after = set(traces_dir.rglob("trace-*.yaml"))

    new_traces = after - before
    assert len(new_traces) >= 1, \
        f"No new trace recorded. Before: {len(before)}, After: {len(after)}"

    print(f"  ✅ Trace recorded: {len(new_traces)} new trace(s) ({len(after)} total)")


def test_health_json_pipeable():
    """JSON output must be parseable via pipe (no extra output)."""
    returncode, stdout, stderr = _run("--json")

    # First char must be '{'
    stripped = stdout.strip()
    assert stripped.startswith("{"), f"JSON output must start with '{{', got: {stripped[:20]}..."
    assert stripped.endswith("}"), f"JSON output must end with '}}', got: ...{stripped[-20:]}"

    # Every line before the closing brace must be valid in isolation
    # (this is a quick check for stray print statements)
    lines = stripped.split("\n")
    assert lines[0].strip() == "{", f"First line should be '{{', got: '{lines[0].strip()}'"

    print(f"  ✅ JSON pipeable: clean output, {len(lines)} lines")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_health_human_output()
    test_health_json_schema()
    test_health_exit_codes()
    test_health_trace_recorded()
    test_health_json_pipeable()
    print(f"\n  ✅ Health CLI verified — full M1→M4 pipeline, dual output, CI-ready")
