#!/usr/bin/env python3
"""
Validator — deterministic constraint engine (physics layer).

Reads invariants from kernel/foundation/validator-invariants.yaml.
Checks structural, governance, event, and graph invariants.
Returns pass/fail + violations + health snapshot.

HARD CONSTRAINTS (never violated by this code):
  - Never calls Arbiter or simulates Arbiter logic
  - Never resolves ownership disputes
  - Never decides semantic correctness
  - Never modifies system state (read-only)

Architecture: layered pipeline, strict short-circuiting.
  Layer 1 fail → immediate REJECT (no further checks needed).
  Layer 2 fail → accumulate WARNING, continue.
  Layer 3 fail → FLAG, continue.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import yaml


# ============================================================================
# PATH RESOLUTION
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INVARIANTS_PATH = PROJECT_ROOT / "kernel" / "foundation" / "validator-invariants.yaml"
CONTRACT_PATH   = PROJECT_ROOT / "kernel" / "foundation" / "validator-contract.yaml"
REGISTRY_PATH   = PROJECT_ROOT / "kernel" / "foundation" / "concept-registry.yaml"
EVENT_STORE_DIR = PROJECT_ROOT / "runtime" / "event-store"
SSOT_DIR        = PROJECT_ROOT / "knowledge" / "ssot"
LEARNING_DIR    = PROJECT_ROOT / "knowledge" / "learning-model"
SCHEMAS_DIR     = PROJECT_ROOT / "knowledge" / "schemas"
RESEARCH_DIR    = PROJECT_ROOT / "knowledge" / "research"
CORRECTIONS_DIR = PROJECT_ROOT / "governance" / "corrections"


# ============================================================================
# RESULT TYPES (output-only, no side effects)
# ============================================================================

class Violation:
    __slots__ = ("invariant_id", "invariant_name", "severity", "layer",
                 "location_file", "location_field", "expected", "actual",
                 "recovery_auto", "recovery_action", "failure_mode_ref",
                 "timestamp")

    def __init__(self, invariant_id, invariant_name, severity, layer,
                 location_file=None, location_field=None,
                 expected=None, actual=None,
                 recovery_auto=False, recovery_action=None,
                 failure_mode_ref=None):
        self.invariant_id = invariant_id
        self.invariant_name = invariant_name
        self.severity = severity
        self.layer = layer
        self.location_file = location_file
        self.location_field = location_field
        self.expected = expected
        self.actual = actual
        self.recovery_auto = recovery_auto
        self.recovery_action = recovery_action
        self.failure_mode_ref = failure_mode_ref
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        d = {
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "severity": self.severity,
            "layer": self.layer,
            "timestamp": self.timestamp,
        }
        if self.location_file:
            d["location"] = {"file": self.location_file}
            if self.location_field:
                d["location"]["field"] = self.location_field
            if self.expected is not None:
                d["location"]["expected"] = self.expected
            if self.actual is not None:
                d["location"]["actual"] = self.actual
        d["recovery"] = {
            "auto_recoverable": self.recovery_auto,
            "suggested_action": self.recovery_action or "manual review required",
        }
        if self.failure_mode_ref:
            d["recovery"]["failure_mode_ref"] = self.failure_mode_ref
        return d


class ValidationResult:
    __slots__ = ("valid", "violations", "summary", "health_snapshot", "error")

    def __init__(self):
        self.valid = True
        self.violations = []
        self.summary = {
            "total_checks": 0,
            "passed": 0,
            "failed_critical": 0,
            "failed_warning": 0,
            "skipped": 0,
            "duration_ms": 0,
        }
        self.health_snapshot = {
            "total_nodes": 0,
            "orphan_count": 0,
            "orphan_rate": 0.0,
            "broken_link_count": 0,
            "circular_dependency_count": 0,
            "domains_without_owner": 0,
            "stale_corrections": 0,
        }
        self.error = None

    def to_dict(self):
        d = {
            "valid": self.valid,
            "summary": self.summary,
        }
        if self.violations:
            d["violations"] = [v.to_dict() for v in self.violations]
        if any(v != 0 for v in self.health_snapshot.values()):
            d["health_snapshot"] = self.health_snapshot
        if self.error:
            d["error"] = self.error
        return d


# ============================================================================
# VALIDATOR CORE
# ============================================================================

class Validator:
    """
    Deterministic constraint engine.

    Usage:
        v = Validator(phase="phase_1")
        result = v.validate(target="full-system")
        print(json.dumps(result.to_dict(), indent=2))
    """

    def __init__(self, phase="phase_1"):
        self.phase = phase
        self._invariants = None
        self._registry = None
        self._ssot_files = {}
        self._event_files = {}
        self._correction_files = {}

    # ── LOAD (read-only) ─────────────────────────────────────────────

    def _load_invariants(self):
        if self._invariants is None:
            with open(INVARIANTS_PATH) as f:
                self._invariants = yaml.safe_load(f)
        return self._invariants

    def _load_registry(self):
        if self._registry is None:
            if REGISTRY_PATH.exists():
                with open(REGISTRY_PATH) as f:
                    self._registry = yaml.safe_load(f)
            else:
                self._registry = {"concepts": {}}
        return self._registry

    def _load_file(self, path):
        """Read a file and return (raw_text, frontmatter_dict, body_text)."""
        try:
            with open(path) as f:
                raw = f.read()
        except Exception:
            return None, None, None

        fm = {}
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm = {}
                body = parts[2]
        return raw, fm, body

    # ── LAYER 1: STRUCTURAL INVARIANTS ────────────────────────────────

    def _check_S_INV_001_no_broken_references(self, result):
        """S-INV-001: Every link/source target must exist."""
        inv = self._get_invariant("S-INV-001")
        for file_path, (_, fm, _) in self._ssot_files.items():
            for link_list_name in ["links", "sources"]:
                links = fm.get(link_list_name, []) or []
                for i, target in enumerate(links):
                    result.summary["total_checks"] += 1
                    target_path = PROJECT_ROOT / target
                    if not target_path.exists():
                        result.valid = False
                        result.summary["failed_critical"] += 1
                        result.summary["broken_link_count"] += 1
                        result.violations.append(Violation(
                            invariant_id="S-INV-001",
                            invariant_name=inv["name"],
                            severity="critical",
                            layer=1,
                            location_file=str(file_path.relative_to(PROJECT_ROOT)),
                            location_field=f"{link_list_name}[{i}]",
                            expected=f"{target} (exists)",
                            actual=f"{target} (missing)",
                            recovery_auto=False,
                            recovery_action=f"Update {link_list_name}[{i}] to existing file or create {target}",
                            failure_mode_ref="FM-validator-001",
                        ))
                    else:
                        result.summary["passed"] += 1

    def _check_S_INV_002_frontmatter_completeness(self, result):
        """S-INV-002: Every SSOT must have required frontmatter fields."""
        inv = self._get_invariant("S-INV-002")
        required = ["status", "last-reviewed", "review-by", "sources",
                     "links", "owner", "primary-domain", "version"]
        for file_path, (_, fm, _) in self._ssot_files.items():
            for field in required:
                result.summary["total_checks"] += 1
                if field not in fm or fm[field] is None:
                    result.valid = False
                    result.summary["failed_critical"] += 1
                    result.violations.append(Violation(
                        invariant_id="S-INV-002",
                        invariant_name=inv["name"],
                        severity="critical",
                        layer=1,
                        location_file=str(file_path.relative_to(PROJECT_ROOT)),
                        location_field=field,
                        expected="present and non-null",
                        actual="missing or null",
                        recovery_auto=True,
                        recovery_action=f"Add '{field}' to frontmatter",
                        failure_mode_ref="FM-validator-002",
                    ))
                else:
                    result.summary["passed"] += 1

    def _check_S_INV_003_schema_compliance(self, result):
        """S-INV-003: YAML files must match declared schema."""
        inv = self._get_invariant("S-INV-003")
        yaml_dirs = [
            PROJECT_ROOT / "kernel",
            PROJECT_ROOT / "governance",
            EVENT_STORE_DIR,
        ]
        for ydir in yaml_dirs:
            if not ydir.exists():
                continue
            for yf in ydir.rglob("*.yaml"):
                result.summary["total_checks"] += 1
                try:
                    with open(yf) as f:
                        yaml.safe_load(f)
                    result.summary["passed"] += 1
                except yaml.YAMLError as e:
                    result.valid = False
                    result.summary["failed_critical"] += 1
                    result.violations.append(Violation(
                        invariant_id="S-INV-003",
                        invariant_name=inv["name"],
                        severity="critical",
                        layer=1,
                        location_file=str(yf.relative_to(PROJECT_ROOT)),
                        expected="valid YAML",
                        actual=f"parse error: {e}",
                        recovery_auto=False,
                        recovery_action="Fix YAML syntax",
                    ))

    # ── LAYER 1: GOVERNANCE INVARIANTS ────────────────────────────────

    def _check_G_INV_001_every_domain_has_owner(self, result):
        """G-INV-001: Every domain must have an owner."""
        if self.phase == "phase_0":
            result.summary["skipped"] += 1
            return
        inv = self._get_invariant("G-INV-001")
        registry = self._load_registry()
        concepts = registry.get("concepts", {})
        domains_seen = set()
        for concept_name, entry in concepts.items():
            primary = entry.get("primary-domain")
            if primary:
                domains_seen.add(primary)
            for sd in entry.get("secondary-domains", []) or []:
                domains_seen.add(sd)
        for domain in domains_seen:
            result.summary["total_checks"] += 1
            has_owner = False
            for concept_name, entry in concepts.items():
                if entry.get("primary-domain") == domain:
                    if entry.get("owner"):
                        has_owner = True
                        break
            if not has_owner:
                result.summary["domains_without_owner"] += 1
                result.valid = False
                result.summary["failed_critical"] += 1
                result.violations.append(Violation(
                    invariant_id="G-INV-001",
                    invariant_name=inv["name"],
                    severity="critical",
                    layer=1,
                    location_field=f"domain: {domain}",
                    expected="has owner",
                    actual="no owner",
                    recovery_auto=True,
                    recovery_action="Trigger domain-assignment workflow",
                    failure_mode_ref="FM-validator-003",
                ))
            else:
                result.summary["passed"] += 1

    def _check_G_INV_002_one_concept_one_owner(self, result):
        """G-INV-002: Each concept has exactly one canonical owner."""
        inv = self._get_invariant("G-INV-002")
        registry = self._load_registry()
        concepts = registry.get("concepts", {})
        paths_seen = {}
        for concept_name, entry in concepts.items():
            result.summary["total_checks"] += 1
            owner_path = entry.get("owner")
            if not owner_path:
                result.valid = False
                result.summary["failed_critical"] += 1
                result.violations.append(Violation(
                    invariant_id="G-INV-002",
                    invariant_name=inv["name"],
                    severity="critical",
                    layer=1,
                    location_field=f"concept: {concept_name}",
                    expected="non-null owner",
                    actual="null or missing owner",
                    recovery_auto=False,
                    failure_mode_ref="FM-validator-004",
                ))
                continue
            if owner_path in paths_seen:
                result.valid = False
                result.summary["failed_critical"] += 1
                result.violations.append(Violation(
                    invariant_id="G-INV-002",
                    invariant_name=inv["name"],
                    severity="critical",
                    layer=1,
                    location_field=f"concept: {concept_name}",
                    expected=f"unique owner (not {paths_seen[owner_path]})",
                    actual=f"duplicate owner path: {owner_path}",
                    recovery_auto=False,
                    recovery_action="Domain owner or Arbiter resolves via L3 correction",
                    failure_mode_ref="FM-validator-004",
                ))
            else:
                paths_seen[owner_path] = concept_name
                result.summary["passed"] += 1

    # ── LAYER 1: EVENT INTEGRITY ─────────────────────────────────────

    def _check_E_INV_001_event_immutability(self, result):
        """E-INV-001: Event content hashes match."""
        inv = self._get_invariant("E-INV-001")
        for file_path, event_doc in self._event_files.items():
            result.summary["total_checks"] += 1
            stored_hash = event_doc.get("content_hash")
            if not stored_hash:
                result.summary["skipped"] += 1
                continue
            with open(file_path) as f:
                raw = f.read()
            computed = hashlib.sha256(raw.encode()).hexdigest()
            if stored_hash != computed:
                result.valid = False
                result.summary["failed_critical"] += 1
                result.violations.append(Violation(
                    invariant_id="E-INV-001",
                    invariant_name=inv["name"],
                    severity="critical",
                    layer=1,
                    location_file=str(file_path.relative_to(PROJECT_ROOT)),
                    expected=stored_hash,
                    actual=computed,
                    recovery_auto=False,
                    recovery_action="Restore event from git or snapshot",
                    failure_mode_ref="FM-validator-005",
                ))
            else:
                result.summary["passed"] += 1

    def _check_E_INV_002_event_causality_chain(self, result):
        """E-INV-002: Every causation_id must reference an existing event."""
        inv = self._get_invariant("E-INV-002")
        event_ids = set()
        for _, event_doc in self._event_files.items():
            eid = event_doc.get("id")
            if eid:
                event_ids.add(eid)
        for file_path, event_doc in self._event_files.items():
            causation = event_doc.get("metadata", {}).get("causation_id")
            if causation is None:
                result.summary["skipped"] += 1
                continue
            result.summary["total_checks"] += 1
            if causation not in event_ids:
                result.valid = False
                result.summary["failed_critical"] += 1
                result.violations.append(Violation(
                    invariant_id="E-INV-002",
                    invariant_name=inv["name"],
                    severity="critical",
                    layer=1,
                    location_file=str(file_path.relative_to(PROJECT_ROOT)),
                    location_field="metadata.causation_id",
                    expected=f"existing event ID",
                    actual=f"{causation} (not found)",
                    recovery_auto=False,
                    recovery_action="Fix causation_id or remove event",
                ))
            else:
                result.summary["passed"] += 1

    # ── LAYER 2: HEALTH METRICS ──────────────────────────────────────

    def _check_GH_MET_001_unreferenced_nodes(self, result):
        """GH-MET-001: Unreferenced node rate < 10%."""
        inv = self._get_invariant("GH-MET-001")
        all_nodes = set(self._ssot_files.keys())
        referenced = set()
        for _, (_, fm, _) in self._ssot_files.items():
            for link in fm.get("links", []) or []:
                target_path = PROJECT_ROOT / link
                if target_path in all_nodes:
                    referenced.add(target_path)
        total = len(all_nodes)
        unreferenced = total - len(referenced)
        rate = unreferenced / total if total > 0 else 0.0

        result.summary["total_checks"] += 1
        result.health_snapshot["total_nodes"] = total
        result.health_snapshot["orphan_count"] = unreferenced
        result.health_snapshot["orphan_rate"] = round(rate, 2)

        if rate > 0.10:
            result.summary["failed_warning"] += 1
            result.violations.append(Violation(
                invariant_id="GH-MET-001",
                invariant_name=inv["name"],
                severity="warning",
                layer=2,
                expected="orphan_rate <= 0.10",
                actual=f"orphan_rate = {rate:.2f} ({unreferenced}/{total})",
                recovery_action="Review unreferenced nodes — may be abandoned or newly created",
            ))
        else:
            result.summary["passed"] += 1

    def _check_GH_MET_002_no_circular_dependency(self, result):
        """GH-MET-002: SSOT dependency graph must be a DAG."""
        inv = self._get_invariant("GH-MET-002")
        adjacency = {}
        for file_path, (_, fm, _) in self._ssot_files.items():
            adjacency[file_path] = []
            for link in fm.get("links", []) or []:
                target = (PROJECT_ROOT / link).resolve()
                if target in self._ssot_files:
                    adjacency[file_path].append(target)

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in adjacency}
        cycle_found = None

        def dfs(node, path):
            nonlocal cycle_found
            color[node] = GRAY
            for neighbor in adjacency.get(node, []):
                if color.get(neighbor) == GRAY:
                    cycle_found = path + [neighbor]
                    return True
                if color.get(neighbor) == WHITE:
                    if dfs(neighbor, path + [neighbor]):
                        return True
            color[node] = BLACK
            return False

        for node in adjacency:
            if color[node] == WHITE:
                if dfs(node, [node]):
                    break

        result.summary["total_checks"] += 1
        if cycle_found:
            result.valid = False
            result.summary["failed_critical"] += 1
            result.summary["circular_dependency_count"] += 1
            cycle_str = " → ".join(str(p.relative_to(PROJECT_ROOT)) for p in cycle_found)
            result.violations.append(Violation(
                invariant_id="GH-MET-002",
                invariant_name=inv["name"],
                severity="critical",
                layer=2,
                expected="DAG (no cycles)",
                actual=f"cycle: {cycle_str}",
                recovery_auto=False,
                recovery_action="Break cycle by removing one link",
                failure_mode_ref="FM-validator-006",
            ))
        else:
            result.summary["passed"] += 1

    def _check_GH_MET_003_event_ordering_monotonic(self, result):
        """GH-MET-003: Event timestamps should be monotonic within correlation chain."""
        inv = self._get_invariant("GH-MET-003")
        chains = {}
        for file_path, event_doc in self._event_files.items():
            corr_id = event_doc.get("metadata", {}).get("correlation_id", "__root__")
            if corr_id not in chains:
                chains[corr_id] = []
            ts = event_doc.get("timestamp", "")
            chains[corr_id].append((ts, file_path))

        MAX_SKEW_S = 5
        for corr_id, events in chains.items():
            sorted_events = sorted(events, key=lambda x: x[0])
            for i in range(1, len(sorted_events)):
                result.summary["total_checks"] += 1
                prev_ts, _ = sorted_events[i-1]
                curr_ts, curr_path = sorted_events[i]
                try:
                    prev_dt = datetime.fromisoformat(prev_ts)
                    curr_dt = datetime.fromisoformat(curr_ts)
                    if (curr_dt - prev_dt).total_seconds() < -MAX_SKEW_S:
                        result.summary["failed_warning"] += 1
                        result.violations.append(Violation(
                            invariant_id="GH-MET-003",
                            invariant_name=inv["name"],
                            severity="warning",
                            layer=2,
                            location_file=str(curr_path.relative_to(PROJECT_ROOT)),
                            expected=f"timestamp >= {prev_ts}",
                            actual=f"{curr_ts} (reverse causality)",
                            recovery_action="Check clock synchronization",
                        ))
                    else:
                        result.summary["passed"] += 1
                except Exception:
                    result.summary["skipped"] += 1

    # ── LAYER 3: GOVERNANCE RULES ────────────────────────────────────

    def _check_GR_POL_001_correction_convergence(self, result):
        """GR-POL-001: Every correction must converge (48h timeout, max 3 attempts)."""
        inv = self._get_invariant("GR-POL-001")
        now = datetime.now(timezone.utc)
        MAX_AGE_H = 48
        MAX_ATTEMPTS = 3

        for file_path, (_, fm, _) in self._correction_files.items():
            result.summary["total_checks"] += 1
            status = fm.get("status", "open")
            if status in ("applied", "rejected", "superseded"):
                result.summary["passed"] += 1
                continue

            date_str = fm.get("date", "")
            attempts = fm.get("attempts", 1)
            try:
                created = datetime.fromisoformat(date_str)
                age_h = (now - created).total_seconds() / 3600
            except Exception:
                age_h = 0

            if status == "open" and age_h > MAX_AGE_H:
                result.summary["failed_warning"] += 1
                result.summary["stale_corrections"] += 1
                result.violations.append(Violation(
                    invariant_id="GR-POL-001",
                    invariant_name=inv["name"],
                    severity="warning",
                    layer=3,
                    location_file=str(file_path.relative_to(PROJECT_ROOT)),
                    expected="resolved within 48h",
                    actual=f"open for {age_h:.1f}h",
                    recovery_action="Arbiter MUST auto-close, reassign, or extend with written rationale",
                ))
            elif attempts > MAX_ATTEMPTS:
                result.summary["failed_warning"] += 1
                result.summary["stale_corrections"] += 1
                result.violations.append(Violation(
                    invariant_id="GR-POL-001",
                    invariant_name=inv["name"],
                    severity="warning",
                    layer=3,
                    location_file=str(file_path.relative_to(PROJECT_ROOT)),
                    expected=f"attempts <= {MAX_ATTEMPTS}",
                    actual=f"{attempts} attempts",
                    recovery_action="Arbiter MUST reject or supersede after max attempts",
                ))
            else:
                result.summary["passed"] += 1

    # ── HELPERS ──────────────────────────────────────────────────────

    def _get_invariant(self, inv_id):
        invs = self._load_invariants()
        for section_key in ["structural", "governance", "events",
                             "health_metrics", "governance_rules"]:
            for item in invs.get(section_key, []) or []:
                if item.get("id") == inv_id:
                    return item
        return {"id": inv_id, "name": inv_id}

    def _collect_files(self, target):
        """Gather all SSOT, event, and correction files for validation."""
        # SSOT files
        for d in [SSOT_DIR, LEARNING_DIR, SCHEMAS_DIR]:
            if d.exists():
                for f in d.rglob("*.md"):
                    raw, fm, body = self._load_file(f)
                    if fm:
                        self._ssot_files[f] = (raw, fm, body)
                for f in d.rglob("*.yaml"):
                    raw, fm, body = self._load_file(f)
                    if fm:
                        self._ssot_files[f] = (raw, fm, body)

        # Event files
        if EVENT_STORE_DIR.exists():
            for f in EVENT_STORE_DIR.rglob("*.yaml"):
                try:
                    with open(f) as fh:
                        doc = yaml.safe_load(fh)
                    if doc and isinstance(doc, dict):
                        self._event_files[f] = doc
                except Exception:
                    pass

        # Correction files
        if CORRECTIONS_DIR.exists():
            for f in CORRECTIONS_DIR.rglob("*.md"):
                raw, fm, body = self._load_file(f)
                if fm and "status" in fm:
                    self._correction_files[f] = (raw, fm, body)

    # ── MAIN ENTRY POINT ─────────────────────────────────────────────

    def validate(self, target="full-system"):
        """
        Run all invariant checks. Returns ValidationResult.

        target: "full-system" | path to file | path to directory
        """
        import time
        t0 = time.time()

        result = ValidationResult()

        # Load invariants spec (fail fast if missing)
        try:
            self._load_invariants()
        except Exception as e:
            result.error = {
                "code": "ERR-VAL-003",
                "type": "DEPENDENCY_MISSING",
                "message": f"Cannot load invariants: {e}",
            }
            return result

        # Collect files
        self._collect_files(target)

        # ── LAYER 1: Hard Invariants (fail = REJECT, short-circuit) ──
        self._check_S_INV_001_no_broken_references(result)
        self._check_S_INV_002_frontmatter_completeness(result)
        self._check_S_INV_003_schema_compliance(result)

        # Governance (phase-gated)
        self._check_G_INV_001_every_domain_has_owner(result)
        self._check_G_INV_002_one_concept_one_owner(result)

        # Event integrity
        self._check_E_INV_001_event_immutability(result)
        self._check_E_INV_002_event_causality_chain(result)

        # ── LAYER 2: Health Metrics (warn, continue) ──────────────────
        self._check_GH_MET_001_unreferenced_nodes(result)
        self._check_GH_MET_002_no_circular_dependency(result)
        self._check_GH_MET_003_event_ordering_monotonic(result)

        # ── LAYER 3: Governance Rules (flag, continue) ────────────────
        self._check_GR_POL_001_correction_convergence(result)

        result.summary["duration_ms"] = int((time.time() - t0) * 1000)
        return result


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validator — deterministic constraint engine")
    parser.add_argument("--target", default="full-system",
                        help="File, directory, or 'full-system' (default)")
    parser.add_argument("--phase", default="phase_1",
                        choices=["phase_0", "phase_1", "phase_2"],
                        help="Bootstrap phase (default: phase_1)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    v = Validator(phase=args.phase)
    result = v.validate(target=args.target)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"valid: {result.valid}")
        print(f"checks: {result.summary['total_checks']} total, "
              f"{result.summary['passed']} passed, "
              f"{result.summary['failed_critical']} critical, "
              f"{result.summary['failed_warning']} warnings, "
              f"{result.summary['skipped']} skipped")
        if result.violations:
            print(f"\nviolations ({len(result.violations)}):")
            for v in result.violations:
                loc = v.location_file or v.location_field or "—"
                print(f"  [{v.severity.upper()}] {v.invariant_id} @ {loc}: "
                      f"expected {v.expected}, got {v.actual}")
        if result.error:
            print(f"\nerror: {result.error['code']} — {result.error['message']}")

    sys.exit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
