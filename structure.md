# Knowledge OS — Structure

> Canonical input structure (pre-phase). Always reflects consensus decisions.
> See `structure-log.md` for change history and counterarguments.
>
> **Vision:** Event-sourced, governance-bound, AI-executable knowledge kernel.
> Not a document system or project structure — but an operating system for AI-driven knowledge workflows.
> Can be extracted into a standalone template for AI-native projects (B2B, B2C, hybrid).

---

## Overall Flow

```
Foundation
    ↓
Governance
    └── ACP Packs
    └── Corrections
    ↓
Knowledge
    └── Inbox → Research → SSOT → Models → Schemas
    ↓
Archive
```

**Correction loop:**
```
New Research
    ↓
Proposal (correction event)
    ↓
Validation (domain owner)
    ↓
Implementation (SSOT author)
    ↓
Closure
```

---

## Governance model (3-tier)

Every mechanism in the system operates under 3 authority layers:

```
AUTHORS
    → maintain SSOT, links
    → implement corrections

DOMAIN OWNERS
    → resolve semantic conflicts
    → approve corrections
    → arbitrate concept overlap

SYSTEM GUARDIAN
    → detect orphan, broken links
    → enforce registry consistency
    → enforce correction linkage
```

### Core Principles

> Governance isn't about "who has power," but "who is forced to take responsibility when an invalid state exists."

### Accountability closure loop for every action

```
Detection (system)
    ↓
Proposal (anyone)
    ↓
Decision (domain owner)
    ↓
Execution (author)
    ↓
Validation (system)
```

---

## Domain model

Domains are not taxonomies (topic classification). A domain is a **zone of final decision responsibility for a class of questions**.

### 3 domains

| Domain | Answers the question | Example SSOT |
|--------|---------------------|------------|
| **Structural** | How is knowledge organized as a system? | product-vision, knowledge-model, dependency-map |
| **Pedagogical** | How do humans learn? | learning-science, pedagogy, skill-graph |
| **Evaluation** | How is correctness assessed? | assessment-model, mastery-model, difficulty-model |

### Primary + Secondary ownership

Domain overlap is the default, not a bug. An SSOT belonging to multiple domains is normal. Solution:

```yaml
primary-domain: evaluation          # decides "definition of correct/incorrect"
secondary-domains:                  # consultation, no veto power
  - structural
  - pedagogical
```

Rules:

| Decision type | Who decides |
|---------------|-------------|
| Definition correctness | Primary domain owner |
| Structural representation | Secondary (structural) |
| Pedagogy interpretation | Secondary (pedagogical) |

---

## Bootstrap — 3 phases

A cold-start system cannot have decentralized governance immediately. It needs bootstrapping authority.

### 🟢 Phase 0 — Seed Authority (Day 0)

1 single person (seed owner):
- Define domains
- Assign domain owners
- Approve first SSOT
- Initialize concept registry

> Domain owner CANNOT self-assign. Seed owner assigns.

### 🟡 Phase 1 — Domain Bootstrap (Day 1–7)

Seed owner creates:
```
domains:
  structural:   { owner: person-a }
  pedagogical:  { owner: person-b }
  evaluation:   { owner: person-c }
```

Domain owners begin operating: approve corrections, resolve concept overlap.

### 🔵 Phase 2 — Distributed Governance (Day 7+)

Seed owner transitions to observer / override authority (rare use).
- Domain owners govern
- System enforces
- Authors operate
- Seed only intervenes on system deadlock

> Every distributed system needs an "initial arbitrary authority" to create the first order.

---

## Anti-death constraints

> Governance systems don't die from bad design. They die from lacking mechanisms that force progress to keep moving.

4 layers of collapse prevention, applied across the entire system:

### 1. Flow enforcement

Every item in the system must have a path and an endpoint:

| Component | Requirement |
|-----------|-------------|
| **Inbox** | Every item must have 1 of 3 outcomes: promote → SSOT, convert → research active, discard → abandoned |
| **Correction** | Every event must have status: open → applied/rejected/superseded |
| **Domain** | Every domain must always have an owner. If not → BLOCKED STATE → trigger assignment workflow |

### 2. Time enforcement

