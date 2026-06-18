# ADR-002: Projection MUST NOT interpret data

## Status
Accepted (2026-06-18)

## Context
The Projection layer (M2) builds materialized views from trace and event data. The design question: should Projection add trend analysis, severity judgment, or suggested actions to its output?

## Decision
Projection is a **pure view compiler.** It transforms immutable source data into structured views using deterministic functions only. It does NOT interpret trends, judge severity, or suggest actions. Trend labels (stable/clean/degrading/improving) are computed via deterministic threshold comparison, not semantic reasoning.

## Rationale
1. **Single source of interpretation.** If Projection interprets data, M3 Auditor will either duplicate the interpretation (semantic duplication) or override it (conflicting judgment sources). One system, one interpreter.
2. **Replay guarantee.** Projection must produce identical output from identical input. Interpretation is contextual (depends on domain knowledge, current priorities, human judgment) and therefore non-deterministic by nature.
3. **Upstream immutability.** Projection reads traces; it does not modify them. If Projection added interpretation metadata to its output, downstream consumers (M2.1, M3) would have two competing narratives: "what happened" (traces) vs "what it means" (projection interpretation).
4. **Precedent.** This follows the SQL VIEW pattern (derived, not authoritative), Kubernetes controllers (observe state, don't interpret it), and event sourcing (projections are read models, not decision models).

## Consequences
- Projection output is purely structural: timeline, counts, trends (via math, not judgment).
- M2.1 Diagnostics and M3 Auditor consume projection data as raw input, never as pre-interpreted guidance.
- Any "smart dashboard" must be built as a consumer of M2.1 diagnostics, not as part of M2.

## Alternatives Considered
- **Smart Projection:** Projection analyzes trends and flags concerns. Rejected: semantic creep, breaks replay determinism, creates competing interpretation sources.
- **No Projection:** Skip M2, go directly to Auditor. Rejected: Auditor would have to build its own views from raw traces, duplicating projection logic and creating tight coupling to trace format.
