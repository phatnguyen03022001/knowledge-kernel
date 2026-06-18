#!/usr/bin/env python3
"""
Diagnostic Normalizer (M2.1).

Transforms raw violation data into classified, grouped diagnostics
using deterministic rules only. Zero interpretation.

Three functions:
  1. NORMALIZE — map violations to canonical categories
  2. CLASSIFY  — assign severity (from invariant spec, not judgment)
  3. GROUP     — detect recurring patterns (same invariant + same file)

This is a data normalization layer, not an interpretation layer.
It structures raw data so M3 Auditor doesn't have to invent taxonomy.

HARD CONSTRAINT:
  All classification rules are DETERMINISTIC.
  No ML. No heuristics. No contextual judgment.
  If a rule can't be expressed as a boolean expression over
  the violation data, it does not belong here.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ============================================================================
# CANONICAL VIOLATION CATEGORIES (deterministic mapping)
# ============================================================================
# invariant_id → category. One-to-one, no ambiguity.
# These categories are the vocabulary M3 Auditor will consume.

CATEGORY_MAP = {
    # Structural
    "S-INV-001": "broken-reference",
    "S-INV-002": "incomplete-provenance",
    "S-INV-003": "schema-violation",
    # Governance
    "G-INV-001": "missing-ownership",
    "G-INV-002": "ownership-conflict",
    "G-INV-003": "unlinked-correction",
    # Events
    "E-INV-001": "tampered-event",
    "E-INV-002": "broken-causality",
    # Health
    "GH-MET-001": "knowledge-decay",
    "GH-MET-002": "circular-dependency",
    "GH-MET-003": "clock-skew",
    # Governance rules
    "GR-POL-001": "stale-correction",
}

# Severity is read from the invariant spec, not assigned here.
# This table is the FALLBACK only if the invariant spec is unavailable.
FALLBACK_SEVERITY = {
    "broken-reference":       "critical",
    "incomplete-provenance":  "critical",
    "schema-violation":       "critical",
    "missing-ownership":      "critical",
    "ownership-conflict":     "critical",
    "unlinked-correction":    "critical",
    "tampered-event":         "critical",
    "broken-causality":       "critical",
    "knowledge-decay":        "warning",
    "circular-dependency":    "critical",
    "clock-skew":             "warning",
    "stale-correction":       "warning",
}


# ============================================================================
# NORMALIZER
# ============================================================================

def normalize(violations):
    """
    Normalize raw violations → canonical diagnostics.

    Input:  list of violation dicts (from Validator output)
    Output: list of normalized diagnostic dicts

    Each diagnostic has:
      - category: canonical category name
      - severity: from invariant spec (critical/warning)
      - invariant_id: original invariant that flagged it
      - location: file + field
      - fingerprint: unique key for grouping (category + file + field)
    """
    diagnostics = []
    for v in (violations or []):
        inv_id = v.get("invariant_id", "unknown")
        category = CATEGORY_MAP.get(inv_id, "unknown-violation")
        severity = v.get("severity", FALLBACK_SEVERITY.get(category, "warning"))

        loc = v.get("location", {}) or {}
        file_path = loc.get("file", "unknown")
        field = loc.get("field", "")

        diagnostic = {
            "category": category,
            "severity": severity,
            "invariant_id": inv_id,
            "invariant_name": v.get("invariant_name", inv_id),
            "location_file": file_path,
            "location_field": field,
            "expected": loc.get("expected", ""),
            "actual": loc.get("actual", ""),
            "recovery_auto": (v.get("recovery", {}) or {}).get("auto_recoverable", False),
            "fingerprint": _fingerprint(category, file_path, field),
        }
        diagnostics.append(diagnostic)
    return diagnostics


# ============================================================================
# CLASSIFIER
# ============================================================================

def classify(diagnostics):
    """
    Classify diagnostics by severity and category.

    Pure aggregation — no judgment added.

    Output:
      by_severity:  {critical: [diagnostics], warning: [diagnostics]}
      by_category:  {category_name: [diagnostics]}
      counts:       {total, critical, warning, by category}
    """
    by_severity = {"critical": [], "warning": []}
    by_category = defaultdict(list)
    counts = {"total": len(diagnostics), "critical": 0, "warning": 0,
               "by_category": {}}

    for d in diagnostics:
        sev = d["severity"]
        cat = d["category"]

        if sev in by_severity:
            by_severity[sev].append(d)
        else:
            by_severity["warning"].append(d)

        by_category[cat].append(d)
        counts[sev] = counts.get(sev, 0) + 1

    for cat, items in by_category.items():
        counts["by_category"][cat] = len(items)

    return {
        "by_severity": {k: v for k, v in by_severity.items()},
        "by_category": dict(by_category),
        "counts": counts,
    }


# ============================================================================
# GROUPER (pattern detection — deterministic only)
# ============================================================================

def group(diagnostics, history=None):
    """
    Group recurring patterns.

    Rules (deterministic, no ML):
      - Same fingerprint appearing > 1 time in current run = "recurring"
      - Same fingerprint appearing in previous run = "persistent"
      - Fingerprint seen once, never before = "new"

    history: optional list of fingerprints from previous run(s)

    Returns:
      groups: {fingerprint: {category, count, status, diagnostics}}
      summary: {new, recurring, persistent, total_groups}
    """
    current_fingerprints = defaultdict(list)
    for d in diagnostics:
        current_fingerprints[d["fingerprint"]].append(d)

    history_set = set(history or [])

    groups = {}
    summary = {"new": 0, "recurring": 0, "persistent": 0, "total_groups": 0}

    for fp, items in current_fingerprints.items():
        if len(items) > 1:
            status = "recurring"
        elif fp in history_set:
            status = "persistent"
        else:
            status = "new"

        groups[fp] = {
            "fingerprint": fp,
            "category": items[0]["category"],
            "severity": items[0]["severity"],
            "count": len(items),
            "status": status,
            "location_file": items[0]["location_file"],
            "location_field": items[0]["location_field"],
            "diagnostics": items,
        }
        summary[status] += 1
        summary["total_groups"] += 1

    return groups, summary


# ============================================================================
# DIAGNOSTIC ENGINE (coordinates all three)
# ============================================================================

class DiagnosticEngine:
    """
    Coordinates normalize → classify → group.

    Usage:
        de = DiagnosticEngine()
        report = de.process(violations, history_fingerprints=["fp1", "fp2"])
        print(json.dumps(report, indent=2))
    """

    def __init__(self):
        self._history = []  # fingerprints from previous runs

    def process(self, violations, history_fingerprints=None):
        """
        Process raw violations into a diagnostic report.

        Returns a dict ready for M3 Auditor to consume.
        """
        # Step 1: Normalize
        diagnostics = normalize(violations)

        # Step 2: Classify
        classified = classify(diagnostics)

        # Step 3: Group
        history = history_fingerprints or self._history
        groups, group_summary = group(diagnostics, history)

        # Record fingerprints for next run
        self._history = list(groups.keys())

        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input_violations": len(violations or []),
            "output_diagnostics": len(diagnostics),
            "classification": classified,
            "groups": {
                "summary": group_summary,
                "details": {fp: {
                    "category": g["category"],
                    "severity": g["severity"],
                    "count": g["count"],
                    "status": g["status"],
                    "location": f"{g['location_file']}{' @ ' + g['location_field'] if g['location_field'] else ''}",
                } for fp, g in groups.items()},
            },
            "fingerprints": list(groups.keys()),
        }

    def load_history(self, fingerprints):
        """Restore history from a previous session."""
        self._history = fingerprints or []


# ============================================================================
# HELPERS
# ============================================================================

def _fingerprint(category, file_path, field=""):
    """
    Create a deterministic fingerprint for grouping.

    Format: category::file_path::field
    This ensures same violation in same location = same fingerprint.
    """
    field_part = f"::{field}" if field else ""
    return f"{category}::{file_path}{field_part}"


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Diagnostic Normalizer — classify + group violations (deterministic only)"
    )
    parser.add_argument("--input", help="Path to JSON file with violations array")
    parser.add_argument("--history", help="Path to JSON file with previous fingerprints")
    parser.add_argument("--stdin", action="store_true", help="Read violations from stdin (JSON)")
    args = parser.parse_args()

    violations = []

    if args.stdin:
        violations = json.loads(sys.stdin.read())
        if isinstance(violations, dict):
            violations = violations.get("violations", [])
    elif args.input:
        with open(args.input) as f:
            data = json.load(f)
            if isinstance(data, list):
                violations = data
            else:
                violations = data.get("violations", [])
    else:
        # Demo mode
        violations = [
            {"invariant_id": "S-INV-001", "severity": "critical",
             "invariant_name": "no-broken-references",
             "location": {"file": "ssot/broken.md", "field": "links[0]",
                          "expected": "exists", "actual": "missing"}},
            {"invariant_id": "S-INV-001", "severity": "critical",
             "invariant_name": "no-broken-references",
             "location": {"file": "ssot/broken.md", "field": "links[1]",
                          "expected": "exists", "actual": "missing"}},
            {"invariant_id": "GH-MET-001", "severity": "warning",
             "invariant_name": "unreferenced-node-threshold",
             "location": {"file": "ssot/orphan.md", "field": "",
                          "expected": "referenced", "actual": "unreferenced"}},
        ]

    history = []
    if args.history:
        with open(args.history) as f:
            history = json.load(f)

    de = DiagnosticEngine()
    if history:
        de.load_history(history)

    report = de.process(violations, history)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