Every stalled state has a deadline:

| Constraint | Value | Applies to |
|------------|-------|------------|
| **Inbox TTL** | 7 days | Expired item → INVALID STATE |
| **Correction cycle** | 48h | Domain owner review window |
| **Seed phase** | 30 days | Seed owner auto-loses write permission after Day 30 |
| **SSOT review-by** | Per frontmatter | `review-by < today` → flag |

### 3. Cap enforcement

Prevents processor overload (domain owners):

| Cap | Value |
|-----|-------|
| **Inbox WIP** | 20 items max. Exceeded → block new intake or force prioritization |
| **Correction per cycle** | 20 per domain per cycle. Excess → deferred queue |

### 4. Role decay enforcement

Authority must have a lifecycle:

| Role | Decay | After |
|------|-------|-------|
| **Seed owner** | Write permission → override only | Day 30 |
| **Seed owner** | Cannot create new domains | Day 7 |
| **Domain owner** | Stable, no decay | — |
| **System Guardian** | Invariant | — |

### Correction tiering

Prevents domain owner bottleneck. 3 levels:

| Level | Type | Handled by | Example |
|-------|------|-----------|---------|
| **L1** | Trivial — auto-merge | System / Author | typo, link update, metadata mismatch |
| **L2** | Domain review required | Domain owner | content change, real correction |
| **L3** | Multi-domain arbitration | Multiple domain owners | conflict between primary and secondary domain |

---

## ACP execution runtime

ACP pack = **declarative execution contract + permission-bound action unit**. Not a script, config, or workflow doc.

### Canonical pack format

```yaml
id: update-ssot
version: 1.0

trigger:
  type: manual | ai | cron | event
  event: correction.approved

context:
  requires:
    - ssot
    - corrections

inputs:
  - correction_id
  - ssot_path

permissions:
  requires:
    domain_owner_approval: true
    system_guardian: validate

execution:
  steps:
    - validate_correction
    - load_ssot
    - apply_patch
    - update_metadata
    - write_ssot

outputs:
  - ssot_updated
  - correction_closed

rollback:
  enabled: true

audit:
  log_level: full
```

### Execution engine

```
ACP Runner
├── Loader (load YAML)
├── Context Builder (fetch files)
├── Permission Checker
├── Step Executor
├── State Writer
├── Audit Logger
```

### Execution flow

```
trigger → load pack → validate → execute steps → commit → log
```

### Critical rule

> ACP must not autonomously change the system outside its execution boundary.
> AI only proposes execution plan + fills input. Execution engine commits.

---

## System health metrics

### 4 vital signs

| Metric | Measures | Health threshold |
|--------|----------|-----------------|
| **Inbox health** | avg_age, % > TTL | inbox stagnant > 7 days → DEGRADED |
| **Correction health** | open_count, avg_resolution_time | backlog > threshold → DEGRADED |
| **Graph health** | orphan_count, broken_links | orphan_rate > 10% → DEGRADED |
| **Governance health** | domains_without_owner, stale_corrections | unowned domain → BLOCKED |

### Composite heartbeat score

```
system_health_score =
  40% graph_health
  30% correction_health
  20% inbox_health
  10% governance_health
```

### Dead system detection

```
IF:
  orphan_rate > 10%
  OR correction_backlog > threshold
  OR inbox stagnant > 7 days
THEN:
  system_state = DEGRADED
```

### Dashboard (minimal spec)

```yaml
system_health:
  score: 82
  status: healthy | degraded | critical

metrics:
  inbox_avg_age: 3d
  corrections_open: 12
  orphans: 5
  domains_unowned: 0
```

---

## Conflict resolution protocol

**Principle: hierarchical override with escalation.**
No peer-to-peer resolution at governance level (avoids deadlock).

| Layer | Authority |
|-------|-----------|
| **Primary domain owner** | Default authoritative |
| **Secondary domain** | Cannot block directly. Only escalate to System Guardian |
| **System guardian** | Final arbiter |

### Final system architecture

```
AI → proposes ACP execution
        ↓
ACP Engine validates
        ↓
Domain Owner approves (if required)
        ↓
System Guardian enforces
        ↓
State updated
        ↓
Audit logged
```

