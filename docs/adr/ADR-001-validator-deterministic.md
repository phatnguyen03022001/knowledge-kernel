# ADR-001: Validator is a deterministic constraint engine

## Status
Accepted (2026-06-18)

## Context
The Validator (M1) is the first layer in the Phase 2 pipeline. It checks system state against invariants. The design question: should Validator have the ability to interpret results and suggest fixes, or should it only report pass/fail?

## Decision
Validator is a **pure deterministic constraint engine.** It checks invariants and returns REJECT/WARN/FLAG. It does NOT interpret results, suggest fixes, or resolve disputes.

## Rationale
1. **Separation of concerns.** Interpretation is Auditor's job (M3). If Validator interprets, it becomes a god-object that both enforces AND judges.
2. **Deterministic replay.** Same input → same output. This is required for the trace replay guarantee (M1.5) and projection determinism (M2).
3. **Testability.** A deterministic validator can be tested with known inputs and expected outputs. An interpreting validator requires testing judgment quality, which is unbounded.
4. **Precedent.** This pattern follows Kubernetes admission controllers (validate, don't mutate), etcd Raft (check invariants, don't interpret), and Kafka log validation (structural, not semantic).

## Consequences
- Validator output is machine-readable and stable (violations list with invariant IDs).
- Auditor (M3) must be built as a separate layer to provide human-readable interpretation.
- Any future "smart validation" must be built in M3, never in M1.
- Validator code is simpler and smaller (~750 lines) because it doesn't need interpretation logic.

## Alternatives Considered
- **Smart Validator:** Validator interprets results and suggests fixes. Rejected: blurs M1/M3 boundary, makes replay non-deterministic, creates god-object.
- **Pluggable Rules:** Validator loads rules dynamically from external sources. Rejected for V1: adds complexity without clear need. Can be added in Phase 3 if needed.
