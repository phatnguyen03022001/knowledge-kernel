# Structure Log

> Decision log for structure choices, rationale for selections/rejections, counterarguments from all sources.

---

## 2026-06-18

### Decision 1: Root name is `knowledge-os/`

| Field | Value |
|--------|---------|
| **Selected** | `knowledge-os/` |
| **Rejected** | `docs/` |
| **Rationale** | The name clearly states intent. `docs/` is too ambiguous |
| **Counterargument** | Could be seen as "overambitious" for a system not yet at scale |

**Source:** GPT#1, DS Pro (used knowledge-os). GPT#3 (proposed docs).

---

### Decision 2: ACP Packs under `governance/acp-packs/`

| Field | Value |
|--------|---------|
| **Selected** | `governance/acp-packs/` |
| **Rejected** | `operations/acp-packs/` (DS Pro) |
| **Rationale** | Governance and tools are tightly coupled. Separating them creates an implicit contract. V1 should keep them together |
| **Counterargument** | If packs > 15-20, separate them again |
| **Confidence** | ~70% |

**Source:** DS Pro (separate), GPT#3 (group under governance).

---

### Decision 3: Add `knowledge/inbox/`

| Field | Value |
|--------|---------|
| **Selected** | Include `inbox/` |
| **Rejected** | System without inbox |
| **Rationale** | Landing zone for new knowledge, prevents scattered debris |
| **Counterargument** | Inbox could become a dumping ground if not processed promptly |
| **Source** | Zettelkasten. Not present in the 3 original GPT/DS files |

---

### Decision 4: Post-hoc research classification

| Field | Value |
|--------|---------|
| **Selected** | `active/`, `abandoned/`, `superseded/`, `refuted/` |
| **Rejected** | `research/tracking/` (manual log), `candidate/` (virtual state) |
| **Rationale** | Folders make status immediately visible. `refuted/` must be separate because it's dangerous garbage |
| **Confidence** | ~85% |

**Source:** GPT (active+archived), Claude (split archived into 3 types).

---

### Decision 5: SSOT lifecycle via frontmatter

| Field | Value |
|--------|---------|
| **Selected** | Frontmatter: `status`, `last-reviewed`, `review-by`, `sources`, `version`, `owner` |
| **Rejected** | `ssot/validation/`, `governance/review-schedule.md` |
| **Rationale** | Metadata travels with the file, is queryable, cannot be separated |
| **Confidence** | ~90% |

**Source:** GPT (round 2).

---

### Decision 6: Provenance is the biggest lever

| Field | Value |
|--------|---------|
| **Selected** | Rule: "No content is canonical unless it resides in an SSOT with `sources`" |
| **Rationale** | Solves multiple problems simultaneously: stale research, provenance, orphans, duplicates |
| **Confidence** | ~90% |

**Source:** GPT (round 2, MVP).

---

### Decision 7: Orphan detection — 2-layer linking

| Field | Value |
|--------|---------|
| **Selected** | `links:` (dependency graph) + `sources:` (provenance) in frontmatter |
| **Rejected** | Plain markdown links (lack semantics), only sources (misses orphans) |
| **Orphan definition** | `incoming_links = 0 AND not in root index` |
| **Enforce** | Script `knowledge-os validate-graph` (CI/local) |
| **Still missing** | Dead links not handled. Who implements the script? |
| **Confidence** | ~75%. `links:` must also be maintained manually — could become garbage |

**Source:** GPT (round 3), Claude (filter: warn dead links, maintain manually).

---

### Decision 8: Duplicate detection — Concept Registry

| Field | Value |
|--------|---------|
| **Selected** | `foundation/concept-registry.yaml` — single owner per concept |
| **Rule** | One concept, one owner. Conflict → reject |
| **Enforce** | CI check: new SSOT must register concept first |
| **Still missing** | Who maintains the registry? Overlapping concepts? Cleanup when SSOT deprecated? |
| **Confidence** | ~70% |

**Source:** GPT (round 3), Claude (filter: operational cost, overlapping).

---

### Decision 9: Correction loop

| Field | Value |
|--------|---------|
| **Selected** | `governance/corrections/` — correction event log |
| **Rule** | SSOT is never directly overwritten. All changes go through correction events |
| **SSOT states** | `active` → `deprecated` → `superseded` |
| **Enforce** | CI: if SSOT content changes without a correction event → fail |
| **Template** | Event file: date, affects, type, source, status, rationale |
| **Still missing** | Who can create correction events? Rollback if research is wrong? |
| **Confidence** | ~80%. Needs governance layer behind it. |