---

## Event Bus — kernel coordination layer

Event Bus is a first-class kernel component, not part of ACP.

```text
ACP = execution unit
Event Bus = coordination layer
```

### Architecture

```
Event Publisher
      ↓
 Event Bus
      ↓
 Subscription Registry
      ↓
 ACP Runtime
```

### Event message format (envelope)

```yaml
id: evt-20260618-001
type: correction.approved
timestamp: 2026-06-18T10:30:00Z
source:
  component: correction-system
  entity:
    type: correction
    id: corr-123

payload:
  correction_id: corr-123
  affected_ssot:
    - ssot/learning-model.md

metadata:
  correlation_id: corr-123       # groups the entire workflow chain
  causation_id: evt-20260618-000 # which event spawned this event
version: 1
```

### Subscription mechanism (declarative)

```yaml
# governance/subscriptions/correction-approved.yaml
event: correction.approved
handlers:
  - pack: update-ssot
```

```yaml
event: ssot.updated
handlers:
  - pack: validate-graph
  - pack: refresh-index
```

### Replay strategy

Correction events are immutable → replayable.

```bash
knowledge-os replay --from evt-001 --to evt-050
```

Dev mode (file-based):
```
runtime/event-store/2026/06/18/evt-001.yaml
runtime/event-store/2026/06/18/evt-002.yaml
```

Append-only. No edits. No deletes.

### ACP + Event Bus relationship

```
correction.approved
        ↓
Event Bus → subscription lookup → queue
        ↓
ACP Runner: update-ssot
        ↓
ssot.updated emitted
        ↓
Event Bus → validate-graph, refresh-index
```

---

## Guardian — split into 3 services

System Guardian is "dissolved" into 3 separate roles, no longer a god-object.

### Validator (automatic enforcement)

```text
schema validation
graph validation
orphan detection
link validation
ownership validation
```

Returns: `valid: true/false`. Does not decide. Does not block.

### Auditor (observation)

```text
audit logs
metrics
health dashboard
stagnation reports
compliance reports
```

Does not block. Does not approve. Only records.

### Arbiter (escalation only)

Single responsibility: resolve domain conflicts.

```
Primary Domain disagrees with Secondary Domain
        ↓
Escalation Event → Arbiter
```

**Arbiter is not on the happy path.** Only invoked on escalation.

### New Guardian flow

```text
Permission Check
        ↓
Validator (auto, non-blocking)
        ↓
Executor
```

When there's no conflict, Arbiter does not appear.

Only on conflict:

```text
Permission Check
        ↓
Validator
        ↓
Conflict → Arbiter
        ↓
Executor
```

### Directory

No `governance/guardian/` directory. Validator, Auditor, Arbiter are runtime services, not knowledge objects.

```text
foundation/
  event-schema.yaml          # event format
  validator-rules.yaml       # validation rules

governance/
  subscriptions/             # event → handler mapping
  escalation-policy.yaml     # arbiter rules
```

### 3-layer separation for universal template

```text
CORE KERNEL (invariants — platform-agnostic)
├── Knowledge model: SSOT, concept registry, correction system
├── Governance model: domain ownership, 3-tier authority, conflict resolution
├── Execution model: ACP spec, step-based execution, audit trail
├── Graph model: links as dependency graph, orphan detection
│
↓

RUNTIME ADAPTERS (implementations — swappable)
├── file-system (dev mode)
├── postgresql (scale mode)
├── cloud-api (distributed mode)
├── audit store (file / db / external)
│
↓

PLUGIN LAYER (extensions — B2B / B2C / AI)
├── AI agent executor
├── UI dashboard
├── B2B governance (strict audit, exposed correction)
├── B2C governance (hidden, abstracted)
├── GitHub Actions / CI
```

### Core kernel = the main content of this file (foundation, governance, ACP, anti-death)
### Everything else = adapter + plugin — designed to be swappable from day one.

### Missing piece: Event bus / IPC layer

Currently the system has:
- Processes (ACP execution)
- Memory (SSOT + corrections)
- Governance (domain owners)

**Missing:** event-driven coordination layer so ACP packs can communicate with each other.

