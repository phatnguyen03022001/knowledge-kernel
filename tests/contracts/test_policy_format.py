#!/usr/bin/env python3
"""
Policy Format Verification — FM-ARCH-001

Verifies every M3 policy conforms to category + threshold + action:
  - 15 policies across 3 files (hard-fail.yaml, risk-thresholds.yaml, trend-alerts.yaml)
  - No policy uses cross-category reasoning (condition fields are bounded per type)
  - Policy types are recognized (hard_fail / risk / trend)
  - Risk policies have valid weights; hard_fail policies are severity critical

Contrapositive: if a developer adds a policy with cross-category logic,
the condition field constraint test fails immediately.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# CONSTANTS
# ============================================================================

POLICIES_DIR = PROJECT_ROOT / "governance" / "policies"

EXPECTED_COUNTS = {
    "hard-fail.yaml": 5,
    "risk-thresholds.yaml": 7,
    "trend-alerts.yaml": 3,
}

KNOWN_TYPES = {"hard_fail", "risk", "trend"}

# Fields allowed in 'condition' per policy type (FM-ARCH-001 enforcement)
# Any field outside these sets = cross-category reasoning = VIOLATION
CONDITION_ALLOWED = {
    "hard_fail": {"category", "threshold"},
    "risk": {"category", "threshold"},
    "trend": {"metric", "direction", "window_runs", "threshold_runs"},
}

# Base required fields (every policy must have these)
BASE_REQUIRED = {"id", "name", "type", "condition", "message"}


# ============================================================================
# HELPERS
# ============================================================================

def load_all_policies():
    """Load all policy YAML files. Returns dict: filename -> list of policy dicts."""
    import yaml
    all_policies = {}
    for pf in sorted(POLICIES_DIR.glob("*.yaml")):
        with open(pf) as f:
            doc = yaml.safe_load(f)
        all_policies[pf.name] = doc.get("policies", [])
    return all_policies


# ============================================================================
# TESTS
# ============================================================================

def test_fm_arch_001_policy_count():
    """Verify exact policy counts per file (no accidental additions/deletions)."""
    all_policies = load_all_policies()
    errors = []

    for filename, expected in EXPECTED_COUNTS.items():
        actual = len(all_policies.get(filename, []))
        if actual != expected:
            errors.append(
                f"{filename}: expected {expected} policies, got {actual}"
            )

    total = sum(len(v) for v in all_policies.values())
    if total != 15:
        errors.append(f"Total: expected 15 policies, got {total}")

    if errors:
        print(f"\n  FM-ARCH-001 COUNT VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ FM-ARCH-001: 15 policies across 3 files (5+7+3)")


def test_fm_arch_001_required_fields():
    """
    Core structural check. Verifies:
      - Every policy has base required fields
      - type is in known set
      - condition has exactly the allowed fields for its type
    """
    all_policies = load_all_policies()
    errors = []

    for filename, policies in all_policies.items():
        for i, p in enumerate(policies):
            prefix = f"{filename}#{i} ({p.get('id', 'NO-ID')})"

            # Base fields
            missing_base = BASE_REQUIRED - set(p.keys())
            if missing_base:
                errors.append(f"{prefix}: missing required fields: {missing_base}")

            # Type check
            ptype = p.get("type")
            if ptype not in KNOWN_TYPES:
                errors.append(
                    f"{prefix}: unknown type '{ptype}' — must be one of {KNOWN_TYPES}"
                )
                continue  # skip condition check if type is unknown

            # Condition fields (FM-ARCH-001 core)
            condition = p.get("condition", {})
            allowed_cond_fields = CONDITION_ALLOWED[ptype]

            # Check for extra fields
            extra = set(condition.keys()) - allowed_cond_fields
            if extra:
                errors.append(
                    f"{prefix}: condition has extra fields {extra} — "
                    f"allowed for type '{ptype}': {allowed_cond_fields}. "
                    f"FM-ARCH-001 VIOLATION: cross-category reasoning"
                )

            # Type-specific: hard_fail + risk must have category + threshold
            if ptype in ("hard_fail", "risk"):
                if "category" not in condition:
                    errors.append(
                        f"{prefix}: hard_fail/risk must have condition.category"
                    )
                if "threshold" not in condition:
                    errors.append(
                        f"{prefix}: hard_fail/risk must have condition.threshold"
                    )

            # Type-specific: trend must have metric
            if ptype == "trend":
                if "metric" not in condition:
                    errors.append(
                        f"{prefix}: trend must have condition.metric"
                    )
                has_direction = "direction" in condition
                has_window = "window_runs" in condition
                has_threshold_runs = "threshold_runs" in condition
                if not has_direction and not has_threshold_runs:
                    errors.append(
                        f"{prefix}: trend must have condition.direction "
                        f"or condition.threshold_runs"
                    )

            # Check condition values for non-null
            for key, val in condition.items():
                if val is None:
                    errors.append(f"{prefix}: condition.{key} is None")

    if errors:
        print(f"\n  FM-ARCH-001 STRUCTURE VIOLATIONS ({len(errors)}):")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ FM-ARCH-001: All policies conform to category+threshold+action format")


def test_fm_arch_001_risk_has_weight():
    """Every risk policy must have a numeric weight in (0, 1]."""
    all_policies = load_all_policies()
    errors = []

    for filename, policies in all_policies.items():
        for p in policies:
            if p.get("type") != "risk":
                continue
            wid = p.get("id", "NO-ID")
            weight = p.get("weight")
            if weight is None:
                errors.append(f"{wid}: risk policy missing 'weight' field")
            elif not isinstance(weight, (int, float)):
                errors.append(f"{wid}: weight must be numeric, got {type(weight).__name__}")
            elif weight <= 0 or weight > 1:
                errors.append(f"{wid}: weight {weight} must be in (0, 1]")

    if errors:
        print(f"\n  WEIGHT VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ Risk policies: all have valid weights in (0, 1]")


def test_fm_arch_001_hard_fail_severity():
    """Every hard_fail policy must have severity: critical."""
    all_policies = load_all_policies()
    policies = [p for plist in all_policies.values() for p in plist]
    errors = []

    hard_fails = [p for p in policies if p.get("type") == "hard_fail"]
    for p in hard_fails:
        if p.get("severity") != "critical":
            errors.append(
                f"{p.get('id', 'NO-ID')}: hard_fail severity must be 'critical', "
                f"got '{p.get('severity')}'"
            )

    if len(hard_fails) != 5:
        errors.append(f"Expected 5 hard_fail policies, got {len(hard_fails)}")

    if errors:
        print(f"\n  SEVERITY VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ Hard fail policies: all severity=critical (5/5)")


def test_fm_arch_001_all_have_message():
    """Every policy must have a non-empty message."""
    policies = [p for plist in load_all_policies().values() for p in plist]
    errors = []

    for p in policies:
        msg = p.get("message", "")
        if not msg or not isinstance(msg, str) or not msg.strip():
            errors.append(f"{p.get('id', 'NO-ID')}: message is empty or missing")

    if errors:
        print(f"\n  MESSAGE VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ All 15 policies have non-empty message strings")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_fm_arch_001_policy_count()
    test_fm_arch_001_required_fields()
    test_fm_arch_001_risk_has_weight()
    test_fm_arch_001_hard_fail_severity()
    test_fm_arch_001_all_have_message()
    print(f"\n  ✅ FM-ARCH-001 verified — 15 policies, zero cross-category reasoning")
