#!/usr/bin/env python3
"""
M4 Arbiter — minimal deterministic action router.

Maps M3 audit verdicts to resolution actions.
Does NOT judge. Does NOT interpret. Does NOT resolve disputes.

Architecture:
  M3 Audit Report → Rule Table → Action Mapping → Resolution Event

Mental model:
  M1 = detects violations     M3 = judges according to policy
  M2 = shows structure        M4 = routes consequence (THIS)
  M2.1 = normalizes           M4 is NOT "final judge" — it's "action switchboard"

HARD CONSTRAINTS (non-negotiable):
  ❌ No semantic interpretation        ❌ No category creation
  ❌ No policy evaluation (M3's job)    ❌ No mutation of upstream data
  ❌ No "smart decisions" — if Arbiter starts reasoning, it's broken by design
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESOLUTION_DIR = PROJECT_ROOT / "runtime" / "resolutions"


# ============================================================================
# RULE TABLE — deterministic lookup (no inference)
# ============================================================================

def resolve_action(verdict, risk_score, policy_hits):
    """
    Deterministic action mapping.

    Rules (priority order):
      R1: PASS                    → NONE
      R2: WARN                    → MONITOR
      R3: FAIL + critical_hits>0  → BLOCK
      R4: FAIL otherwise          → ESCALATE
      R5: risk_score >= 0.8       → ESCALATE (override upward only)

    Returns: (action, reason_codes)
    """
    critical_hits = sum(1 for h in policy_hits if h.get("severity") == "critical")
    reason_codes = []

    if verdict == "PASS":
        return "NONE", []

    if verdict == "WARN":
        reason_codes.append("WARN_VERDICT")
        if risk_score >= 0.8:
            return "ESCALATE", reason_codes + ["HIGH_RISK"]
        return "MONITOR", reason_codes

    if verdict == "FAIL":
        if critical_hits > 0:
            reason_codes.append("CRITICAL_FAILURES")
            reason_codes.append(f"CRITICAL_COUNT={critical_hits}")
            return "BLOCK", reason_codes
        else:
            reason_codes.append("FAIL_NO_CRITICAL")
            return "ESCALATE", reason_codes

    # Fallback (should never reach here with valid M3 input)
    return "MONITOR", ["UNKNOWN_VERDICT"]


def determine_scope(action, policy_hits):
    """
    Determine target scope from policy hits.

    Rules (deterministic):
      - BLOCK with system-level categories → "system"
      - BLOCK with file-level categories   → "node"
      - others                             → "run"
    """
    if action == "BLOCK":
        system_categories = {"tampered-event", "broken-causality"}
        hit_categories = {h.get("policy_id", "") for h in policy_hits}
        # Check affected categories from policy hit IDs
        if any("tampered" in h.get("policy_id", "") or "causality" in h.get("policy_id", "")
               for h in policy_hits):
            return "system"
        return "node"
    return "run"


# ============================================================================
# RESOLUTION EVENT (immutable, append-only)
# ============================================================================

class ResolutionEvent:
    """Immutable record of an Arbiter action."""

    __slots__ = ("resolution_id", "timestamp", "action", "reason_codes",
                 "target_scope", "source_audit_id", "source_verdict",
                 "source_risk_score", "content_hash")

    def __init__(self, action, reason_codes, target_scope,
                 audit_report):
        now = datetime.now(timezone.utc)
        self.resolution_id = f"res-{now.strftime('%Y%m%d-%H%M%S-%f')}"
        self.timestamp = now.isoformat()
        self.action = action
        self.reason_codes = reason_codes
        self.target_scope = target_scope
        self.source_audit_id = audit_report.audit_id if hasattr(audit_report, 'audit_id') else audit_report.get("audit_id", "unknown")
        self.source_verdict = audit_report.verdict if hasattr(audit_report, 'verdict') else audit_report.get("verdict", "unknown")
        self.source_risk_score = audit_report.risk_score if hasattr(audit_report, 'risk_score') else audit_report.get("risk_score", 0)

        # Content hash for immutability (computed last)
        self.content_hash = None
        self.content_hash = self._compute_hash()

    def _compute_hash(self):
        payload = json.dumps({
            "resolution_id": self.resolution_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "reason_codes": self.reason_codes,
            "target_scope": self.target_scope,
            "source_audit_id": self.source_audit_id,
            "source_verdict": self.source_verdict,
            "source_risk_score": self.source_risk_score,
            "immutable": True,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self):
        return {
            "resolution_id": self.resolution_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "reason_codes": self.reason_codes,
            "target_scope": self.target_scope,
            "source_audit_id": self.source_audit_id,
            "source_verdict": self.source_verdict,
            "source_risk_score": self.source_risk_score,
            "immutable": True,
            "content_hash": self.content_hash or self._compute_hash(),
        }


# ============================================================================
# ARBITER — minimal router
# ============================================================================

class Arbiter:
    """
    Minimal deterministic action router.

    Usage:
        arb = Arbiter()
        resolution = arb.route(audit_report)
        arb.emit(resolution)
    """

    def __init__(self):
        RESOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    def route(self, audit_report):
        """
        Route M3 verdict → resolution action.

        Pure function. Same input → same action. Always.
        """
        # Extract fields (handle both AuditReport objects and dicts)
        verdict = audit_report.verdict if hasattr(audit_report, 'verdict') else audit_report.get("verdict", "PASS")
        risk_score = audit_report.risk_score if hasattr(audit_report, 'risk_score') else audit_report.get("risk_score", 0.0)
        policy_hits = audit_report.policy_hits if hasattr(audit_report, 'policy_hits') else audit_report.get("policy_hits", [])

        action, reason_codes = resolve_action(verdict, risk_score, policy_hits)
        scope = determine_scope(action, policy_hits)

        return ResolutionEvent(action, reason_codes, scope, audit_report)

    def emit(self, resolution):
        """
        Write resolution event to store (append-only, immutable).

        Returns: resolution_id
        """
        day_dir = RESOLUTION_DIR / datetime.now(timezone.utc).strftime("%Y/%m/%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        file_path = day_dir / f"{resolution.resolution_id}.yaml"
        with open(file_path, "w") as f:
            yaml.dump(resolution.to_dict(), f, default_flow_style=False,
                       sort_keys=False, allow_unicode=True, width=120)

        return resolution.resolution_id

    def emit_to_event_store(self, resolution):
        """
        Write resolution as escalation.resolved event to event store.

        Uses emit_event() from acp_runner which handles:
        - UUID generation for event ID
        - ISO8601 timestamp
        - Canonical event envelope format
        - Sequential file naming
        - Directory creation and file locking

        This is the architecturally required path for event bus
        integration per ADR-004. The existing emit() to
        runtime/resolutions/ continues to work (dual-write
        during migration period).

        Returns: event dict (with generated id)
        """
        from acp_runner import emit_event

        return emit_event(
            event_type="escalation.resolved",
            payload=resolution.to_dict(),
            correlation_id=resolution.source_audit_id,
            source_component="arbiter",
            source_entity_type="m4",
            source_entity_id="arbiter",
        )

    def recent(self, limit=10):
        """Read recent resolution events (read-only)."""
        events = []
        if RESOLUTION_DIR.exists():
            files = sorted(RESOLUTION_DIR.rglob("res-*.yaml"), reverse=True)
            for f in files[:limit]:
                try:
                    with open(f) as fh:
                        events.append(yaml.safe_load(fh))
                except Exception:
                    continue
        return events


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="M4 Arbiter — minimal deterministic action router"
    )
    sub = parser.add_subparsers(dest="command")

    # arbiter route
    route_parser = sub.add_parser("route", help="Route M3 verdict → action")
    route_parser.add_argument("--verdict", default="PASS", choices=["PASS", "WARN", "FAIL"])
    route_parser.add_argument("--risk", type=float, default=0.0)
    route_parser.add_argument("--critical-hits", type=int, default=0)

    # arbiter log
    sub.add_parser("log", help="Show recent resolutions")

    args = parser.parse_args()
    arb = Arbiter()

    if args.command == "route":
        policy_hits = [
            {"severity": "critical", "policy_id": "FAIL-001"}
        ] * args.critical_hits
        # Simulate audit report as dict
        audit = type('obj', (object,), {
            'audit_id': 'demo',
            'verdict': args.verdict,
            'risk_score': args.risk,
            'policy_hits': policy_hits,
        })()
        resolution = arb.route(audit)
        arb.emit(resolution)
        print(f"action:  {resolution.action}")
        print(f"scope:   {resolution.target_scope}")
        print(f"reasons: {resolution.reason_codes}")
        print(f"res_id:  {resolution.resolution_id}")

    elif args.command == "log":
        events = arb.recent(limit=10)
        for ev in events:
            print(f"{ev.get('action', '?'):10s}  {ev.get('timestamp','?')[:19]}  "
                  f"scope={ev.get('target_scope','?')}  "
                  f"verdict={ev.get('source_verdict','?')}  "
                  f"risk={ev.get('source_risk_score','?')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
