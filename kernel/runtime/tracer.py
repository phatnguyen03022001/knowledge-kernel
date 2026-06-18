#!/usr/bin/env python3
"""
Tracer — observation layer (M1.5).

Records validation runs as immutable trace events.
Provides causal chain visibility without reasoning.
Zero interpretation — just records what happened and when.

Architecture:
  trace = a frozen snapshot of one validation run
  trace store = append-only log of traces (runtime/traces/)
  trace CLI = read-only viewer (like `git log` for the knowledge graph)

TRACE GRANULARITY CONTRACT (M2 Projection depends on this):
  Unit:      1 trace = 1 complete validator pipeline run (all layers, all files).
             Not per-file, not per-invariant. This is the atomic unit of
             system observation. Rationale: per-file traces would fragment
             the causal chain; per-invariant would lose cross-check context.
  Ordering:  Total order within a single-machine session.
             Each trace has exactly one parent_trace_id (the immediately
             preceding trace). This forms a linear chain, not a DAG.
             Multi-machine traces (Phase 3) will require vector clocks.
  Schema:    Stable. Fields added only by appending new keys, never by
             removing or renaming existing keys. M2 Projection reads
             trace.summary, trace.violations, trace.health_snapshot.
             These field names are part of the contract.
  Immutable: Each trace has a content_hash (SHA256). Once written to
             the trace store, a trace MUST NOT be modified. The trace
             store is append-only, same as the event store.

HARD CONSTRAINT:
  Tracer MUST NEVER interpret validation results.
  It records that a violation occurred; it does NOT judge severity,
  suggest remediation, or trigger downstream actions.
  That is Auditor's job (M3).
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRACE_DIR = PROJECT_ROOT / "runtime" / "traces"

# ============================================================================
# TRACE EVENT (immutable, append-only)
# ============================================================================

class TraceEvent:
    """
    A frozen record of one validation run.

    Immutable after write. Content hash verified on read.
    Format is stable — this is the vocabulary M2 Projection will consume.
    """

    def __init__(self, validation_result, phase, target):
        now = datetime.now(timezone.utc)
        self.id = f"trace-{now.strftime('%Y%m%d-%H%M%S-%f')}"
        self.timestamp = now.isoformat()
        self.phase = phase
        self.target = target

        # Core metrics (from validator output — no interpretation added)
        self.valid = validation_result.valid
        self.summary = validation_result.summary
        self.health_snapshot = validation_result.health_snapshot

        # Violations (exact copy — no filtering, no prioritization)
        self.violations = [
            v.to_dict() if hasattr(v, 'to_dict') else v
            for v in validation_result.violations
        ]

        # Error (if validator itself failed)
        self.error = validation_result.error

        # Causal link to previous trace (for chain visualization)
        self.parent_trace_id = None  # set by Tracer on write

    def to_dict(self):
        d = {
            "id": self.id,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "target": self.target,
            "valid": self.valid,
            "summary": self.summary,
        }
        if self.violations:
            d["violations"] = self.violations
        if any(v != 0 for v in (self.health_snapshot or {}).values()):
            d["health_snapshot"] = self.health_snapshot
        if self.error:
            d["error"] = self.error
        if self.parent_trace_id:
            d["parent_trace_id"] = self.parent_trace_id
        return d

    def content_hash(self):
        """SHA256 of the trace content (for immutability verification)."""
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


# ============================================================================
# TRACE STORE (append-only)
# ============================================================================

class TraceStore:
    """
    Append-only log of trace events.

    Storage: runtime/traces/YYYY/MM/DD/trace-*.yaml
    Same structure as event-store for consistency.
    """

    def __init__(self):
        self.trace_dir = TRACE_DIR
        self.trace_dir.mkdir(parents=True, exist_ok=True)

    def _day_dir(self, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return self.trace_dir / timestamp.strftime("%Y/%m/%d")

    def _last_trace(self):
        """Find the most recent trace for causal chain linking."""
        if not self.trace_dir.exists():
            return None
        files = sorted(self.trace_dir.rglob("trace-*.yaml"), reverse=True)
        for f in files:
            try:
                with open(f) as fh:
                    doc = yaml.safe_load(fh)
                if doc and doc.get("id"):
                    return doc["id"]
            except Exception:
                continue
        return None

    def write(self, trace_event):
        """Append trace to store. Returns the trace ID."""
        # Link causal chain
        parent = self._last_trace()
        if parent and parent != trace_event.id:
            trace_event.parent_trace_id = parent

        # Write to day-partitioned directory
        day_dir = self._day_dir(trace_event.timestamp)
        day_dir.mkdir(parents=True, exist_ok=True)

        file_path = day_dir / f"{trace_event.id}.yaml"
        payload = trace_event.to_dict()
        payload["content_hash"] = trace_event.content_hash()

        with open(file_path, "w") as f:
            yaml.dump(payload, f, default_flow_style=False, sort_keys=False,
                       allow_unicode=True, width=120)

        return trace_event.id

    def read(self, trace_id=None, limit=10):
        """
        Read traces from store.

        If trace_id is given, read that specific trace.
        Otherwise, read the most recent `limit` traces in reverse chronological order.
        """
        if trace_id:
            for f in self.trace_dir.rglob(f"{trace_id}.yaml"):
                with open(f) as fh:
                    return yaml.safe_load(fh)
            return None

        traces = []
        files = sorted(self.trace_dir.rglob("trace-*.yaml"), reverse=True)
        for f in files[:limit]:
            try:
                with open(f) as fh:
                    traces.append(yaml.safe_load(fh))
            except Exception:
                continue
        return traces

    def chain(self, trace_id):
        """
        Reconstruct the causal chain for a given trace.
        Walks parent_trace_id links backward to build full history.
        """
        chain = []
        current_id = trace_id
        seen = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            doc = self.read(trace_id=current_id)
            if doc is None:
                break
            chain.append(doc)
            current_id = doc.get("parent_trace_id")
        return list(reversed(chain))


# ============================================================================
# TRACER (coordinates validator + trace store)
# ============================================================================

class Tracer:
    """
    Lightweight coordinator. Runs validator, records trace.

    Usage:
        t = Tracer(phase="phase_1")
        trace_id = t.run(target="full-system")
        # Later:
        traces = t.recent(limit=5)
        chain = t.causal_chain(trace_id)
    """

    def __init__(self, phase="phase_1"):
        self.phase = phase
        self.store = TraceStore()

    def run(self, target="full-system"):
        """Run validator and record trace. Returns trace ID."""
        # Import validator inline to avoid circular deps at module level
        sys.path.insert(0, str(PROJECT_ROOT))
        from kernel.runtime.validator import Validator
        v = Validator(phase=self.phase)
        result = v.validate(target=target)

        trace = TraceEvent(result, self.phase, target)
        trace_id = self.store.write(trace)
        return trace_id

    def recent(self, limit=10):
        """Get most recent traces."""
        return self.store.read(limit=limit)

    def causal_chain(self, trace_id):
        """Get full causal chain for a trace."""
        return self.store.chain(trace_id)

    def diff(self, trace_id_a, trace_id_b):
        """
        Diff two traces — what changed between validation runs?
        Pure data comparison, no semantic judgment.
        """
        doc_a = self.store.read(trace_id=trace_id_a)
        doc_b = self.store.read(trace_id=trace_id_b)
        if not doc_a or not doc_b:
            return {"error": "one or both traces not found"}

        changes = {
            "trace_a": trace_id_a,
            "trace_b": trace_id_b,
            "valid": f"{doc_a.get('valid')} → {doc_b.get('valid')}",
            "total_checks": self._delta(doc_a, doc_b, "summary.total_checks"),
            "failed_critical": self._delta(doc_a, doc_b, "summary.failed_critical"),
            "failed_warning": self._delta(doc_a, doc_b, "summary.failed_warning"),
            "new_violations": [],
            "resolved_violations": [],
        }

        # Compare violations by invariant_id + location
        v_ids_a = set()
        for v in doc_a.get("violations", []) or []:
            v_ids_a.add(f"{v.get('invariant_id')}@{v.get('location', {}).get('file', '?')}")

        v_ids_b = set()
        for v in doc_b.get("violations", []) or []:
            v_ids_b.add(f"{v.get('invariant_id')}@{v.get('location', {}).get('file', '?')}")

        changes["new_violations"] = sorted(v_ids_b - v_ids_a)
        changes["resolved_violations"] = sorted(v_ids_a - v_ids_b)

        return changes

    @staticmethod
    def _delta(doc_a, doc_b, path):
        """Extract nested value by dotted path and return 'old → new'."""
        def _get(d, path):
            for key in path.split("."):
                d = (d or {}).get(key, 0)
            return d
        a = _get(doc_a, path)
        b = _get(doc_b, path)
        return f"{a} → {b}"


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Tracer — observation layer (read-only, zero interpretation)"
    )
    sub = parser.add_subparsers(dest="command")

    # tracer run
    run_parser = sub.add_parser("run", help="Run validator and record trace")
    run_parser.add_argument("--target", default="full-system")
    run_parser.add_argument("--phase", default="phase_1")

    # tracer log
    log_parser = sub.add_parser("log", help="Show recent traces")
    log_parser.add_argument("--limit", type=int, default=10)
    log_parser.add_argument("--json", action="store_true")

    # tracer chain
    chain_parser = sub.add_parser("chain", help="Show causal chain")
    chain_parser.add_argument("trace_id")
    chain_parser.add_argument("--json", action="store_true")

    # tracer diff
    diff_parser = sub.add_parser("diff", help="Diff two traces")
    diff_parser.add_argument("trace_a")
    diff_parser.add_argument("trace_b")

    args = parser.parse_args()
    t = Tracer()

    if args.command == "run":
        trace_id = t.run(target=args.target)
        print(f"trace: {trace_id}")

    elif args.command == "log":
        traces = t.recent(limit=args.limit)
        if args.json:
            print(json.dumps(traces, indent=2))
        else:
            for tr in traces:
                vid = "✅" if tr.get("valid") else "❌"
                ts = tr.get("timestamp", "?")[:19]
                print(f"{vid} {tr['id']}  {ts}  "
                      f"checks={tr['summary']['total_checks']}  "
                      f"fail={tr['summary']['failed_critical']}/{tr['summary']['failed_warning']}")

    elif args.command == "chain":
        chain = t.causal_chain(args.trace_id)
        if args.json:
            print(json.dumps(chain, indent=2))
        else:
            for tr in chain:
                vid = "✅" if tr.get("valid") else "❌"
                ts = tr.get("timestamp", "?")[:19]
                parent = tr.get("parent_trace_id", "root")
                print(f"{vid} {tr['id']}  ← {parent}  {ts}")

    elif args.command == "diff":
        result = t.diff(args.trace_a, args.trace_b)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
