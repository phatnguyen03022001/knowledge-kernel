#!/usr/bin/env python3
"""
Knowledge OS Health Check — M1→M4 full pipeline in one command.

Usage:
    python3 cli/health.py              # human-readable health report
    python3 cli/health.py --json       # JSON output (for CI)

Exit codes:
    0 = healthy  (PASS, all clear)
    1 = warning  (WARN, non-critical issues exist)
    2 = critical (FAIL, must fix)
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kernel.runtime.validator import Validator
from kernel.runtime.diagnostics import DiagnosticEngine
from kernel.runtime.projection import ProjectionBuilder
from kernel.runtime.auditor import Auditor
from kernel.runtime.arbiter import Arbiter
from kernel.runtime.tracer import TraceEvent, TraceStore

# ============================================================================
# Constants
# ============================================================================

STATUS_ICONS = {
    "healthy":  "✅",  # ✅
    "warning":  "⚠️",  # ⚠️
    "critical": "❌",  # ❌
    "error":    "❌",  # ❌
}

STATUS_LABELS = {
    "healthy":  "HEALTHY",
    "warning":  "WARNING",
    "critical": "CRITICAL",
    "error":    "ERROR",
}

MAX_VIOLATIONS_PER_CATEGORY = 20


# ============================================================================
# Pipeline
# ============================================================================

def run_pipeline():
    """
    Execute full M1→M4 pipeline.

    Returns a dict with all layer outputs. Never raises — errors are
    captured and returned as status: "error".
    """
    t0 = time.time()

    try:
        # ---- M1: Validator ----
        v = Validator(phase="phase_1")
        result = v.validate(target="full-system")

        if result.error:
            return _error_result(
                "VALIDATOR_FAILED",
                f"{result.error.get('code', 'UNKNOWN')}: {result.error.get('message', '')}",
                t0,
            )

        # Record trace (append-only — enables future projection/trend)
        trace = TraceEvent(result, "phase_1", "full-system")
        TraceStore().write(trace)

        # ---- M2.1: Diagnostics ----
        violation_dicts = [
            vrec.to_dict() if hasattr(vrec, 'to_dict') else vrec
            for vrec in result.violations
        ]
        de = DiagnosticEngine()
        diagnostics = de.process(violation_dicts)

        # ---- M2.0: Projection ----
        pb = ProjectionBuilder()
        proj_result = pb.build(view_name="validation-timeline", limit=100)
        projection_data = proj_result.to_dict() if proj_result else None

        # Read recent traces for trend evaluation
        trace_history = TraceStore().read(limit=10)

        # ---- M3: Auditor ----
        auditor = Auditor()
        audit_report = auditor.audit(
            diagnostics=diagnostics,
            projection_data=projection_data,
            trace_history=trace_history,
        )

        # ---- M4: Arbiter ----
        arbiter = Arbiter()
        resolution = arbiter.route(audit_report)

        duration_ms = int((time.time() - t0) * 1000)

        # Derive composite status
        verdict = audit_report.verdict
        action = resolution.action
        if verdict == "FAIL":
            status = "critical"
        elif verdict == "WARN":
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "error": None,
            "validation": {
                "valid": result.valid,
                "summary": dict(result.summary),
                "health_snapshot": dict(result.health_snapshot) if result.health_snapshot else {},
                "violations": violation_dicts,
            },
            "diagnostics": diagnostics,
            "projection": projection_data,
            "trace_history_ids": [
                t.get("id", "") if isinstance(t, dict) else getattr(t, "id", "")
                for t in trace_history
            ],
            "audit": audit_report.to_dict(),
            "resolution": resolution.to_dict(),
            "pipeline_duration_ms": duration_ms,
        }

    except Exception as e:
        return _error_result("PIPELINE_CRASH", str(e), t0)


def _error_result(code, message, t0):
    """Build error result dict."""
    return {
        "status": "error",
        "error": {"code": code, "message": str(message)},
        "validation": {
            "valid": False,
            "summary": {},
            "health_snapshot": {},
            "violations": [],
        },
        "diagnostics": {},
        "projection": None,
        "trace_history_ids": [],
        "audit": {"verdict": "FAIL", "risk_score": 1.0, "trend": "unknown"},
        "resolution": {"action": "ESCALATE", "reason_codes": [code], "target_scope": "system"},
        "pipeline_duration_ms": int((time.time() - t0) * 1000),
    }


# ============================================================================
# Report composition
# ============================================================================

def compose_health_report(pipe):
    """
    Transform raw pipeline output into the stable health report schema.

    This is the JSON output format — guaranteed stable for CI integration.
    """
    audit = pipe.get("audit", {})
    resolution = pipe.get("resolution", {})
    val = pipe.get("validation", {})
    diag = pipe.get("diagnostics", {})

    # Build violations_by_category from diagnostics classification
    violations_by_category = {}
    classification = diag.get("classification", {})
    by_cat = classification.get("by_category", {})
    for cat, diags in by_cat.items():
        violations_by_category[cat] = []
        for d in diags:
            violations_by_category[cat].append({
                "file": d.get("location_file", ""),
                "field": d.get("location_field", ""),
                "expected": d.get("expected", ""),
                "actual": d.get("actual", ""),
            })

    # Trend detail from projection
    trend_detail = None
    if pipe.get("projection"):
        pdata = pipe["projection"].get("data", {})
        trend_detail = pdata.get("trend")

    summary = val.get("summary", {})
    return {
        "status": pipe.get("status", "error"),
        "verdict": audit.get("verdict", "PASS"),
        "risk_score": audit.get("risk_score", 0.0),
        "trend": audit.get("trend", "unknown"),
        "action": resolution.get("action", "NONE"),
        "summary": {
            "total_checks": summary.get("total_checks", 0),
            "passed": summary.get("passed", 0),
            "failed_critical": summary.get("failed_critical", 0),
            "failed_warning": summary.get("failed_warning", 0),
            "skipped": summary.get("skipped", 0),
            "duration_ms": pipe.get("pipeline_duration_ms", 0),
        },
        "violations_by_category": violations_by_category,
        "health_snapshot": {
            "total_nodes": val.get("health_snapshot", {}).get("total_nodes", 0),
            "orphan_count": val.get("health_snapshot", {}).get("orphan_count", 0),
            "orphan_rate": val.get("health_snapshot", {}).get("orphan_rate", 0.0),
            "broken_link_count": val.get("health_snapshot", {}).get("broken_link_count", 0),
            "circular_dependency_count": val.get("health_snapshot", {}).get("circular_dependency_count", 0),
            "domains_without_owner": val.get("health_snapshot", {}).get("domains_without_owner", 0),
            "stale_corrections": val.get("health_snapshot", {}).get("stale_corrections", 0),
        },
        "trend_detail": trend_detail,
        "resolution": {
            "action": resolution.get("action", "NONE"),
            "reason_codes": resolution.get("reason_codes", []),
            "target_scope": resolution.get("target_scope", "run"),
        },
    }


# ============================================================================
# Output formatters
# ============================================================================

def format_human(report):
    """Format health report as readable terminal output."""
    lines = []
    app = lines.append

    status = report["status"]
    icon = STATUS_ICONS.get(status, "?")
    label = STATUS_LABELS.get(status, status.upper())

    app("")
    app("  Knowledge OS Health Report")
    app("  ==========================")
    app("")
    app(f"  Status:      {icon} {label}")
    app(f"  Verdict:     {report['verdict']}")
    app(f"  Risk Score:  {report['risk_score']:.2f} / 1.00")
    app(f"  Trend:       {report['trend']}")
    app(f"  Action:      {report['action']}")

    # Summary
    s = report["summary"]
    app("")
    app("  ── Summary " + "─" * 35)
    app(f"  Checks run:     {s['total_checks']}")
    app(f"  Passed:         {s['passed']}")
    app(f"  Critical:       {s['failed_critical']}")
    app(f"  Warnings:       {s['failed_warning']}")
    app(f"  Skipped:        {s['skipped']}")
    app(f"  Duration:       {s['duration_ms']}ms")

    # Warnings (violations by category)
    violations = report["violations_by_category"]
    if violations:
        app("")
        app("  ── Warnings " + "─" * 33)
        for cat, items in sorted(violations.items()):
            count = len(items)
            app(f"  {cat} ({count}):")
            for item in items[:MAX_VIOLATIONS_PER_CATEGORY]:
                file_name = item.get("file", "?")
                field = item.get("field", "")
                expected = item.get("expected", "")
                actual = item.get("actual", "")
                detail = f"{file_name}"
                if field:
                    detail += f" [{field}]"
                if expected and actual:
                    detail += f" (expected={expected}, actual={actual})"
                elif actual:
                    detail += f" ({actual})"
                app(f"    • {detail}")
            if count > MAX_VIOLATIONS_PER_CATEGORY:
                app(f"    ... and {count - MAX_VIOLATIONS_PER_CATEGORY} more")

    # Health metrics
    hs = report["health_snapshot"]
    if hs:
        app("")
        app("  ── Health Metrics " + "─" * 26)
        app(f"  Total nodes:            {hs['total_nodes']}")
        app(f"  Orphan rate:            {hs['orphan_rate']:.1%}")
        app(f"  Broken links:           {hs['broken_link_count']}")
        app(f"  Circular deps:          {hs['circular_dependency_count']}")
        app(f"  Domains w/o owner:      {hs['domains_without_owner']}")
        app(f"  Stale corrections:      {hs['stale_corrections']}")

    # Trend
    trend = report["trend_detail"]
    app("")
    app("  ── Trend (last 5 runs) " + "─" * 21)
    if trend:
        app(f"  Health:      {trend.get('health', 'unknown')}")
        app(f"  Violations:  {trend.get('violations', 'unknown')}")
        app(f"  Critical:    {trend.get('critical', 'unknown')}")
    else:
        app("  No historical data — first run")

    # Resolution
    res = report["resolution"]
    if res.get("reason_codes"):
        app("")
        app(f"  Resolution:  {res['action']} ({', '.join(res['reason_codes'])})")

    app("")
    return "\n".join(lines)


def format_json(report):
    """Format health report as indented JSON."""
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


# ============================================================================
# Exit code
# ============================================================================

def determine_exit_code(verdict, action):
    """
    Map M3 verdict + M4 action to CI exit code.

    0 = healthy   (PASS)
    1 = warning   (WARN or MONITOR)
    2 = critical  (FAIL, BLOCK, ESCALATE)
    """
    if verdict == "FAIL":
        return 2
    if verdict == "WARN":
        return 1
    # PASS (or unexpected verdict)
    if action in ("BLOCK", "ESCALATE"):
        return 2
    if action == "MONITOR":
        return 1
    return 0


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Knowledge OS Health Check — run full M1→M4 pipeline"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for CI integration)",
    )
    args = parser.parse_args()

    pipe = run_pipeline()
    report = compose_health_report(pipe)

    if args.json:
        print(format_json(report))
    else:
        print(format_human(report))

    sys.exit(determine_exit_code(
        report["verdict"],
        report["action"],
    ))


if __name__ == "__main__":
    main()