```yaml
# Each ACP pack triggers from an event, not just manual
trigger:
  type: event
  event: correction.created | correction.approved | ssot.updated | orphan.detected
```

Event bus turns ACP executions into **inter-process communication (IPC)** for knowledge OS.

### 3 deployment modes — same kernel

| Mode | Storage | Runtime | When to use |
|------|---------|---------|-------------|
| **Dev** | File + YAML + Git | Local Python | Prototype, single dev |
| **Scale** | PostgreSQL | Server | Team, multi-AI agents |
| **Cloud** | Distributed | Async ACP engine | Production, multi-tenant |

> **Invariant across modes:** ACP + SSOT + correction loop = event-sourced immutable model.
> If this invariant holds, migrating between modes doesn't break the design.

---

## Projection Layer

### Purpose
Event Store → Projection Builder → Current State. Projection is a materialized view, not the source of truth.

### Principles

| Rule | Description |
|------|-------------|
| **Event Store is canonical** | All changes come from ACP → Event → Projection Rebuild. Never edit projections directly |
| **Projection is rebuildable** | Any projection can be regenerated from `runtime/event-store/` |
| **Snapshot is an optimization** | If snapshot is lost, Event Store + Replay can still rebuild |

### Projection Types

```text
Registry:   concept, ownership, domain, subscription
Health:     orphan count, broken link count
Governance: domain owners, approvals, escalations
```

### Storage

```
runtime/projections/
    concept-registry.yaml
    ownership-registry.yaml
    graph-health.yaml
```

### Replay Policy

| Type | When | Description |
|------|------|-------------|
| **Full Replay** | Projection missing, schema upgrade, corruption detected | Rebuild from scratch |
| **Incremental** | Default | `last_processed_event` → new events → update projection |

### Snapshot Policy (V1)

```
snapshot every 100 events OR every 24h (whichever comes first)
runtime/snapshots/
```

### Projection Builder

```
Event Store
    ↓
Projection Builder (trigger: projection.rebuild.requested or projection.refresh)
    ↓
Projection Files (concept-registry, ownership-registry, graph-health — V1)
```

---

## ACP Dependency Graph

### Purpose
Enables handler execution via DAG instead of sequential list.

### Pack schema extension

```yaml
execution:
  graph:
    validate-graph:
      depends_on: []
    refresh-health:
      depends_on:
        - validate-graph
```

### Execution rules
- **Root node** (`depends_on: []`) runs first.
- **Dependency completion**: Node only runs when all dependencies succeed.
- **Failure propagation**: Dependency failed → downstream skipped.
- **V1**: Topological order, single-thread. No worker pool.

---

## Dead Letter Queue (DLQ)

### Storage
```
runtime/event-bus/dlq/
```

### Envelope
```yaml
event_id: ...
event_type: ...
handler: validate-graph
failed_at: ...
error: ...
retry_count: 3
```

### Retry policy (V1)
`retry = 3` → if failed → DLQ.

### Reprocessing
Manual only:
```bash
python3 acp_event_bus.py --reprocess-dlq EVENT_ID
```
No automatic DLQ replay.

---

## Idempotency

### Registry
```
runtime/event-bus/processed/
```

### Identity
`event_id + handler_id` → processed record.

```yaml
event_id: ...
handler_id: validate-graph
processed_at: ...
status: success
```

### Delivery semantics (V1)
**At-Least-Once.** Rationale: simple, file-based, suitable for dev mode.

**Requirement:** Every ACP pack must be idempotent (check if patch already applied before applying).

**Future:** Exactly Once when migrating to transactional queue.

---

## Knowledge Kernel Distribution (standalone template)

> Kernel owns behavior. Project owns knowledge.

### 3-layer distribution

```
knowledge-kernel/

├── kernel/          ← Invariant. Required. Kernel-managed. Not directly editable.
├── starter-packs/   ← ACP pack templates. Customizable.
├── adapters/        ← Swappable. Dev (file) / Scale (postgres) / Cloud (distributed).
├── plugins/         ← Optional. AI agent, dashboard, B2B, B2C.
└── cli/             ← knowledge-os CLI.
```

