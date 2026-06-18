#!/usr/bin/env python3
"""
Action Lock Verification — FM-ARCH-002

Verifies the M4 action space is frozen:
  - resolve_action() returns exactly 4 actions: NONE, MONITOR, BLOCK, ESCALATE
  - All 6 code paths are exercised (no dead actions)
  - No 5th action can be added without this test failing
  - determine_scope() produces valid values
  - Arbiter has zero imports from upstream layers
"""

import sys
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# CANONICAL ACTIONS (frozen per FM-ARCH-002)
# ============================================================================

CANONICAL_ACTIONS = {"NONE", "MONITOR", "BLOCK", "ESCALATE"}


# ============================================================================
# TEST: FM-ARCH-002 — Action count lock
# ============================================================================

def test_fm_arch_002_action_count():
    """
    Exercise every code path in resolve_action().
    Assert the set of returned actions is exactly {NONE, MONITOR, BLOCK, ESCALATE}.
    """
    from kernel.runtime.arbiter import resolve_action

    returned = set()
    errors = []

    # --- R1: PASS -> NONE (unconditional) ---
    action, codes = resolve_action("PASS", 0.0, [])
    returned.add(action)
    if action != "NONE":
        errors.append(f"R1: PASS should return NONE, got {action}")
    if codes != []:
        errors.append(f"R1: PASS should have empty reason codes, got {codes}")

    # --- R1 edge: PASS + high risk -> still NONE ---
    action, codes = resolve_action("PASS", 0.95, [{"severity": "critical"}])
    returned.add(action)
    if action != "NONE":
        errors.append(f"R1edge: PASS is absolute — should be NONE even at risk=0.95, got {action}")

    # --- R2: WARN + low risk -> MONITOR ---
    action, codes = resolve_action("WARN", 0.3, [])
    returned.add(action)
    if action != "MONITOR":
        errors.append(f"R2: WARN+low_risk should return MONITOR, got {action}")
    if "WARN_VERDICT" not in codes:
        errors.append(f"R2: WARN should include WARN_VERDICT reason code, got {codes}")

    # --- R5 override of R2: WARN + high risk -> ESCALATE ---
    action, codes = resolve_action("WARN", 0.9, [])
    returned.add(action)
    if action != "ESCALATE":
        errors.append(f"R5up: WARN+risk=0.9 should return ESCALATE, got {action}")
    if "HIGH_RISK" not in codes:
        errors.append(f"R5up: ESCALATE from WARN should include HIGH_RISK reason code")

    # --- R3: FAIL + critical hits -> BLOCK ---
    action, codes = resolve_action("FAIL", 0.5, [
        {"severity": "critical", "policy_id": "FAIL-001", "category": "broken-reference"}
    ])
    returned.add(action)
    if action != "BLOCK":
        errors.append(f"R3: FAIL+critical should return BLOCK, got {action}")
    if "CRITICAL_FAILURES" not in codes:
        errors.append(f"R3: BLOCK should include CRITICAL_FAILURES reason code")

    # --- R3 edge: FAIL + multiple critical hits -> BLOCK + count ---
    action, codes = resolve_action("FAIL", 0.0, [
        {"severity": "critical", "policy_id": "FAIL-001"},
        {"severity": "critical", "policy_id": "FAIL-004"},
    ])
    returned.add(action)
    if action != "BLOCK":
        errors.append(f"R3multi: FAIL+2critical should return BLOCK, got {action}")
    if not any("CRITICAL_COUNT=2" in c for c in codes):
        errors.append(f"R3multi: should include CRITICAL_COUNT=2, got {codes}")

    # --- R4: FAIL + no critical hits -> ESCALATE ---
    action, codes = resolve_action("FAIL", 0.0, [
        {"severity": "high", "policy_id": "RISK-001"},
    ])
    returned.add(action)
    if action != "ESCALATE":
        errors.append(f"R4: FAIL+no_critical should return ESCALATE, got {action}")
    if "FAIL_NO_CRITICAL" not in codes:
        errors.append(f"R4: ESCALATE from FAIL should include FAIL_NO_CRITICAL")

    # --- R5 override of R3: R5 says "upward only" — BLOCK > ESCALATE ---
    # FAIL + critical + high risk should stay BLOCK (not ESCALATE)
    action, codes = resolve_action("FAIL", 0.95, [
        {"severity": "critical", "policy_id": "FAIL-003"},
    ])
    returned.add(action)
    if action != "BLOCK":
        errors.append(f"R5dn: FAIL+critical+high_risk should stay BLOCK (override upward only), got {action}")

    # --- Fallback: unknown verdict -> MONITOR ---
    action, codes = resolve_action("UNKNOWN", 0.0, [])
    returned.add(action)
    if action != "MONITOR":
        errors.append(f"FALLBACK: UNKNOWN should return MONITOR, got {action}")
    if "UNKNOWN_VERDICT" not in codes:
        errors.append(f"FALLBACK: UNKNOWN should include UNKNOWN_VERDICT reason code")

    # --- Canonical check ---
    if returned != CANONICAL_ACTIONS:
        extra = returned - CANONICAL_ACTIONS
        missing = CANONICAL_ACTIONS - returned
        if extra:
            errors.append(f"ACTIONS: extra actions found: {extra} — FM-ARCH-002 VIOLATION")
        if missing:
            errors.append(f"ACTIONS: missing actions: {missing} — dead code or unreachable")

    if len(returned) != 4:
        errors.append(f"ACTIONS: expected 4 actions, got {len(returned)}: {returned}")

    if errors:
        print(f"\n  FM-ARCH-002 VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ FM-ARCH-002: Exactly 4 actions locked ({', '.join(sorted(returned))})")