**Source:** GPT (round 3). Claude (filter: rollback, permissions).

---

### Decision 10: Governance model (3-tier)

| Field | Value |
|--------|---------|
| **Selected** | 3-tier: Authors, Domain Owners, System Guardian |
| **Rationale** | All 3 mechanisms (orphan, registry, correction) die without an accountability anchor |
| **Closure loop** | Detection → Proposal → Decision → Execution → Validation |
| **Authors** | Maintain SSOT, links. Implement corrections |
| **Domain Owners** | Resolve semantic conflicts. Approve corrections. Arbitrate concept overlap |
| **System Guardian** | Detect orphans, broken links. Enforce registry consistency, correction linkage |
| **Confidence** | ~85% |

**Source:** GPT (round 4).

---

### Decision 11: Domain model

| Field | Value |
|--------|---------|
| **Selected** | 3 domains: **Structural**, **Pedagogical**, **Evaluation** |
| **Definition** | Domain = zone of responsibility for right/wrong decisions, not a topic |
| **Overlap** | Is the default, not a bug. Resolved via primary + secondary ownership |
| **Primary** | Decides definition correctness |
| **Secondary** | Consultation, no veto — for structural/pedagogy/evaluation interpretation |
| **Example** | skill-graph.md: primary=evaluation, secondary=[structural, pedagogical] |
| **Confidence** | ~80%. Domain boundaries need refinement in practice |

**Source:** GPT (round 5). Overlap handling is a key insight.

---

### Decision 12: Bootstrap 3-phase

| Field | Value |
|--------|---------|
| **Selected** | 3 phases: Seed → Domain Assignment → Distributed |
| **Phase 0 (Day 0)** | Single seed owner. Define domains, assign owners, approve first SSOT |
| **Phase 1 (Day 1–7)** | Domain owners begin operating. Seed creates domain registry |
| **Phase 2 (Day 7+)** | Seed becomes observer. Domain owners govern, system enforces |
| **Rule** | Domain owner CANNOT self-assign |
| **Insight** | "Domain boundaries don't exist before governance. They are birthed by bootstrap." |
| **Confidence** | ~85%. This is a real problem in every system, pragmatic solution |

**Source:** GPT (round 5). Assessed as the hardest phase.

---

### Decision 13: ACP is executable governance procedure

| Field | Value |
|--------|---------|
| **Selected** | ACP pack = executable governance procedure (not static config) |
| **Lifecycle** | propose → validate → execute → audit |
| **Who creates** | Phase 0–1: Seed owner. Phase 2: Domain owners (within their domain) |
| **Nature** | Similar to GitHub Actions / DB migrations / policy-as-code |
| **Confidence** | ~75%. Needs concrete spec for pack format and execution engine |

**Source:** GPT (round 5).

---

## Confidence Summary

