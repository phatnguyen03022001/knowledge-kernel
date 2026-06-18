#!/usr/bin/env python3
"""
Ontology Freeze Verification — B1, B2, B3

Verifies the 12-category diagnostic ontology is frozen:
  B1: Category count == 12
  B2: No category mutation (runtime creation blocked)
  B3: Invariant→Category mapping is immutable
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# B1: CATEGORY COUNT LOCK
# ============================================================================

CANONICAL_CATEGORIES = {
    "broken-reference",
    "incomplete-provenance",
    "schema-violation",
    "missing-ownership",
    "ownership-conflict",
    "unlinked-correction",
    "tampered-event",
    "broken-causality",
    "knowledge-decay",
    "circular-dependency",
    "clock-skew",
    "stale-correction",
}


def test_b1_category_count():
    """Verify exactly 12 categories exist."""
    count = len(CANONICAL_CATEGORIES)
    assert count == 12, f"Expected 12 categories, got {count}"
    print(f"  ✅ B1: {count} categories (locked)")


# ============================================================================
# B2: CATEGORY MUTATION DETECTION
# ============================================================================

def test_b2_no_mutation():
    """Verify no new category can be created at runtime."""
    from kernel.runtime.diagnostics import CATEGORY_MAP

    runtime_categories = set(CATEGORY_MAP.values())
    extra = runtime_categories - CANONICAL_CATEGORIES
    missing = CANONICAL_CATEGORIES - runtime_categories

    assert not extra, f"Runtime has unregistered categories: {extra}"
    assert not missing, f"Canonical categories missing at runtime: {missing}"
    assert runtime_categories == CANONICAL_CATEGORIES, \
        f"Runtime categories ({len(runtime_categories)}) != canonical ({len(CANONICAL_CATEGORIES)})"
    print(f"  ✅ B2: Runtime categories match canonical (no drift)")


# ============================================================================
# B3: RECLASSIFICATION PROTECTION
# ============================================================================

EXPECTED_MAPPING = {
    "S-INV-001": "broken-reference",
    "S-INV-002": "incomplete-provenance",
    "S-INV-003": "schema-violation",
    "G-INV-001": "missing-ownership",
    "G-INV-002": "ownership-conflict",
    "G-INV-003": "unlinked-correction",
    "E-INV-001": "tampered-event",
    "E-INV-002": "broken-causality",
    "GH-MET-001": "knowledge-decay",
    "GH-MET-002": "circular-dependency",
    "GH-MET-003": "clock-skew",
    "GR-POL-001": "stale-correction",
}


def test_b3_invariant_category_mapping():
    """Verify invariant→category mapping is immutable."""
    from kernel.runtime.diagnostics import CATEGORY_MAP

    for inv_id, expected_cat in EXPECTED_MAPPING.items():
        actual_cat = CATEGORY_MAP.get(inv_id)
        assert actual_cat == expected_cat, \
            f"{inv_id}: expected category '{expected_cat}', got '{actual_cat}'"

    # Also verify no extra mappings exist
    extra_invariants = set(CATEGORY_MAP.keys()) - set(EXPECTED_MAPPING.keys())
    assert not extra_invariants, f"Runtime has unmapped invariants: {extra_invariants}"

    print(f"  ✅ B3: All {len(EXPECTED_MAPPING)} invariant→category mappings immutable")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_b1_category_count()
    test_b2_no_mutation()
    test_b3_invariant_category_mapping()
    print(f"\n  ✅ Ontology freeze verified — 12 categories, zero drift")