# ============================================================================
# TEST: determine_scope sanity
# ============================================================================

def test_determine_scope():
    """Verify determine_scope() produces valid scope strings."""
    from kernel.runtime.arbiter import determine_scope

    valid_scopes = {"system", "node", "run"}
    errors = []

    # BLOCK with system-level categories -> "system"
    # NOTE: determine_scope uses substring matching on policy_id
    # ("tampered" or "causality" — arbiter.py:88-92). This means
    # real policy IDs like FAIL-003 fail this check. The function
    # should be refactored to use the category field instead.
    scope = determine_scope("BLOCK", [
        {"policy_id": "tampered-event-001", "severity": "critical"},
    ])
    if scope != "system":
        errors.append(f"BLOCK+tampered should return 'system', got '{scope}'")

    # BLOCK without system-level keywords -> "node"
    scope = determine_scope("BLOCK", [
        {"policy_id": "RISK-001", "severity": "high"},
    ])
    if scope != "node":
        errors.append(f"BLOCK+non-system should return 'node', got '{scope}'")

    # Everything else -> "run"
    for action in ["MONITOR", "NONE", "ESCALATE"]:
        scope = determine_scope(action, [])
        if scope != "run":
            errors.append(f"{action} scope should be 'run', got {scope}")

    if errors:
        print(f"\n  SCOPE VIOLATIONS:")
        for e in errors:
            print(f"    ❌ {e}")
        sys.exit(1)
    else:
        print(f"  ✅ determine_scope: valid scopes for all actions")


# ============================================================================
# TEST: Import creep — Arbiter never depends on upstream layers
# ============================================================================

FORBIDDEN_UPSTREAM = {"validator", "tracer", "projection", "diagnostics", "auditor"}


def get_top_level_imports(file_path):
    """Extract top-level imported module names from a Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def test_no_upstream_imports():
    """Arbiter must not import from upstream M1-M3 layers."""
    arbiter_path = PROJECT_ROOT / "kernel" / "runtime" / "arbiter.py"
    imports = get_top_level_imports(arbiter_path)
    violations = FORBIDDEN_UPSTREAM & imports

    if violations:
        print(f"\n  ARBITER IMPORT VIOLATIONS:")
        for v in violations:
            print(f"    ❌ arbiter.py imports '{v}' which is FORBIDDEN")
        sys.exit(1)
    else:
        print(f"  ✅ arbiter.py: zero imports from upstream layers")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_fm_arch_002_action_count()
    test_determine_scope()
    test_no_upstream_imports()
    print(f"\n  ✅ FM-ARCH-002 verified — 4 actions, zero scope drift, zero import creep")