| Decision | Score | Main risk |
|-----------|-------|-------------|
| Root name | ~85% | Overambitious-sounding |
| ACP in governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research classification | ~85% | — |
| SSOT frontmatter | ~90% | Migrating old files |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` manually maintained |
| Concept registry | ~70% | Operational cost |
| Correction loop | ~80% | Governance behind it |
| Governance 3-tier | ~85% | Domain owner not fulfilling role |
| Domain model | ~80% | Boundaries need refinement |
| Bootstrap | ~85% | Seed owner chosen wrong |
| ACP executable | ~75% | Needs execution spec |

---

### Decision 14: Inbox anti-death (TTL + WIP + sink)

| Field | Value |
|--------|---------|
| **Selected** | Inbox TTL 7 days, WIP limit 20, mandatory outcome (promote/convert/discard) |
| **Rejected** | Inbox as unconstrained folder |
| **Rationale** | Inbox dies without a throughput guarantee. Needs a forcing function to push items forward |
| **Anti-pattern** | If inbox unprocessed → system auto-generates stagnation report |
| **Confidence** | ~80%. Specific numbers (7 days, 20 items) need refinement in practice |

**Source:** GPT (round 6 — anti-death layer).

---

### Decision 15: Correction anti-death (3-tier + batch + cap)

| Field | Value |
|--------|---------|
| **Selected** | 3-tier correction system: L1 auto-merge, L2 domain review, L3 multi-domain |
| **Rejected** | Every correction through domain owner (bottleneck) |
| **Cycle** | Review every 48h, cap 20 per domain per cycle |
| **Excess** | Deferred queue |
| **Rationale** | Correction log explosion is a decision bottleneck at the domain owner, not a volume problem |
| **Confidence** | ~80%. L1/L2/L3 boundaries need refinement |

**Source:** GPT (round 6).

---

### Decision 16: Seed owner anti-death (expiring authority)

| Field | Value |
|--------|---------|
| **Selected** | Seed owner: TTL 30 days, auto-loses write permission |
| **Rejected** | Seed owner "can leave" but no enforcement mechanism |
| **Domain creation** | Seed cannot create new domains after Day 7. Domain creation → domain proposal + council approval |
| **Orphan domain** | System auto-detects domain without owner → BLOCKED STATE |
| **Rationale** | Seed owner is unresolved authority residue. Must be gradually deprecated by design |
| **Confidence** | ~85%. Realistic for small systems |

**Source:** GPT (round 6).

---

## Confidence Summary (expanded)

| Decision | Score | Main risk |
|-----------|-------|-------------|
| Root name | ~85% | Overambitious-sounding |
| ACP in governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research classification | ~85% | — |
| SSOT frontmatter | ~90% | Migrating old files |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` manually maintained |
| Concept registry | ~70% | Operational cost |
| Correction loop | ~80% | Governance behind it |
| Governance 3-tier | ~85% | Domain owner not fulfilling role |
| Domain model | ~80% | Boundaries need refinement |
| Bootstrap | ~85% | Seed owner chosen wrong |
| ACP executable | ~75% | Needs execution spec |
| **Inbox anti-death** | **~80%** | Specific numbers need refinement |
| **Correction tiering** | **~80%** | L1/L2/L3 boundaries |
| **Seed expiry** | **~85%** | Realistic for small systems |

---

### Decision 17: ACP execution runtime spec

| Field | Value |
|--------|---------|
| **Selected** | ACP = declarative execution contract + permission-bound action unit |
| **Format** | YAML: id, trigger, context, inputs, permissions, execution steps, outputs, rollback, audit |
| **Engine** | Loader → Context Builder → Permission Checker → Step Executor → State Writer → Audit Logger |
| **Critical rule** | AI proposes execution plan. Execution engine commits. ACP must not autonomously change anything outside its execution boundary |
| **Confidence** | ~80%. Needs reference implementation (~250 lines Python) |

**Source:** GPT (round 7 — runtime spec).

---

### Decision 18: System health metrics (4 vital signs)

| Field | Value |
|--------|---------|
| **Selected** | 4 metrics: inbox health, correction health, graph health, governance health |
| **Composite** | 40% graph + 30% correction + 20% inbox + 10% governance |
| **Dead detection** | orphan_rate > 10% OR correction backlog > threshold OR inbox stagnant > 7 days → DEGRADED |
| **Dashboard** | Minimal YAML spec: score, status, 4 metrics |
| **Confidence** | ~85%. Weights can be refined later |

**Source:** GPT (round 7).

---

### Decision 19: Conflict resolution protocol

| Field | Value |
|--------|---------|
| **Selected** | Hierarchical override with escalation. Primary domain wins by default |
| **Rejected** | Voting, consensus, peer-to-peer resolution (leads to deadlock) |
| **Secondary** | Cannot block directly. Only escalate to System Guardian |
| **System Guardian** | Final arbiter |
| **Rule** | No peer-to-peer resolution at governance level |
| **Confidence** | ~85%. Simple, avoids deadlock |

**Source:** GPT (round 7).

---

### Decision 20: Final system architecture

| Field | Value |
|--------|---------|
| **Flow** | AI propose → ACP Engine validate → Domain Owner approve → System Guardian enforce → State update → Audit log |
| **Confidence** | ~85%. This is the final summary of the entire system design |

**Source:** GPT (round 7).

---

## Confidence Summary (final)

