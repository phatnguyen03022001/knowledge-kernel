# ADR-003: Auditor MUST NOT create diagnostic ontology

## Status
Accepted (2026-06-18)

## Context
The Auditor (M3, not yet implemented) will be the first layer that interprets system state and produces human-readable judgments. The design question: should Auditor be allowed to create new diagnostic categories when it encounters patterns not covered by the existing 12-category ontology?

## Decision
Auditor **MUST NOT create, infer, or expand the diagnostic ontology.** The 12 categories defined in M2.1 are FROZEN. Auditor may only read and apply policy rules to existing categories. Any new category requires: (a) a new invariant in validator-invariants.yaml, (b) a new entry in the CATEGORY_MAP, (c) a version bump of system-contract.yaml, and (d) a decision log entry.

## Rationale
1. **Ontology stability.** If Auditor can create categories at runtime, the diagnostic vocabulary becomes unbounded. Two Auditors on two different sessions could produce different category sets for the same system state — destroying the determinism guarantee.
2. **Classification authority.** The invariant→category mapping is a 1:1 structural mapping. It is not a judgment. Auditor applies policy (e.g., "3 critical violations of type 'broken-reference' → DEGRADED"), which requires stable categories as input.
3. **Prevent semantic explosion.** The #1 failure mode of diagnostic systems is unbounded category growth. Each new Auditor version adds "one more category" until the taxonomy is unmanageable. Freezing at 12 forces discipline: every new category must justify its existence as a new invariant, not as a new interpretation of an existing invariant.
4. **Precedent.** This follows the SNMP MIB model (fixed OID tree), Prometheus metric naming (convention-enforced, not runtime-generated), and Kubernetes condition types (fixed set, extensible only via API versioning).

## Consequences
- Auditor is constrained to policy evaluation only: read categories → apply rules → produce report.
- The 12-category ontology must be reviewed when new invariants are added (Phase 3+).
- If Auditor encounters a genuinely new failure mode, it must flag it as "unclassified" and trigger the ontology expansion process (which is a design-time activity, not a runtime activity).

## Alternatives Considered
- **Dynamic Ontology:** Auditor creates new categories as it discovers patterns. Rejected: leads to semantic explosion, breaks determinism, makes cross-session comparison impossible.
- **Auditor-Owned Ontology:** Auditor maintains its own separate category system. Rejected: creates two competing taxonomies (M2.1 vs M3), forcing consumers to reconcile them.
