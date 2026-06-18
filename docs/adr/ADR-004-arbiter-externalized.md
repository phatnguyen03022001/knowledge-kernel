# ADR-004: Arbiter is externalized from the data pipeline

## Status
Accepted (2026-06-18)

## Context
The Arbiter (M4, not yet implemented) resolves domain ownership disputes when primary and secondary domain owners disagree. The design question: should Arbiter be embedded in the validation pipeline (called by Validator on L3 violations), or should it be an external service triggered by escalation events?

## Decision
Arbiter is **completely externalized from the data pipeline.** It communicates only through events: it receives `escalation.created` events and emits `escalation.resolved` events. It is never called directly by Validator, Projection, Tracer, or Diagnostics. It has no import dependency in any upstream layer.

## Rationale
1. **Pipeline isolation.** If Arbiter is embedded in Validator, a slow or deadlocked Arbiter blocks the entire validation pipeline. Externalized, the pipeline continues while Arbiter resolves asynchronously.
2. **Separation of data vs policy.** The M1→M2.1 pipeline is a data plane (deterministic, one-way). Arbiter is a control plane (judgment, two-way communication). Mixing them creates the exact god-object the Guardian decomposition was designed to prevent.
3. **Testability.** An externalized Arbiter can be tested in isolation with synthetic escalation events. An embedded Arbiter requires full pipeline setup to test a single resolution path.
4. **Event-sourced decisions.** Arbiter decisions are first-class immutable events (`escalation.resolved`). This creates an audit trail of governance decisions, satisfying E-INV-002 (event causality) and enabling full replay of governance actions.
5. **Precedent.** This follows the Kubernetes scheduler pattern (separate control loop, communicates via API server), etcd's leader election (external to the Raft log), and Git's merge resolution (human-in-the-loop, external to the commit DAG).

## Consequences
- Arbiter is the LAST layer built (M4), because it depends on escalation events from M2.1 Diagnostics and M3 Auditor.
- Validator MUST NEVER call Arbiter. This is enforced by the layer isolation contract test.
- Arbiter's only system interface is: read escalation event → produce resolution event. It has no filesystem access beyond the event store.
- If Arbiter is unavailable, the data pipeline continues operating. Escalations accumulate as open events until Arbiter processes them.

## Alternatives Considered
- **Embedded Arbiter:** Validator calls Arbiter on L3 governance rule violations. Rejected: couples pipeline availability to Arbiter availability, creates circular dependency (Arbiter needs Validator output, Validator needs Arbiter decision).
- **No Arbiter:** Let domain disputes remain unresolved. Rejected: violates correction convergence (GR-POL-001) and creates indefinite BLOCKED STATE for unowned domains.
- **Validator-as-Arbiter:** Validator resolves simple disputes automatically. Rejected: Validator becomes a god-object with both enforcement and resolution authority — exactly the anti-pattern the 3-tier governance model was designed to prevent.