| Decision | Score | Main risk |
|-----------|-------|-------------|
| Root name | ~85% | Overambitious-sounding |
| ACP in governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research classification | ~85% | — |
| SSOT frontmatter | ~90% | Migrating old files |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` manually maintained |
| Concept registry | ~70% | Operational cost |
| Correction loop | ~80% | Governance behind it |
| Governance 3-tier | ~85% | Domain owner not fulfilling role |
| Domain model | ~80% | Boundaries need refinement |
| Bootstrap | ~85% | Seed owner chosen wrong |
| ACP executable | ~75% | Needs execution spec |
| Inbox anti-death | ~80% | Specific numbers need refinement |
| Correction tiering | ~80% | L1/L2/L3 boundaries |
| Seed expiry | ~85% | Realistic for small systems |
| **ACP runtime** | **~80%** | Needs reference implementation |
| **Health metrics** | **~85%** | Weights can be refined |
| **Conflict resolution** | **~85%** | — |
| **Final architecture** | **~85%** | — |
| **ACP runner impl** | **~100%** | Step registry real, atomic write, event emission, permission token, validator, retry/skip |
| **Event Bus** | **~95%** | Subscription loader, event matcher, sequential scheduler, listen mode, manual mode |
| **End-to-end chain** | **~95%** | correction.approved → update-ssot → ssot.updated → validate-graph + refresh-health |
| **Test harness** | **~100%** | 3/3 PASS, YAML scenario format |
| **Infrastructure deferral** | **~95%** | Adapter-layer invariant confirmed — no premature scaling |
| **Phase 2 build plan** | **~90%** | Dependency-driven order, no GPT needed — Phase 1 spec is complete |
| **Phase 2.0 hardening** | **~92%** | Invariants → contracts → chaos tests before implementation |

---

### Decision 21: System is a knowledge kernel, not a product platform

| Field | Value |
|--------|---------|
| **Vision** | Event-sourced, governance-bound, AI-executable knowledge kernel |
| **Achieved** | Runtime governance kernel (SSOT + governance + ACP + audit) |
| **Not yet achieved** | Product platform — needs 3-layer separation |
| **Confidence** | ~90% |

**Source:** GPT (round 8 — final stress test).

---

### Decision 22: 3-layer separation (core / adapters / plugins)

| Field | Value |
|--------|---------|
| **Core kernel** | Knowledge model, governance model, execution model, graph model — platform-agnostic invariants |
| **Runtime adapters** | file-system (dev), postgresql (scale), cloud-api (distributed) |
| **Plugin layer** | AI agents, UI, B2B/B2C governance profiles, CI integrations |
| **Rule** | Keep core pure. Push all implementation bias down to adapters |
| **Confidence** | ~85% |

**Source:** GPT (round 8).

---

### Decision 23: Missing OS layer — Event bus / IPC

| Field | Value |
|--------|---------|
| **Problem** | Has processes (ACP), memory (SSOT), governance (domain) — missing event-driven coordination |
| **Solution** | ACP trigger field extended: `trigger.type: event`, `trigger.event: correction.created` |
| **Significance** | ACP executions = IPC for knowledge OS. Packs communicate via events |
| **Confidence** | ~80%. Needs design spec before implementation |

**Source:** GPT (round 8).

---

### Decision 24: 3 deployment modes — same kernel

| Field | Value |
|--------|---------|
| **Dev** | File + YAML + Git + local Python |
| **Scale** | PostgreSQL + server |
| **Cloud** | Distributed + async ACP engine |
| **Invariant** | ACP + SSOT + correction loop = event-sourced immutable model. Migration doesn't break design |
| **Confidence** | ~85% |

**Source:** GPT (round 8).

---

### Decision 25: B2B vs B2C — same kernel, different policy + exposure

| Field | Value |
|--------|---------|
| **Kernel** | Shared (SSOT, governance, ACP, audit) |
| **B2B** | Strict governance, full audit, exposed correction loop, explicit domain ownership |
| **B2C** | Hidden governance, partial audit, internal correction, abstracted domain |
| **UX layer** | B2B: irrelevant. B2C: critical |
| **Confidence** | ~90%. This is a solid architectural insight |

**Source:** GPT (round 8).

---

### Decision 26: Event Bus is a separate kernel component

| Field | Value |
|--------|---------|
| **Selected** | Event Bus = first-class kernel component, not part of ACP |
| **Rationale** | ACP = execution unit, Event Bus = coordination layer. Two different abstractions |
| **Format** | Envelope: id, type, timestamp, source, payload, metadata (correlation_id, causation_id) |
| **Subscription** | Declarative YAML: `governance/subscriptions/` — event → handler mapping |
| **Replay** | `knowledge-os replay --from evt-001 --to evt-050`, event store append-only |
| **Dev mode** | File-based: `runtime/event-store/YYYY/MM/DD/evt-NNN.yaml` + queue/pending/ |
| **Confidence** | ~90% |

**Source:** GPT (round 9 — self-review). This is the most important missing piece.

---

### Decision 27: Guardian decomposition

| Field | Value |
|--------|---------|
| **Selected** | "Dissolve" System Guardian into 3 services: Validator, Auditor, Arbiter |
| **Rejected** | System Guardian god-object (overloaded: CI, audit, and arbitration all in one) |
| **Validator** | Automatic enforcement — schema, graph, orphan, link, ownership. Returns valid: true/false |
| **Auditor** | Observation — audit logs, metrics, health dashboard, stagnation reports. Doesn't block, doesn't approve |
| **Arbiter** | Escalation only — resolve domain conflicts. Not on the happy path |
| **Directory** | No governance/guardian/ directory. Validator/Auditor/Arbiter are runtime services, not knowledge objects |
| **Confidence** | ~95% |

**Source:** GPT (round 9 — self-review).

---

From a folder structure → an **event-sourced, governance-bound knowledge kernel** that can become a universal template for AI-native projects.

---

### Decision 28: 3-layer distribution (kernel / adapters / plugins)

| Field | Value |
|--------|---------|
| **Selected** | `knowledge-kernel/`: kernel/ + starter-packs/ + adapters/ + plugins/ + cli/ |
| **Rejected** | Template as "empty project" (conflates kernel evolution vs project evolution) |
| **Kernel** | Invariant. Required. Kernel-managed. Not directly editable |
| **Starter-packs** | Sample ACP packs. Customizable |
| **Adapters** | Swappable: filesystem (dev), postgres (scale), cloud (distributed) |
| **Plugins** | Optional: ai-agent, dashboard, github-actions, b2b, b2c |
| **Confidence** | ~90% |

**Source:** GPT (round 10 — packaging).

---

### Decision 29: ACP spec is core, ACP packs are starter content

| Field | Value |
|--------|---------|
| **Core** | `kernel/foundation/pack-schema.yaml` — defines pack format |
| **Starter** | `starter-packs/update-ssot.yaml` — concrete implementation |
| **Analogous to** | Kubernetes API (core) vs Deployment.yaml (template content) |
| **Confidence** | ~95% |

**Source:** GPT (round 10).

---

### Decision 30: Kernel-managed vs Project-owned

| Field | Value |
|--------|---------|
| **Managed-by header** | `managed-by: knowledge-kernel`, `managed-version: 1.0.0` |
| **Kernel-managed** | `kernel/foundation/*`, `kernel/governance/*`, `kernel/runtime/*` |
| **Project-owned** | `knowledge/*`, `archive/*`, `corrections/*` |
| **Upgrade** | `knowledge-os upgrade` → only updates kernel-managed files, does not touch project content |
| **Init** | `knowledge-os init my-project` → generate project structure + `.knowledge-os/` manifest |
| **Confidence** | ~90% |

**Source:** GPT (round 10).

---

### Decision 31: Spec additions (Projection, DAG, DLQ, Idempotency)

| Field | Value |
|--------|---------|
| **Projection** | Event Store → Projection Builder → Current State. Snapshot 100 events/24h. V1: concept-registry, ownership-registry, graph-health |
| **ACP DAG** | `execution.graph` YAML format. Topological order. Dependency failed → downstream skipped. V1 single-thread |
| **DLQ** | `runtime/event-bus/dlq/`. Retry 3 → DLQ. Manual reprocess only |
| **Idempotency** | At-Least-Once. `event_id + handler_id` → processed registry. Packs must be idempotent |
| **Confidence** | ~95% |

**Source:** GPT (round 11 — final).

---

### Decision 32: Test harness

| Field | Value |
|--------|---------|
| **Selected** | `tests/harness.py` + `tests/scenarios/*.yaml` |
| **Format** | YAML scenario: steps (run_pack, run_event_bus) + expectations (events, audit_logs, packs_executed, processed_count) |
| **V1 scenarios** | update-ssot-flow, validate-graph-only, refresh-health-only |
| **Result** | 3/3 PASS |

---

### Decision 33: No etcd/Kafka in Phase 1 — adapter-layer invariant

| Field | Value |
|--------|---------|
| **Selected** | Defer etcd/Kafka to Phase 2 (PostgreSQL) and Phase 3 (Kafka-class). Phase 1 stays on file-system + Git |
| **Rejected** | Preemptively adopting distributed infrastructure (etcd/Kafka) for a single-dev bootstrap |
| **Rationale** | File + YAML + Git provides sufficient consistency (SHA-commit chain), durability (append-only YAML), and replay for a single operator. The trap to avoid: building infrastructure for scale before having a second user. The 3-layer adapter architecture already isolates storage backend from kernel — migration path is designed, not retrofitted |
| **Current equivalents** | Git = strong consistency (like etcd Raft). Append-only event-store/ = durable log (like Kafka). Single-thread scheduler = coordination (like leader election, but only 1 node exists) |
| **Migration path** | `adapters/file-system/` → `adapters/postgresql/` (Phase 2, multi-writer) → `adapters/cloud-api/` (Phase 3, multi-tenant). Invariant preserved: ACP + SSOT + correction loop remain event-sourced immutable regardless of backend |
| **Confidence** | ~95%. Protocol is storage-agnostic by design — no hardcoded file-system assumptions in Event Bus envelope, subscription registry, or replay strategy |

**Source:** Claude (post-Phase-1 architecture review).

---

## End of Phase 1

Total: **33 decisions** across **11 GPT rounds + Claude filtering + 1 post-review**.

```text
Stage 1 (rounds 1-3):   Structure + anti-garbage mechanisms
Stage 2 (rounds 4-5):   Governance + domain + bootstrap
Stage 3 (round 6):      Anti-death constraints
Stage 4 (round 7):      ACP runtime + metrics + conflict resolution
Stage 5 (round 8):      Platform architecture + standalone template vision
Stage 6 (round 9):      Event Bus + Guardian decomposition
Stage 7 (round 10):     Kernel distribution packaging
Stage 8 (round 11):     Final spec (Projection, DAG, DLQ, Idempotency) + Test harness
Stage 9 (post-review):  Infrastructure deferral — adapter-layer invariant confirmed
```

From a folder structure → an **event-sourced, governance-bound knowledge kernel** that can become a universal template for AI-native projects.

### Final Principle

> **Kernel owns behavior. Project owns knowledge.**
>
> Template contains only what defines how the system operates.
> Project contains only what the system operates on.

---

## Phase 2 Plan — Domain Bootstrap

> Goal: build the remaining kernel runtime so domain owners can begin operating.
> Timeline: Day 1–7 of bootstrap.
> Principle: build in dependency order — each milestone unlocks the next.

### Dependency chain

```text
Validator ──→ Projection ──→ Health Dashboard
    │                              │
    └──→ Correction Loop ──────────┘
              │
              └──→ Auditor ──→ Arbiter (escalation only)
```

### M1: Validator (Day 1–2)

**The foundation.** Every other component needs to know: "is this state valid?"

| What | Details |
|------|---------|
| **File** | `kernel/runtime/validator.py` (~300 lines) |
| **Checks** | schema validation, graph validation (orphan detection), link validation (broken links), ownership validation (domain owner exists), registry consistency |
| **Interface** | `validate(target, rules) → {valid: bool, violations: [...]}` |
| **Rules source** | `kernel/foundation/validator-rules.yaml` |
| **Depends on** | `concept-registry.yaml` (ownership), `event-schema.yaml` (schema) |
| **Acceptance** | All 5 check types pass against current `runtime/` state. Introducing a deliberate orphan → caught. Broken link → caught. Schema violation → caught |
| **Test scenarios** | validate-graph-only (exists), validate-schema-broken (new), validate-orphan-detected (new), validate-ownership-missing (new) |

### M2: Projection Layer (Day 2–3)

**Materialized views.** Event Store is append-only. Projections give queryable current state.

| What | Details |
|------|---------|
| **File** | `kernel/runtime/projection.py` (~250 lines) |
| **Projections** | `concept-registry` (from events + concept-registry.yaml), `ownership-registry` (who owns what), `graph-health` (orphan count, broken links, link density) |
| **Modes** | Full Replay (rebuild from event-store), Incremental (from last_processed_event) |
| **Snapshot** | Every 100 events or 24h → `runtime/snapshots/` |
| **Depends on** | M1 Validator (runs validation before projection commit), `runtime/event-store/` |
| **Acceptance** | `concept-registry` projection matches `concept-registry.yaml` source. `graph-health` projection updates after `validate-graph` event. Rebuild from scratch yields identical result |
| **Test scenarios** | projection-full-replay (new), projection-incremental (new), projection-snapshot (new) |

### M3: Correction Loop (Day 3–4)

**The governance mechanism.** Every SSOT change must pass through correction event → domain owner approval → apply → closure.

| What | Details |
|------|---------|
| **File** | `kernel/runtime/correction.py` (~350 lines) |
| **Flow** | `propose → validate (M1) → domain_owner_approve → apply_patch → update_metadata → close` |
| **Tiering** | L1 auto-merge (typo, link fix, metadata), L2 domain review (content change), L3 multi-domain arbitration (conflict between primary/secondary) |
| **Enforcement** | CI check: SSOT content changed without correction event → fail |
| **Depends on** | M1 Validator, ACP Runner (for apply_patch step), `governance/corrections/` |
| **Acceptance** | L1 correction auto-applied without human. L2 correction waits for domain owner approval token. Correction applied → SSOT updated → correction status = closed |
| **Test scenarios** | correction-l1-auto-merge (new), correction-l2-domain-review (new), correction-l3-multi-domain (new), correction-reject-invalid (new) |

### M4: Health Dashboard (Day 4–5)

**System observability.** Composite heartbeat score from 4 vital signs.

| What | Details |
|------|---------|
| **File** | `kernel/runtime/health.py` (~200 lines) |
| **Metrics** | inbox_health (avg_age, % > TTL), correction_health (open_count, avg_resolution_time), graph_health (orphan_count, broken_links), governance_health (domains_without_owner, stale_corrections) |
| **Composite** | `score = 0.4*graph + 0.3*correction + 0.2*inbox + 0.1*governance` |
| **Dead detection** | orphan_rate > 10% OR correction_backlog > threshold OR inbox_stagnant > 7 days → DEGRADED |
| **Output** | `runtime/reports/latest-health.yaml` (auto-refreshed) |
| **Depends on** | M2 Projection (reads graph-health, concept-registry projections), M3 Correction Loop (correction stats) |
| **Acceptance** | Healthy system → score >= 80. Introduce 5 orphans → score drops, status = DEGRADED. Clear orphans → score recovers |
| **Test scenarios** | health-score-healthy (new), health-score-degraded (new), health-dead-detection (new) |

### M5: Auditor (Day 5–6)

**Passive observation.** Does not block, does not approve. Only records.

| What | Details |
|------|---------|
| **File** | `kernel/runtime/auditor.py` (~200 lines) |
| **Reports** | stagnation report (inbox unprocessed > threshold), compliance report (all SSOT have review-by dates, all domains have owners), audit trail (every state mutation logged) |
| **Output** | `audit_logs/` (stagnation, compliance, mutation) |
| **Depends on** | M4 Health Dashboard (triggers on DEGRADED state), M2 Projection (reads current state) |
| **Acceptance** | Inbox untouched for 8 days → stagnation report auto-generated. Domain missing owner → compliance report flags it. Every ACP execution → audit trail entry |
| **Test scenarios** | auditor-stagnation-report (new), auditor-compliance-missing-owner (new), auditor-audit-trail (new) |

### M6: Arbiter (Day 6–7)

**Escalation only.** Resolves domain conflicts. Not on the happy path.

| What | Details |
|------|---------|
| **File** | `kernel/runtime/arbiter.py` (~150 lines) |
| **Trigger** | Escalation event from M3 Correction Loop (L3 multi-domain conflict) |
| **Resolution** | Primary domain wins by default. Secondary can escalate with rationale. Arbiter reviews both positions → final decision binding |
| **Rules source** | `governance/escalation-policy.yaml` |
| **Depends on** | M3 Correction Loop (L3 tiering) |
| **Acceptance** | Primary + Secondary disagree → escalation event → Arbiter resolves → decision recorded. Arbiter decision is final (no appeal loop). Happy path executions never invoke Arbiter |
| **Test scenarios** | arbiter-resolve-conflict (new), arbiter-primary-wins-default (new), arbiter-no-escalation-on-happy-path (new) |

### Phase 2 completion criteria

| Criterion | Threshold |
|-----------|-----------|
| **All 6 milestones built** | M1–M6 code + tests |
| **Test coverage** | ≥ 20 test scenarios (from current 3) |
| **End-to-end chain** | correction.approved → update-ssot → validate-graph + refresh-health → health score updated → audit logged |
| **Domain owner can operate** | Approve/reject correction, view health dashboard, receive stagnation alerts |
| **No regression** | All Phase 1 tests still pass |

### What Phase 2 does NOT build

| Deferred to Phase 3 | Reason |
|---------------------|--------|
| Multi-tenant adapter (postgres/cloud) | Single-dev bootstrap doesn't need it |
| UI dashboard | CLI-first. Dashboard is plugin layer |
| B2B/B2C governance profiles | Not yet at multi-project scale |
| Exactly-once delivery | At-Least-Once + idempotency sufficient for V2 |
| Worker pool / parallel execution | Single-thread ACP runner handles Phase 2 load |

---

### Decision 34: Phase 2 build plan — build Validator first, no GPT needed

| Field | Value |
|--------|---------|
| **Selected** | Self-build Phase 2 from existing Phase 1 spec. No additional GPT rounds |
| **Rejected** | More GPT design rounds (risk: analysis paralysis, design-by-committee) |
| **Order** | Validator → Projection → Correction Loop → Health Dashboard → Auditor → Arbiter (dependency-driven) |
| **Rationale** | Phase 1 already has 33 decisions across 11 GPT rounds. The spec is complete — what's missing is code, not design. GPT doesn't know the current codebase (acp_runner.py 1477 lines, acp_event_bus.py 872 lines) well enough to give implementation-level guidance |
| **Confidence** | ~90% |
| **Estimated effort** | ~1450 lines Python + ~17 test scenarios |

**Source:** Claude (Phase 1 retrospective + Phase 2 planning).

---

### Decision 35: Phase 2.0 Hardening — invariants before implementation

| Field | Value |
|--------|---------|
| **Selected** | Insert Phase 2.0 hardening step before M1 Validator. Write invariants → contracts → chaos tests → then document. No implementation may introduce a new invariant not declared in Phase 2.0 |
| **Rejected** | Starting M1 Validator code immediately without hardened constraints |
| **Rationale** | External architecture review identified 3 risks: (1) Correction Loop is a "mini-OS" — 350 LOC optimistic without formal constraints, (2) Projection consistency model undefined, (3) Arbiter lacks formal tie-break strategy. The hardening step addresses all three by committing invariants first, then deriving contracts, then validating with chaos tests — before any implementation code |
| **Artifacts committed** | `kernel/foundation/validator-invariants.yaml` (13 invariants across 4 tiers + 7 failure modes + 5 chaos contracts), `kernel/foundation/validator-contract.yaml` (input/output boundary + error model + retry semantics + integration points), `tests/scenarios/chaos-validator-kill.yaml`, `tests/scenarios/chaos-invalid-graph.yaml`, `tests/scenarios/chaos-cold-start.yaml` |
| **Meta-rule** | No implementation may introduce a new invariant not declared in validator-invariants.yaml. This prevents implicit behavior creep, hidden logic, and future god-object drift |
| **Ordering principle** | Invariants are "physics of the system" — they come before contracts, code, and documentation. Decision log records what was constrained, not what was planned |
| **Confidence** | ~92%. The constraint-first approach is standard in systems like etcd (Raft invariants before implementation) and Kafka (log consistency model before broker code) |

**Source:** Claude + external architecture review (2026-06-18).

**v1.2 refinement (2026-06-18):** Third review identified 3 runtime conflicts that spec would hit:
1. Ownership conflated semantic authority (SA) with write authority (WA). Fixed: SA = primary domain owner decides "what concept means." WA = anyone can propose corrections. Arbiter resolves SA disputes but does NOT hold SA. Arbiter can temporarily route WA if domain owner unresponsive > 48h.
2. "Correction links to SSOT" ambiguous — state or event? Fixed: SSOT defined as 3 representations (Concept = logical path, State = file on disk, Event = immutable record). Correction.affects → SSOT Concept. Correction application → updates State. Correction record → new Event (append-only).
3. GR-POL-001 convergence undefined — mini-consensus algorithm without rules. Fixed: concrete convergence rule — timeout (48h) + max attempts (3) + mandatory Arbiter action. Arbiter cannot "do nothing." If Arbiter doesn't act → System Guardian escalates to Seed/Council.

**Source:** Claude + second external architecture review (2026-06-18).
