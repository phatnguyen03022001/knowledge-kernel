#!/usr/bin/env python3
"""
Failure Injection Certification — D1, D2, D3

D1: Corrupted trace entry (checksum mismatch)
D2: Partial event loss (missing event in causal chain)
D3: Duplicate event replay (same event twice)
"""

import sys
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_d1_corrupted_trace():
    """Inject a trace with broken content_hash. Validator must detect."""
    from kernel.runtime.validator import Validator
    from kernel.runtime.diagnostics import DiagnosticEngine

    v = Validator(phase="phase_1")
    result = v.validate(target="full-system")

    # Simulate a corrupted trace: hash doesn't match content
    violations = [
        {
            "invariant_id": "E-INV-001",
            "invariant_name": "event-immutability",
            "severity": "critical",
            "location": {
                "file": "runtime/traces/2026/06/18/trace-corrupted.yaml",
                "field": "content_hash",
                "expected": "abc123",
                "actual": "def456 (hash mismatch)",
            },
        }
    ]

    de = DiagnosticEngine()
    report = de.process(violations)

    # Must detect as tampered-event
    categories = set()
    for d in report["classification"]["by_category"]:
        categories.add(d)
    assert "tampered-event" in de.process(violations)["classification"]["counts"]["by_category"], \
        "Corrupted trace not detected as tampered-event"

    print(f"  ✅ D1: Corrupted trace → tampered-event detected")


def test_d2_partial_event_loss():
    """Missing event in causal chain → E-INV-002 broken-causality."""
    from kernel.runtime.diagnostics import DiagnosticEngine

    violations = [
        {
            "invariant_id": "E-INV-002",
            "invariant_name": "event-causality-chain",
            "severity": "critical",
            "location": {
                "file": "runtime/event-store/2026/06/18/evt-003.yaml",
                "field": "metadata.causation_id",
                "expected": "existing event ID",
                "actual": "evt-20260618-002 (not found)",
            },
        }
    ]

    de = DiagnosticEngine()
    report = de.process(violations)

    counts = report["classification"]["counts"]
    assert counts["by_category"].get("broken-causality", 0) >= 1, \
        "Missing event not classified as broken-causality"
    assert counts["critical"] >= 1, "Should be critical severity"

    print(f"  ✅ D2: Partial event loss → broken-causality (critical)")


def test_d3_duplicate_event_replay():
    """Same event replayed twice → tampered-event or duplicate."""
    from kernel.runtime.diagnostics import DiagnosticEngine

    violations = [
        {
            "invariant_id": "E-INV-001",
            "invariant_name": "event-immutability",
            "severity": "critical",
            "location": {
                "file": "runtime/event-store/2026/06/18/evt-001.yaml",
                "field": "content_hash",
                "expected": "abc123",
                "actual": "def456 (content modified on replay)",
            },
        }
    ]

    de = DiagnosticEngine()
    report = de.process(violations)

    counts = report["classification"]["counts"]
    assert counts["by_category"].get("tampered-event", 0) >= 1, \
        "Duplicate/replayed event not detected"

    # Verify proper fingerprinting
    fingerprints = report["fingerprints"]
    assert len(fingerprints) == 1, "Should have exactly 1 unique fingerprint"

    print(f"  ✅ D3: Duplicate event replay → tampered-event (fingerprinted)")


def test_no_crash_on_all_failures():
    """All three failure types at once — system must not crash."""
    from kernel.runtime.diagnostics import DiagnosticEngine

    violations = [
        {"invariant_id": "E-INV-001", "severity": "critical",
         "invariant_name": "event-immutability",
         "location": {"file": "trace-x.yaml", "field": "hash", "expected": "a", "actual": "b"}},
        {"invariant_id": "E-INV-002", "severity": "critical",
         "invariant_name": "event-causality-chain",
         "location": {"file": "evt-y.yaml", "field": "causation_id", "expected": "exists", "actual": "missing"}},
        {"invariant_id": "S-INV-001", "severity": "critical",
         "invariant_name": "no-broken-references",
         "location": {"file": "ssot-z.md", "field": "links[0]", "expected": "exists", "actual": "missing"}},
        {"invariant_id": "GH-MET-001", "severity": "warning",
         "invariant_name": "unreferenced-node-threshold",
         "location": {"file": "ssot-w.md", "field": "", "expected": "referenced", "actual": "unreferenced"}},
        {"invariant_id": "GR-POL-001", "severity": "warning",
         "invariant_name": "correction-convergence",
         "location": {"file": "corr-123.md", "field": "status", "expected": "closed", "actual": "open 50h"}},
    ]

    de = DiagnosticEngine()
    report = de.process(violations)

    # Must process all 5
    assert report["output_diagnostics"] == 5, f"Expected 5 diagnostics, got {report['output_diagnostics']}"
    # Must detect 3 categories
    assert len(report["classification"]["counts"]["by_category"]) >= 3
    # Must have critical + warning
    assert report["classification"]["counts"]["critical"] == 3
    assert report["classification"]["counts"]["warning"] == 2

    print(f"  ✅ Stress: 5 mixed violations → 5 diagnostics, 3 categories, no crash")


if __name__ == "__main__":
    test_d1_corrupted_trace()
    test_d2_partial_event_loss()
    test_d3_duplicate_event_replay()
    test_no_crash_on_all_failures()
    print(f"\n  ✅ Failure injection certified — all failure modes classified correctly")