### Core (kernel-managed, immutable)

```
kernel/
  foundation/
    00-glossary.md
    00-document-schema.md
    concept-registry.yaml

    events/
      event-schema.yaml
      event-types.yaml

    validator-rules.yaml
    pack-schema.yaml

  governance/
    ownership-model.md
    policy-management.md
    change-management.md
    escalation-policy.yaml

    corrections/
      00-index.md

    subscriptions/

  runtime/
    acp-runner.py
    event-bus.py
    validators.py

  knowledge/              ← empty, .gitkeep only
    inbox/
    research/active/
    research/abandoned/
    research/superseded/
    research/refuted/
    ssot/
    models/
    schemas/

  archive/
    superseded/
    deprecated/
    retired/
```

### Managed vs Owned

```yaml
# File header for kernel-managed files
managed-by: knowledge-kernel
managed-version: 1.0.0
```

| Layer | Managed by | Editable? |
|-------|-----------|-----------|
| `kernel/foundation/` | Kernel | Not directly editable |
| `kernel/governance/` | Kernel | Not directly editable |
| `kernel/runtime/` | Kernel | Not directly editable |
| `knowledge/` | Project | Freely editable |
| `corrections/` | Project | Editable (via ACP) |
| `starter-packs/` | Kernel+Project | Copy out, customize |

### Init & Upgrade

```bash
# Init project from kernel
knowledge-os init my-project
→ creates my-project/ with kernel files + .knowledge-os/ manifest

# Upgrade kernel (does not touch project content)
knowledge-os upgrade
→ updates kernel/foundation/*, kernel/runtime/*, starter-packs/*
→ does not touch knowledge/*, archive/*, corrections/*
```

### Template principle

> Template contains only what defines how the system operates.
> Project contains only what the system operates on.

---

## Directory structure

```
/knowledge-os

foundation/
  00-index.md
  00-glossary.md
  00-document-schema.md
  00-ssot-map.md
  00-decision-framework.md
  00-quality-gates.md
  concept-registry.yaml          ← single source of concept ownership + domain
  event-schema.yaml              ← event envelope format
  validator-rules.yaml           ← validation rules (graph, orphan, ownership)

governance/
  ownership-model.md
  policy-management.md
  change-management.md
  decision-records.md
  escalation-policy.yaml         ← arbiter: when to escalate, who decides

  corrections/                   ← audit trail for all SSOT changes
    00-index.md

  subscriptions/                 ← event → handler mapping
    correction-approved.yaml
    ssot-updated.yaml
    graph-validated.yaml

  acp-packs/
    00-validator-config.yaml
    01-pack--init-knowledge.yaml
    02-pack--add-research.yaml
    03-pack--update-ssot.yaml
    04-pack--update-model.yaml
    05-pack--update-schema.yaml
    06-pack--quality-audit.yaml
    07-pack--archive.yaml
    08-pack--refactor-link.yaml

knowledge/

  inbox/               ← new knowledge, unclassified

  research/
    active/            ← under active research, still valuable
      learning-science.md
      pedagogy.md
      language-acquisition.md
      benchmark-analysis.md
      literature-review.md

    abandoned/         ← discontinued (not wrong, just no one working on it)
    superseded/        ← replaced by newer knowledge
    refuted/           ← proven incorrect

  ssot/
    01-product-vision.md
    02-learning-architecture.md
    03-knowledge-model.md
    04-rag-architecture.md
    05-retrieval-strategy.md
    06-system-stages.md
    07-dependency-map.md
    08-gap-analysis.md
    09-decision-log.md

  learning-model/
    skill-graph.md
    mastery-model.md
    mistake-taxonomy.md
    difficulty-model.md
    progress-model.md
    srs-model.md
    assessment-model.md
    feedback-model.md

  schemas/
    skill-graph.yaml
    mastery-model.yaml
    mistake-taxonomy.yaml
    difficulty-model.yaml
    progress-model.yaml
    srs-model.yaml
    workflows.yaml
    agents.yaml

archive/
  superseded/
  deprecated/
  retired/
  historical-decisions.md
```

---

## Important Rules

### Structural rules

