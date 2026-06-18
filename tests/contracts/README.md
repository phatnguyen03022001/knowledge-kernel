# Contract Tests — ADR to Test Traceability

This directory verifies that ADR commitments are structurally enforced.
Each test maps to one or more ADRs or Failure Modes (FM-ARCH).

## Test Catalog

| Test File | What It Verifies | ADR | FM-ARCH |
|---|---|---|---|
| `test_layer_isolation.py` | Each layer only imports what it's allowed to import. Prevents M3 from depending on M4, etc. | ADR-001, ADR-002, ADR-003, ADR-004 | FM-ARCH-003 (coupling-creep) |
| `test_determinism.py` | Pipeline is deterministic: same input → same output across 10 runs (C1). Order-independent when causal order preserved (C2). | ADR-001, ADR-002 | — |
| `test_ontology_freeze.py` | 12 diagnostic categories are frozen (B1). No runtime category mutation (B2). Invariant→category mapping is immutable (B3). | ADR-003 | — |
| `test_failure_injection.py` | Corrupted traces detected as tampered-event (D1). Partial event loss detected as broken-causality (D2). Duplicate replay detected (D3). Multi-failure stress test. | ADR-001, ADR-003 | — |
| `test_action_lock.py` | M4's `resolve_action()` returns exactly 4 actions: NONE, MONITOR, BLOCK, ESCALATE. All 9 code paths exercised. No 5th action can be added silently. | ADR-004, ADR-005 | FM-ARCH-002 (routing-explosion) |
| `test_policy_format.py` | All 15 M3 policies conform to category+threshold+action. No cross-category reasoning. Condition fields bounded per type. | ADR-005 | FM-ARCH-001 (policy-drift) |
| `test_escalation_events.py` | escalation.created and escalation.resolved exist in event-types.yaml. Subscription routes to Arbiter. Pack conforms to schema. Event envelope is valid. | ADR-004 | — |

## Failure Mode Coverage

| Failure Mode | Prevention Rule | Enforcement |
|---|---|---|
| FM-ARCH-001 (policy-drift) | Every M3 policy must be category+threshold+action | `test_policy_format.py` — asserts allowed condition fields per type, catches cross-category reasoning |
| FM-ARCH-002 (routing-explosion) | M4 has exactly 4 actions | `test_action_lock.py` — asserts set size == 4, exercises all code paths |
| FM-ARCH-003 (coupling-creep) | Layer isolation runs on every commit | `test_layer_isolation.py` — import allowlist enforced via AST analysis |

## ADR Traceability Matrix

```
ADR-001 (Validator deterministic)
  → test_layer_isolation.py   (Validator must not import Arbiter)
  → test_determinism.py       (C1: multi-run determinism)
  → test_failure_injection.py (D1: corrupted traces handled)

ADR-002 (Projection no interpretation)
  → test_determinism.py       (C1: projection hash identical, C2: order independence)
  → test_layer_isolation.py   (Projection must not import Auditor/Arbiter)

ADR-003 (Auditor no ontology creation)
  → test_layer_isolation.py   (Auditor must not import Arbiter)
  → test_ontology_freeze.py   (B1/B2/B3: 12-category lock)
  → test_failure_injection.py (D2/D3: event causality)

ADR-004 (Arbiter externalized)
  → test_layer_isolation.py   (No upstream layer imports Arbiter)
  → test_action_lock.py       (FM-ARCH-002: exactly 4 actions)
  → test_escalation_events.py (Event communication channel)

ADR-005 (Architecture closed, failure modes)
  → test_action_lock.py       (FM-ARCH-002: action count lock)
  → test_policy_format.py     (FM-ARCH-001: policy structure lock)
  → test_layer_isolation.py   (FM-ARCH-003: layer coupling lock)
```

## How to Run

```bash
# Run all contract tests + scenario tests (via harness):
python3 tests/harness.py --all

# Run a single contract test directly:
python3 tests/contracts/test_action_lock.py
python3 tests/contracts/test_policy_format.py
python3 tests/contracts/test_escalation_events.py
python3 tests/contracts/test_layer_isolation.py
python3 tests/contracts/test_determinism.py
python3 tests/contracts/test_ontology_freeze.py
python3 tests/contracts/test_failure_injection.py

# All tests exit 0 on pass, 1 on fail.
```

## Adding a New Contract Test

1. Create `tests/contracts/test_YOUR_NAME.py` following the existing pattern:
   - Shebang: `#!/usr/bin/env python3`
   - Docstring describing what it verifies
   - `sys.path.insert(0, str(PROJECT_ROOT))` for imports
   - Test functions with print-based output (`[OK]` / `FAIL`)
   - `if __name__ == "__main__":` block
2. Update this README — add the test to the catalog table and ADR matrix.
3. Run `python3 tests/harness.py --all` to confirm auto-discovery and passing.
