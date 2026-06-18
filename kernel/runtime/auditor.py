#!/usr/bin/env python3
"""
M3 Auditor — stateless policy evaluation engine.

Reads normalized diagnostics from M2.1. Applies policy rules.
Produces structured audit reports. Zero ontology creation.

Architecture:
  Diagnostics (M2.1) → Policy Engine → Risk Engine → Trend Engine → Report

HARD CONSTRAINTS:
  ❌ No new categories            ❌ No reclassification
  ❌ No state mutation            ❌ No Arbiter calls
  ❌ No inference / guessing      ❌ No external dependencies

Mental model:
  M2.1 = "what exists in the system"
  M3   = "what does policy say about what exists"
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_DIR = PROJECT_ROOT / "governance" / "policies"


# ============================================================================
# POLICY LOADER (read-only)
# ============================================================================

def load_policies():
    """Load all policy files from governance/policies/."""
    all_policies = []
    if not POLICY_DIR.exists():
        return all_policies
    for pf in sorted(POLICY_DIR.glob("*.yaml")):
        try:
            with open(pf) as f:
                doc = yaml.safe_load(f)
            for p in doc.get("policies", []) or []:
                p["_source"] = pf.name
                all_policies.append(p)
        except Exception:
            continue
    return all_policies


# ============================================================================
# POLICY ENGINE — deterministic rule matching
# ============================================================================

def match_policies(diagnostics, policies):
    """
    Match diagnostics against policy rules.

    Returns: list of policy_hits.
    Each hit: {policy_id, name, type, severity, weight, message, affected_groups}

    ZERO inference — only exact condition matching.
    """
    hits = []
    counts = diagnostics.get("classification", {}).get("counts", {})
    by_category = counts.get("by_category", {})
    groups = diagnostics.get("groups", {}).get("details", {})

    for policy in policies:
        ptype = policy.get("type")
        condition = policy.get("condition", {})

        if ptype == "hard_fail":
            cat = condition.get("category")
            threshold = condition.get("threshold", 0)
            actual = by_category.get(cat, 0)
            if actual > threshold:
                affected = {
                    fp: g for fp, g in groups.items()
                    if g.get("category") == cat
                }
                hits.append({
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "type": "hard_fail",
                    "severity": policy.get("severity", "critical"),
                    "weight": 1.0,
                    "message": policy.get("message", ""),
                    "affected_count": actual,
                    "affected_groups": list(affected.keys()),
                })

        elif ptype == "risk":
            cat = condition.get("category")
            threshold = condition.get("threshold", 0)
            actual = by_category.get(cat, 0)
            if actual > threshold:
                hits.append({
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "type": "risk",
                    "severity": policy.get("severity", "medium"),
                    "weight": policy.get("weight", 0.3),
                    "message": policy.get("message", ""),
                    "affected_count": actual,
                    "affected_groups": [],
                })

        elif ptype == "trend":
            # Trend policies are evaluated by the trend engine (Step 3).
            # They are registered here but matched later with historical data.
            pass

    return hits


# ============================================================================
# RISK ENGINE — deterministic scoring
# ============================================================================

def compute_risk(hits):
    """
    Compute risk_score from policy hits.

    Formula (deterministic):
      risk_score = Σ (hit.severity_weight × 1.0 if critical else ...)
      Clamped to [0.0, 1.0].

    Severity weights (fixed, not configurable):
      critical → 1.0
      high     → 0.6
      medium   → 0.3
      low      → 0.1
    """
    SEVERITY_WEIGHT = {
        "critical": 1.0,
        "high": 0.6,
        "medium": 0.3,
        "low": 0.1,
    }

    if not hits:
        return 0.0

    score = 0.0
    for hit in hits:
        sw = SEVERITY_WEIGHT.get(hit.get("severity", "low"), 0.1)
        score += sw

    # Clamp to [0, 1]
    return min(max(round(score, 2), 0.0), 1.0)


# ============================================================================
# TREND ENGINE — deterministic historical evaluation
# ============================================================================

def evaluate_trends(projection_data, trace_history):
    """
    Evaluate trend policies against historical data.

    Input:
      projection_data: current projection snapshot (from M2)
      trace_history: list of previous trace summaries

    Returns: list of trend policy hits.

    Rules (deterministic, no ML):
      - "increasing" = monotonic increase over window
      - "decreasing" = monotonic decrease over window
      - "stable" = variance < epsilon
      - "persistent" = same group appears in N consecutive runs
    """
    policies = [p for p in load_policies() if p.get("type") == "trend"]
    hits = []

    timeline = projection_data.get("data", {}).get("timeline", [])
    groups = projection_data.get("data", {}).get("current_groups", {})

    for policy in policies:
        condition = policy.get("condition", {})
        metric = condition.get("metric", "")
        direction = condition.get("direction", "")
        window = condition.get("window_runs", 5)
        threshold_runs = condition.get("threshold_runs", 3)

        recent = timeline[-window:] if len(timeline) >= window else timeline

        if metric == "violation_count" and direction == "increasing":
            counts = [r.get("violation_count", 0) for r in recent]
            if len(counts) >= 2 and _is_increasing(counts):
                hits.append({
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "type": "trend",
                    "severity": policy.get("severity", "medium"),
                    "weight": policy.get("weight", 0.3),
                    "message": policy.get("message", ""),
                    "detail": f"counts: {counts}",
                })

        elif metric == "health_orphan_rate" and direction == "increasing":
            rates = [r.get("health", {}).get("orphan_rate", 0) for r in recent if r.get("health")]
            if len(rates) >= 2 and _is_increasing(rates):
                hits.append({
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "type": "trend",
                    "severity": policy.get("severity", "medium"),
                    "weight": policy.get("weight", 0.3),
                    "message": policy.get("message", ""),
                    "detail": f"rates: {rates}",
                })

        elif metric == "broken-reference_persistence":
            # Check if same broken-reference groups persist across runs
            persistent_count = 0
            for tr in trace_history[-threshold_runs:] if len(trace_history) >= threshold_runs else trace_history:
                tr_groups = tr.get("groups", {}).get("details", {}) if isinstance(tr, dict) else {}
                broken_groups = {fp for fp, g in tr_groups.items() if g.get("category") == "broken-reference"}
                current_broken = {fp for fp, g in groups.items() if g.get("category") == "broken-reference"}
                if broken_groups & current_broken:
                    persistent_count += 1
            if persistent_count >= threshold_runs:
                hits.append({
                    "policy_id": policy["id"],
                    "name": policy["name"],
                    "type": "trend",
                    "severity": policy.get("severity", "critical"),
                    "weight": policy.get("weight", 1.0),
                    "message": policy.get("message", ""),
                    "detail": f"persistent for {persistent_count} runs",
                })

    return hits


def _is_increasing(values):
    """Check if values are monotonically increasing (deterministic)."""
    return all(values[i] >= values[i-1] for i in range(1, len(values)))


# ============================================================================
# AUDITOR — orchestrator
# ============================================================================

class Auditor:
    """
    Stateless policy evaluation engine.

    Usage:
        a = Auditor()
        report = a.audit(diagnostics, projection_data, trace_history)
        print(report.verdict)
    """

    def __init__(self):
        self.policies = load_policies()

    def audit(self, diagnostics, projection_data=None, trace_history=None):
        """
        Produce an audit report from diagnostics + policies.

        Args:
          diagnostics: M2.1 output dict (classification + groups + fingerprints)
          projection_data: M2 projection snapshot (optional, for trend eval)
          trace_history: list of previous trace dicts (optional, for persistence)

        Returns: AuditReport
        """
        # Step 1: Match policies
        hits = match_policies(diagnostics, self.policies)

        # Step 2: Evaluate trends (if historical data available)
        if projection_data:
            trend_hits = evaluate_trends(projection_data, trace_history or [])
            hits.extend(trend_hits)

        # Step 3: Compute risk
        risk_score = compute_risk(hits)

        # Step 4: Determine verdict
        hard_fails = [h for h in hits if h["type"] == "hard_fail"]
        if hard_fails:
            verdict = "FAIL"
        elif risk_score >= 0.7:
            verdict = "WARN"
        elif risk_score >= 0.3:
            verdict = "WARN"
        else:
            verdict = "PASS"

        # Step 5: Trend assessment
        trend = self._assess_trend(projection_data)

        return AuditReport(
            verdict=verdict,
            risk_score=risk_score,
            trend=trend,
            policy_hits=hits,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _assess_trend(projection_data):
        """Determine trend direction from projection timeline (deterministic)."""
        if not projection_data:
            return "unknown"
        timeline = projection_data.get("data", {}).get("timeline", [])
        if len(timeline) < 2:
            return "stable"

        recent = timeline[-5:]
        violations = [r.get("violation_count", 0) for r in recent]
        if len(violations) >= 2:
            if _is_increasing(violations) and violations[-1] > violations[0]:
                return "degrading"
            if all(v <= violations[0] for v in violations[1:]) and violations[-1] < violations[0]:
                return "improving"
        return "stable"


# ============================================================================
# AUDIT REPORT (immutable output)
# ============================================================================

class AuditReport:
    """Immutable audit output. Serializes to JSON/YAML."""

    __slots__ = ("audit_id", "timestamp", "verdict", "risk_score", "trend",
                 "policy_hits", "summary", "content_hash")

    def __init__(self, verdict, risk_score, trend, policy_hits, diagnostics):
        self.audit_id = f"audit-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}"
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.verdict = verdict
        self.risk_score = risk_score
        self.trend = trend
        self.policy_hits = policy_hits

        # Summary (derived — no new facts created)
        fail_hits = [h for h in policy_hits if h["type"] == "hard_fail"]
        risk_hits = [h for h in policy_hits if h["type"] == "risk"]
        trend_hits = [h for h in policy_hits if h["type"] == "trend"]

        # Count affected categories (categories with count > 0)
        cat_counts = (diagnostics or {}).get("classification", {}).get("counts", {}).get("by_category", {})
        affected_cats = {cat for cat, count in cat_counts.items() if count > 0}

        self.summary = {
            "total_policy_hits": len(policy_hits),
            "hard_fails": len(fail_hits),
            "risk_flags": len(risk_hits),
            "trend_alerts": len(trend_hits),
            "categories_affected": len(affected_cats),
        }

        # Content hash for immutability verification
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        self.content_hash = hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "trend": self.trend,
            "summary": self.summary,
            "policy_hits": [
                {
                    "policy_id": h["policy_id"],
                    "name": h["name"],
                    "type": h["type"],
                    "severity": h["severity"],
                    "message": h["message"],
                    "affected_count": h.get("affected_count", 0),
                }
                for h in self.policy_hits
            ],
        }


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="M3 Auditor — stateless policy evaluation engine"
    )
    parser.add_argument("--input", help="Path to JSON file with M2.1 diagnostics output")
    parser.add_argument("--projection", help="Path to M2 projection YAML (for trend eval)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--stdin", action="store_true", help="Read diagnostics from stdin")
    args = parser.parse_args()

    # Load diagnostics
    diagnostics = {}
    if args.stdin:
        diagnostics = json.loads(sys.stdin.read())
    elif args.input:
        with open(args.input) as f:
            diagnostics = json.load(f)
    else:
        # Demo: run full pipeline and audit
        sys.path.insert(0, str(PROJECT_ROOT))
        from kernel.runtime.validator import Validator
        from kernel.runtime.diagnostics import DiagnosticEngine
        from kernel.runtime.projection import ProjectionBuilder

        v = Validator()
        result = v.validate()
        de = DiagnosticEngine()
        diag = de.process([v.to_dict() for v in result.violations])
        pb = ProjectionBuilder()
        pb.build()
        proj = pb.read("validation-timeline")

        diagnostics = diag

    # Load projection (optional)
    projection_data = None
    if args.projection:
        with open(args.projection) as f:
            projection_data = yaml.safe_load(f)
    elif not args.stdin and not args.input:
        # In demo mode, try to read existing projection
        pb2 = ProjectionBuilder()
        projection_data = pb2.read("validation-timeline")

    a = Auditor()
    report = a.audit(diagnostics, projection_data)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"verdict:    {report.verdict}")
        print(f"risk_score: {report.risk_score}")
        print(f"trend:      {report.trend}")
        print(f"policy hits: {report.summary['total_policy_hits']} "
              f"(FAIL={report.summary['hard_fails']}, "
              f"RISK={report.summary['risk_flags']}, "
              f"TREND={report.summary['trend_alerts']})")
        print(f"audit_id:   {report.audit_id}")
        if report.policy_hits:
            print(f"\n  hits:")
            for h in report.policy_hits:
                print(f"  [{h['type'].upper()}] {h['policy_id']}: {h['message']}")

    sys.exit(0 if report.verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