| Rule | Description |
|------|-------------|
| **No technology-named folders** | No `ai/`, `rag/`, `infra/`, `roadmap/`, `product/`, `quality/` |
| **ACP is a child of governance** | Do not split into separate folder |
| **Inbox is the single entry point** | All new knowledge enters through inbox before classification |
| **Archive = soft delete** | Never delete, only move to archive |

### Knowledge rules

| Rule | Description |
|------|-------------|
| **SSOT must have frontmatter** | Every SSOT requires: `status`, `last-reviewed`, `review-by`, `sources`, `links`, `owner` |
| **2-layer linking** | `links:` = dependency graph, `sources:` = provenance |
| **Provenance is mandatory** | No content is canonical unless it resides in an SSOT with `sources` |
| **Research is classified post-hoc** | `abandoned/`, `superseded/`, `refuted/` instead of a generic "archived" bucket |
| **One concept, one owner** | `concept-registry.yaml` is the single source of concept ownership |
| **Registry never deletes** | Deprecated concept → update `status`, do not remove entry |

### Governance rules

| Rule | Description |
|------|-------------|
| **SSOT is never directly overwritten** | All SSOT changes must go through a correction event |
| **Correction events are immutable** | Never edit, only supersede (like Git commit chain) |
| **Broken links are never auto-fixed** | System only REPORTS. Author maintains. Domain owner resolves |
| **No TTL for corrections** | Knowledge does not expire by time. It expires by validity |

### Anti-death rules

| Rule | Description |
|------|-------------|
| **Inbox has 7-day TTL** | Expired item → INVALID STATE |
| **Inbox WIP limit = 20** | Block new intake if exceeded |
| **Inbox needs outcome** | Every item must conclude: promote → SSOT, discard → abandon, or convert → research active |
| **Inbox stagnation auto-report** | If inbox unprocessed → system auto-generates stagnation report |
| **Correction 3-tier** | L1 auto-merge, L2 domain review, L3 multi-domain arbitration |
| **Correction cycle 48h** | Domain owner review window |
| **Correction cap 20/cycle** | Per domain per cycle. Excess → deferred queue |
| **Seed owner TTL 30 days** | Auto-loses write permission, override only |
| **Seed cannot create new domains after Day 7** | Domain creation → system process (domain proposal + council approval) |
| **Orphan domain detector** | Domain without owner → BLOCKED STATE → trigger assignment |

---

## SSOT frontmatter template

```yaml
---
title: Knowledge Model
status: active                # active | needs-review | superseded | deprecated
last-reviewed: 2026-06-18
review-by: 2026-09-18
sources:                      # provenance
  - research/active/learning-science.md
  - research/active/pedagogy.md
links:                        # dependency graph
  - ssot:product-vision
  - ssot:learning-architecture
supersedes:
superseded-by:
version: 1.0
owner: knowledge-team
primary-domain: pedagogical
secondary-domains:
  - structural
  - evaluation
---
```

---

## Correction event template

`governance/corrections/2026-06-18-learning-model-correction.md`:

```yaml
---
title: Correction to Learning Model
date: 2026-06-18
author: <anyone>              # anyone can propose
proposer: <name>
affects:
  - ssot/learning-model.md
type: partial-correction        # partial-correction | full-replacement | deprecation
source:
  - research/active/new-study.md
status: open                    # open → applied | rejected | superseded
domain-owner: learning-domain   # approver
rationale: >
  New study refutes the assumption that...
---
```

---

## concept-registry.yaml template

```yaml
learning-model:
  owner: ssot/learning-model.md
  primary-domain: pedagogical
  secondary-domains: [structural, evaluation]
  status: canonical

assessment-framework:
  owner: ssot/assessment-framework.md
  primary-domain: evaluation
  secondary-domains: [structural]
  status: canonical
```

---

## ACP Packs

ACP pack = **executable governance procedure** — not a static config.

Each pack is:
- An executable procedure
- Permission-bound (calls the right domain owner)
- Has validation rules
- Has an audit trail

Lifecycle: `propose → validate → execute → audit`

Who creates ACP packs:
- **Phase 0–1:** Seed owner
- **Phase 2:** Domain owners (within their domain)
