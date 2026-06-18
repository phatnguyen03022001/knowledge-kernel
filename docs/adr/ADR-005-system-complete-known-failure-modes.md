# ADR-005: Architecture is closed — known failure modes documented

## Status
Accepted (2026-06-18)

## Context
The 6-layer pipeline (M1→M2.1→M3→M4) is built, verified, and locked. All layers have deterministic contracts. The system can detect violations, normalize them, evaluate policy, and route actions — all without semantic drift between layers.

The question: is the architecture "done"? And if so, what are its failure modes?

## Decision
The architecture is **closed** — no new layers are needed to complete the design. However, the system is explicitly vulnerable to 3 failure modes that emerge over time, not at design time. These are documented as anti-patterns in `kernel/contracts/system-contract.yaml` §8.

## The 3 failure modes

### FM-ARCH-001: Policy Drift
As M3 policy files grow, Auditor gradually becomes a hidden reasoning engine. New policies add "context-aware" rules beyond simple category + threshold matching.

**Prevention:** Every M3 policy must be expressible as `category + threshold + action`. Anything requiring cross-category reasoning belongs in a new M1 invariant, not an M3 policy.

### FM-ARCH-002: Routing Explosion
As M4 action types multiply, Arbiter becomes a mini-orchestrator. New actions → new routing rules → rules interact → emergent governance behavior.

**Prevention:** M4 has exactly 4 actions (NONE, MONITOR, BLOCK, ESCALATE). Adding a 5th requires an ADR + contract version bump.

### FM-ARCH-003: Coupling Creep
Features added to one layer create implicit dependencies on another layer's internal format. The strict isolation erodes silently — no single change breaks it, but the cumulative effect destroys the deterministic pipeline guarantee.

**Prevention:** Layer isolation test runs on every commit. Any cross-layer format dependency must be declared as an explicit interface in the system contract.

## Why this matters now
Most systems discover these failure modes 3–6 months into development, after layers have already coupled. By documenting them now — while the architecture is still clean — future maintainers can recognize the early warning signs before damage occurs.

## Consequences
- No M5 layer is needed or planned.
- Future work should focus on stress testing (policy explosion, adversarial input, scaling) rather than architecture expansion.
- The system contract is the single source of truth for what each layer may and may not do.
- Any violation of the failure mode prevention rules requires an ADR.

## Alternatives Considered
- **Keep building more layers (M5, M6).** Rejected: the 6-layer pipeline already covers detection → observation → projection → normalization → judgment → action. Adding more layers would fragment responsibility without adding capability.
- **Don't document failure modes (let them emerge).** Rejected: undocumented failure modes become "how the system actually works" — the worst kind of architecture drift.
