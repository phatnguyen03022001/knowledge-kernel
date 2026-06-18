#!/usr/bin/env python3
"""
Projection — deterministic view compiler (M2.0 Minimal Core).

Builds read-only materialized views from immutable trace + event data.
Does NOT interpret. Does NOT reason. Does NOT modify source data.

Architecture:
  Trace Store + Event Store → Projection Builder → View Files
  Views are derived, not authoritative. Event Store is canonical.
  Any view can be rebuilt from scratch (Full Replay).

M2.0 scope (minimal — 1 view):
  validation-timeline: chronological list of validation outcomes
    with health score trend and violation counts.

M2.1 scope (future — multi-view):
  - dependency-graph: SSOT link topology
  - ownership-graph: domain → concept mapping
  - failure-heatmap: violation frequency by invariant type

HARD CONSTRAINT:
  Projection MUST NEVER interpret violation severity or suggest actions.
  It compiles data from traces; Auditor (M3) interprets meaning.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRACE_DIR = PROJECT_ROOT / "runtime" / "traces"
EVENT_STORE_DIR = PROJECT_ROOT / "runtime" / "event-store"
PROJECTION_DIR = PROJECT_ROOT / "runtime" / "projections"
SNAPSHOT_DIR = PROJECT_ROOT / "runtime" / "snapshots"


# ============================================================================
# PROJECTION RESULT
# ============================================================================

class ProjectionResult:
    """Output of a projection build — never modifies source data."""
    __slots__ = ("view_name", "data", "source_traces", "built_at", "content_hash")

    def __init__(self, view_name, data, source_trace_ids):
        self.view_name = view_name
        self.data = data
        self.source_traces = source_trace_ids
        self.built_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "view": self.view_name,
            "built_at": self.built_at,
            "source_traces": self.source_traces,
            "data": self.data,
        }


# ============================================================================
# VIEW BUILDERS (one per view — pure functions, no side effects)
# ============================================================================

def build_validation_timeline(traces):
    """
    M2.0 view: validation outcome timeline.

    Input:  list of trace dicts (from TraceStore.read)
    Output: chronological timeline with trend data

    Pure function — same input → same output. Always.
    """
    timeline = []
    health_trend = []
    violation_trend = []
    critical_trend = []

    for tr in traces:
        summary = tr.get("summary", {})
        health = tr.get("health_snapshot", {})

        entry = {
            "trace_id": tr.get("id"),
            "timestamp": tr.get("timestamp"),
            "valid": tr.get("valid"),
            "total_checks": summary.get("total_checks", 0),
            "failed_critical": summary.get("failed_critical", 0),
            "failed_warning": summary.get("failed_warning", 0),
            "duration_ms": summary.get("duration_ms", 0),
            "violation_count": len(tr.get("violations", []) or []),
        }

        # Health metrics (if present)
        if health:
            entry["health"] = {
                "total_nodes": health.get("total_nodes", 0),
                "orphan_count": health.get("orphan_count", 0),
                "orphan_rate": health.get("orphan_rate", 0.0),
                "broken_link_count": health.get("broken_link_count", 0),
                "circular_dependency_count": health.get("circular_dependency_count", 0),
                "domains_without_owner": health.get("domains_without_owner", 0),
                "stale_corrections": health.get("stale_corrections", 0),
            }

        timeline.append(entry)
        health_trend.append(health.get("orphan_rate", 0) if health else None)
        violation_trend.append(entry["violation_count"])
        critical_trend.append(entry["failed_critical"])

    # Trend summary (last 5 data points)
    def trend(values):
        clean = [v for v in values if v is not None]
        if len(clean) < 2:
            return "stable"
        recent = clean[-5:] if len(clean) >= 5 else clean
        if all(v == 0 for v in recent):
            return "clean"
        if recent[-1] > recent[0]:
            return "degrading"
        if recent[-1] < recent[0]:
            return "improving"
        return "stable"

    return {
        "timeline": timeline,
        "total_runs": len(timeline),
        "current_valid": timeline[-1]["valid"] if timeline else None,
        "trend": {
            "health": trend(health_trend),
            "violations": trend(violation_trend),
            "critical": trend(critical_trend),
        },
        "last_run": timeline[-1]["timestamp"] if timeline else None,
    }


# ============================================================================
# PROJECTION BUILDER
# ============================================================================

class ProjectionBuilder:
    """
    Builds read-only views from trace + event data.

    Usage:
        pb = ProjectionBuilder()
        result = pb.build("validation-timeline", limit=50)
        pb.write(result)
    """

    def __init__(self):
        self.projection_dir = PROJECTION_DIR
        self.projection_dir.mkdir(parents=True, exist_ok=True)

    def _load_traces(self, limit=100):
        """Load traces from trace store in chronological order."""
        traces = []
        if TRACE_DIR.exists():
            files = sorted(TRACE_DIR.rglob("trace-*.yaml"))
            for f in files[-limit:]:
                try:
                    with open(f) as fh:
                        doc = yaml.safe_load(fh)
                    if doc:
                        traces.append(doc)
                except Exception:
                    continue
        return traces

    def _load_events(self, limit=100):
        """Load events from event store."""
        events = []
        if EVENT_STORE_DIR.exists():
            files = sorted(EVENT_STORE_DIR.rglob("evt-*.yaml"))
            for f in files[-limit:]:
                try:
                    with open(f) as fh:
                        doc = yaml.safe_load(fh)
                    if doc:
                        events.append(doc)
                except Exception:
                    continue
        return events

    def build(self, view_name="validation-timeline", limit=100):
        """
        Build a projection view.

        view_name: which view to build (M2.0: only "validation-timeline")
        limit: max number of source traces to include
        """
        traces = self._load_traces(limit=limit)
        source_ids = [t.get("id") for t in traces if t.get("id")]

        if view_name == "validation-timeline":
            data = build_validation_timeline(traces)
        else:
            return None  # unknown view — M2.1 will add more

        return ProjectionResult(view_name, data, source_ids)

    def write(self, result):
        """Write projection to disk. Does NOT modify source data."""
        file_path = self.projection_dir / f"{result.view_name}.yaml"
        with open(file_path, "w") as f:
            yaml.dump(result.to_dict(), f, default_flow_style=False,
                       sort_keys=False, allow_unicode=True, width=120)
        return str(file_path)

    def read(self, view_name):
        """Read a previously built projection."""
        file_path = self.projection_dir / f"{view_name}.yaml"
        if not file_path.exists():
            return None
        with open(file_path) as f:
            return yaml.safe_load(f)

    # ── SNAPSHOT ─────────────────────────────────────────────────────

    def snapshot(self):
        """
        Take a snapshot of current projections.
        Policy: snapshot every 100 events OR every 24h (whichever comes first).
        V1: manual trigger via CLI.
        """
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        for view_file in self.projection_dir.glob("*.yaml"):
            with open(view_file) as f:
                data = yaml.safe_load(f)
            snap_path = SNAPSHOT_DIR / f"{view_file.stem}-{timestamp}.yaml"
            with open(snap_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False,
                           sort_keys=False, allow_unicode=True, width=120)

        return f"snapshot-{timestamp}"

    def full_replay(self):
        """
        Rebuild ALL projections from scratch (Full Replay).
        Reads all traces and events, recomputes every view.
        Use when: projection missing, schema upgrade, corruption detected.
        """
        results = {}
        for view_name in ["validation-timeline"]:  # M2.1: add more views
            result = self.build(view_name=view_name, limit=0)  # 0 = all traces
            if result:
                self.write(result)
                results[view_name] = "rebuilt"
        return results


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Projection — deterministic view compiler"
    )
    sub = parser.add_subparsers(dest="command")

    # projection build
    build_parser = sub.add_parser("build", help="Build a projection view")
    build_parser.add_argument("--view", default="validation-timeline")
    build_parser.add_argument("--limit", type=int, default=100)

    # projection show
    show_parser = sub.add_parser("show", help="Show a projection view")
    show_parser.add_argument("--view", default="validation-timeline")
    show_parser.add_argument("--json", action="store_true")

    # projection replay
    sub.add_parser("replay", help="Full replay — rebuild all views from scratch")

    # projection snapshot
    sub.add_parser("snapshot", help="Snapshot current projections")

    args = parser.parse_args()
    pb = ProjectionBuilder()

    if args.command == "build":
        result = pb.build(view_name=args.view, limit=args.limit)
        if result is None:
            print(f"Unknown view: {args.view}")
            sys.exit(1)
        path = pb.write(result)
        print(f"built: {args.view} → {path}")
        print(f"traces: {len(result.source_traces)}")
        print(f"valid:  {result.data.get('current_valid')}")
        print(f"trend:  {result.data.get('trend', {})}")

    elif args.command == "show":
        data = pb.read(args.view)
        if data is None:
            print(f"No projection found: {args.view}. Run 'build' first.")
            sys.exit(1)
        if args.json:
            print(json.dumps(data, indent=2, default=str))
        else:
            view_data = data.get("data", {})
            print(f"view:  {data.get('view')}")
            print(f"built: {data.get('built_at')}")
            print(f"runs:  {view_data.get('total_runs', 0)}")
            print(f"valid: {view_data.get('current_valid')}")
            print(f"trend: {view_data.get('trend', {})}")
            timeline = view_data.get("timeline", [])
            if timeline:
                print(f"\nlast 5 runs:")
                for entry in timeline[-5:]:
                    vid = "✅" if entry.get("valid") else "❌"
                    print(f"  {vid} {entry['trace_id'][:30]}...  "
                          f"fail={entry['failed_critical']}/{entry['failed_warning']}  "
                          f"health={entry.get('health', {}).get('orphan_rate', '?')}")

    elif args.command == "replay":
        results = pb.full_replay()
        print(f"replay complete: {results}")

    elif args.command == "snapshot":
        snap_id = pb.snapshot()
        print(f"snapshot: {snap_id}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
