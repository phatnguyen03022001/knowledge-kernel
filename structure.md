# Knowledge OS — Structure

> Cấu trúc chuẩn đầu vào (pre-phase). Luôn phản ánh quyết định đã được đồng thuận.
> Xem `structure-log.md` để biết lịch sử thay đổi và phản biện.
>
> **Tầm nhìn:** Event-sourced, governance-bound, AI-executable knowledge kernel.
> Không phải document system hay project structure — mà là operating system cho AI-driven knowledge workflows.
> Có thể tách thành standalone template cho AI-native projects (B2B, B2C, hybrid).

---

## Flow tổng thể

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
Research mới
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

Mọi cơ chế trong hệ thống đều vận hành bởi 3 lớp quyền:

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

### Nguyên tắc nền

> Governance không phải là "ai có quyền", mà là "ai bị buộc phải chịu trách nhiệm khi có trạng thái không hợp lệ".

### Accountability closure loop cho mọi hành động

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

Domain không phải taxonomy (phân loại chủ đề). Domain là **vùng chịu trách nhiệm quyết định đúng/sai cuối cùng cho một loại câu hỏi**.

### 3 domains

| Domain | Trả lời câu hỏi | Ví dụ SSOT |
|--------|----------------|------------|
| **Structural** | Hệ thống tổ chức tri thức như thế nào? | product-vision, knowledge-model, dependency-map |
| **Pedagogical** | Con người học như thế nào? | learning-science, pedagogy, skill-graph |
| **Evaluation** | Đánh giá đúng/sai như thế nào? | assessment-model, mastery-model, difficulty-model |

### Primary + Secondary ownership

Domain overlap là mặc định, không phải bug. Một SSOT thuộc nhiều domain là bình thường. Giải pháp:

```yaml
primary-domain: evaluation          # quyết định "định nghĩa đúng/sai"
secondary-domains:                  # consultation, không veto
  - structural
  - pedagogical
```

Quy tắc:

| Loại quyết định | Ai quyết |
|----------------|----------|
| Definition correctness | Primary domain owner |
| Structural representation | Secondary (structural) |
| Pedagogy interpretation | Secondary (pedagogical) |

---

## Bootstrap — 3 phase

Hệ thống cold-start không thể có decentralized governance ngay. Cần bootstrapping authority.

### 🟢 Phase 0 — Seed Authority (Day 0)

1 người duy nhất (seed owner):
- Define domains
- Assign domain owners
- Approve first SSOT
- Initialize concept registry

> Domain owner CANNOT self-assign. Seed owner assign.

### 🟡 Phase 1 — Domain Bootstrap (Day 1–7)

Seed owner tạo:
```
domains:
  structural:   { owner: person-a }
  pedagogical:  { owner: person-b }
  evaluation:   { owner: person-c }
```

Domain owners bắt đầu vận hành: approve corrections, resolve concept overlap.

### 🔵 Phase 2 — Distributed Governance (Day 7+)

Seed owner chuyển thành observer / override authority (rare use).
- Domain owners govern
- System enforces
- Authors operate
- Seed chỉ can thiệp khi system deadlock

> Mọi system phân quyền đều cần một "initial arbitrary authority" để tạo trật tự đầu tiên.

---

## Anti-death constraints

> Governance systems không chết vì sai design. Chúng chết vì không có cơ chế bắt buộc tiến trình phải tiếp tục di chuyển.

4 lớp chống sụp đổ, áp dụng xuyên suốt hệ thống:

### 1. Flow enforcement

Mọi item trong system phải có đường đi và điểm kết thúc:

| Component | Yêu cầu |
|-----------|---------|
| **Inbox** | Mỗi item phải có 1 trong 3 outcome: promote → SSOT, convert → research active, discard → abandoned |
| **Correction** | Mỗi event phải có status: open → applied/rejected/superseded |
| **Domain** | Mỗi domain phải luôn có owner. Nếu không → BLOCKED STATE → trigger assignment workflow |

### 2. Time enforcement

Mọi trạng thái treo đều có hạn:

| Constraint | Giá trị | Áp dụng cho |
|------------|---------|-------------|
| **Inbox TTL** | 7 ngày | Item quá hạn → INVALID STATE |
| **Correction cycle** | 48h | Domain owner review window |
| **Seed phase** | 30 ngày | Seed owner tự động mất quyền write sau Day 30 |
| **SSOT review-by** | Theo frontmatter | `review-by < today` → flag |

### 3. Cap enforcement

Chống quá tải bộ xử lý (domain owners):

| Cap | Giá trị |
|-----|---------|
| **Inbox WIP** | 20 items tối đa. Vượt → block new intake hoặc force prioritization |
| **Correction per cycle** | 20 per domain per cycle. Excess → deferred queue |

### 4. Role decay enforcement

Quyền hạn phải có vòng đời:

| Role | Decay | After |
|------|-------|-------|
| **Seed owner** | Write permission → chỉ còn override | Day 30 |
| **Seed owner** | Không thể tạo domain mới | Day 7 |
| **Domain owner** | Ổn định, không decay | — |
| **System Guardian** | Invariant | — |

### Correction tiering

Chống domain owner bottleneck. 3 levels:

| Level | Loại | Xử lý bởi | Ví dụ |
|-------|------|-----------|-------|
| **L1** | Trivial — auto-merge | System / Author | typo, link update, metadata mismatch |
| **L2** | Domain review required | Domain owner | thay đổi nội dung, correction thật |
| **L3** | Multi-domain arbitration | Nhiều domain owners | conflict giữa primary và secondary domain |

---

## ACP execution runtime

ACP pack = **declarative execution contract + permission-bound action unit**. Không phải script, config, hay workflow doc.

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

> ACP không được tự thay đổi hệ thống ngoài execution boundary.
> AI chỉ được propose execution plan + fill input. Execution engine mới commit.

---

## System health metrics

### 4 vital signs

| Metric | Đo lường | Health threshold |
|--------|----------|-----------------|
| **Inbox health** | avg_age, % > TTL | inbox stagnant > 7 ngày → DEGRADED |
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

**Nguyên tắc: hierarchical override with escalation.**
Không peer-to-peer resolution ở governance level (tránh deadlock).

| Layer | Quyền |
|-------|-------|
| **Primary domain owner** | Authoritative mặc định |
| **Secondary domain** | Không block trực tiếp. Chỉ escalate lên System Guardian |
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

Event Bus là first-class kernel component, không nằm trong ACP.

```text
ACP = execution unit
Event Bus = coordination layer
```

### Kiến trúc

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
  correlation_id: corr-123       # gom cả workflow chain
  causation_id: evt-20260618-000 # event nào sinh ra event này
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

Correction events đã immutable → có thể replay.

```bash
knowledge-os replay --from evt-001 --to evt-050
```

Dev mode (file-based):
```
runtime/event-store/2026/06/18/evt-001.yaml
runtime/event-store/2026/06/18/evt-002.yaml
```

Append-only. Không sửa. Không xóa.

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

## Guardian — tách thành 3 services

System Guardian bị "giải thể" thành 3 role riêng, không còn god-object.

### Validator (automatic enforcement)

```text
schema validation
graph validation
orphan detection
link validation
ownership validation
```

Trả về: `valid: true/false`. Không quyết định. Không block.

### Auditor (observation)

```text
audit logs
metrics
health dashboard
stagnation reports
compliance reports
```

Không block. Không approve. Chỉ ghi nhận.

### Arbiter (escalation only)

Trách nhiệm duy nhất: resolve domain conflicts.

```
Primary Domain disagrees with Secondary Domain
        ↓
Escalation Event → Arbiter
```

**Arbiter không nằm trên happy path.** Chỉ gọi khi có escalation.

### Guardian flow mới

```text
Permission Check
        ↓
Validator (auto, không block)
        ↓
Executor
```

Khi không có conflict, Arbiter không xuất hiện.

Chỉ khi conflict:

```text
Permission Check
        ↓
Validator
        ↓
Conflict → Arbiter
        ↓
Executor
```

### Thư mục

Không thêm `governance/guardian/`. Vì Validator, Auditor, Arbiter là runtime services, không phải knowledge objects.

```text
foundation/
  event-schema.yaml          # event format
  validator-rules.yaml       # validation rules

governance/
  subscriptions/             # event → handler mapping
  escalation-policy.yaml     # arbiter rules
```

### 3-layer separation để thành universal template

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

### Core kernel = nội dung chính của file này (foundation, governance, ACP, anti-death)
### Còn lại = adapter + plugin — design để swappable ngay từ đầu.

### Missing piece: Event bus / IPC layer

Hiện tại system có:
- Processes (ACP execution)
- Memory (SSOT + corrections)
- Governance (domain owners)

**Thiếu:** event-driven coordination layer để ACP packs giao tiếp với nhau.

```yaml
# Mỗi ACP pack trigger từ event, không chỉ manual
trigger:
  type: event
  event: correction.created | correction.approved | ssot.updated | orphan.detected
```

Event bus giúp ACP executions trở thành **inter-process communication (IPC)** cho knowledge OS.

### 3 deployment modes — cùng 1 kernel

| Mode | Storage | Runtime | Khi nào dùng |
|------|---------|---------|-------------|
| **Dev** | File + YAML + Git | Local Python | Prototype, single dev |
| **Scale** | PostgreSQL | Server | Team, multi-AI agents |
| **Cloud** | Distributed | Async ACP engine | Production, multi-tenant |

> **Invariant giữa các mode:** ACP + SSOT + correction loop = event-sourced immutable model.
> Nếu giữ invariant này, migrate giữa các mode không phá design.

---

## Projection Layer

### Purpose
Event Store → Projection Builder → Current State. Projection là materialized view, không phải source of truth.

### Principles

| Rule | Mô tả |
|------|-------|
| **Event Store là canonical** | Mọi thay đổi đến từ ACP → Event → Projection Rebuild. Không sửa projection trực tiếp |
| **Projection có thể rebuild** | Bất kỳ projection nào cũng tái tạo từ `runtime/event-store/` |
| **Snapshot là optimization** | Nếu snapshot mất, Event Store + Replay vẫn rebuild được |

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

| Type | Khi nào | Mô tả |
|------|---------|-------|
| **Full Replay** | Projection missing, schema upgrade, corruption detected | Rebuild từ đầu |
| **Incremental** | Default | `last_processed_event` → new events → update projection |

### Snapshot Policy (V1)

```
snapshot every 100 events OR every 24h (điều kiện nào đến trước)
runtime/snapshots/
```

### Projection Builder

```
Event Store
    ↓
Projection Builder (trigger: projection.rebuild.requested hoặc projection.refresh)
    ↓
Projection Files (concept-registry, ownership-registry, graph-health — V1)
```

---

## ACP Dependency Graph

### Purpose
Cho phép handler execution theo DAG thay vì danh sách tuần tự.

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
- **Root node** (`depends_on: []`) chạy đầu tiên.
- **Dependency completion**: Node chỉ chạy khi toàn bộ dependency success.
- **Failure propagation**: Dependency failed → downstream skipped.
- **V1**: Topological order, single-thread. Không worker pool.

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
`retry = 3` → nếu fail → DLQ.

### Reprocessing
Manual only:
```bash
python3 acp_event_bus.py --reprocess-dlq EVENT_ID
```
Không tự động replay DLQ.

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
**At-Least-Once.** Lý do: đơn giản, file-based, phù hợp dev mode.

**Requirement:** Mọi ACP pack phải idempotent (kiểm tra patch đã áp dụng chưa trước khi apply).

**Future:** Exactly Once nếu chuyển sang transactional queue.

---

## Knowledge Kernel Distribution (standalone template)

> Kernel owns behavior. Project owns knowledge.

### 3-layer distribution

```
knowledge-kernel/

├── kernel/          ← Invariant. Bắt buộc. Kernel-managed. Không sửa trực tiếp.
├── starter-packs/   ← Mẫu ACP packs. Có thể tùy chỉnh.
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

  knowledge/              ← trống, chỉ .gitkeep
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
# File header cho kernel-managed files
managed-by: knowledge-kernel
managed-version: 1.0.0
```

| Layer | Quản lý bởi | Có thể sửa? |
|-------|-------------|-------------|
| `kernel/foundation/` | Kernel | Không sửa trực tiếp |
| `kernel/governance/` | Kernel | Không sửa trực tiếp |
| `kernel/runtime/` | Kernel | Không sửa trực tiếp |
| `knowledge/` | Project | Sửa thoải mái |
| `corrections/` | Project | Sửa (qua ACP) |
| `starter-packs/` | Kernel+Project | Copy ra, tùy chỉnh |

### Init & Upgrade

```bash
# Init project từ kernel
knowledge-os init my-project
→ tạo my-project/ với kernel files + .knowledge-os/ manifest

# Upgrade kernel (không đụng project content)
knowledge-os upgrade
→ update kernel/foundation/*, kernel/runtime/*, starter-packs/*
→ không động knowledge/*, archive/*, corrections/*
```

### Template principle

> Template chỉ chứa những thứ định nghĩa cách hệ thống vận hành.
> Project chỉ chứa những thứ hệ thống vận hành lên.

---

## Cấu trúc thư mục

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
  escalation-policy.yaml         ← arbiter: khi nào escalate, ai quyết

  corrections/                   ← audit trail cho mọi thay đổi SSOT
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

  inbox/               ← tri thức mới, chưa phân loại

  research/
    active/            ← đang được nghiên cứu, còn giá trị
      learning-science.md
      pedagogy.md
      language-acquisition.md
      benchmark-analysis.md
      literature-review.md

    abandoned/         ← ngừng theo đuổi (không sai, chỉ không ai làm)
    superseded/        ← đã được thay thế bởi tri thức mới hơn
    refuted/           ← đã được chứng minh là sai

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

## Quy tắc quan trọng

### Structural rules

| Rule | Mô tả |
|------|-------|
| **Không thêm folder công nghệ** | Không `ai/`, `rag/`, `infra/`, `roadmap/`, `product/`, `quality/` |
| **ACP là con của governance** | Không tách thành folder riêng |
| **Inbox là điểm vào duy nhất** | Mọi tri thức mới qua inbox trước khi phân loại |
| **Archive = soft delete** | Không xóa, chỉ chuyển vào archive |

### Knowledge rules

| Rule | Mô tả |
|------|-------|
| **SSOT phải có frontmatter** | Mỗi SSOT bắt buộc: `status`, `last-reviewed`, `review-by`, `sources`, `links`, `owner` |
| **2-layer linking** | `links:` = dependency graph, `sources:` = provenance |
| **Provenance bắt buộc** | Không có nội dung nào là chính thức nếu không nằm trong SSOT có `sources` |
| **Research phân loại hậu kỳ** | `abandoned/`, `superseded/`, `refuted/` thay vì gộp chung "archived" |
| **Một concept một owner** | `concept-registry.yaml` là single source of concept ownership |
| **Registry không xóa** | Concept deprecated → cập nhật `status`, không xóa entry |

### Governance rules

| Rule | Mô tả |
|------|-------|
| **SSOT không bị overwrite trực tiếp** | Mọi thay đổi SSOT phải qua correction event |
| **Correction event immutable** | Không sửa, chỉ supersede (giống Git commit chain) |
| **Broken link không tự sửa** | System chỉ REPORT. Author maintain. Domain owner resolve |
| **Không TTL cho correction** | Tri thức không expire theo thời gian. Chỉ expire theo validity |

### Anti-death rules

| Rule | Mô tả |
|------|-------|
| **Inbox có TTL 7 ngày** | Item quá hạn → INVALID STATE |
| **Inbox WIP limit = 20** | Block new intake nếu vượt |
| **Inbox cần outcome** | Mỗi item phải kết thúc: promote → SSOT, discard → abandon, hoặc convert → research active |
| **Inbox stagnation auto-report** | Nếu inbox không processed → system auto-generates stagnation report |
| **Correction 3-tier** | L1 auto-merge, L2 domain review, L3 multi-domain arbitration |
| **Correction cycle 48h** | Domain owner review window |
| **Correction cap 20/cycle** | Per domain per cycle. Excess → deferred queue |
| **Seed owner TTL 30 ngày** | Auto mất quyền write, chỉ còn override |
| **Seed không tạo domain mới sau Day 7** | Domain creation → system process (domain proposal + council approval) |
| **Orphan domain detector** | Domain không owner → BLOCKED STATE → trigger assignment |

---

## Mẫu frontmatter cho SSOT

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

## Mẫu correction event

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
domain-owner: learning-domain   # người approve
rationale: >
  New study refutes the assumption that...
---
```

---

## Mẫu concept-registry.yaml

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

ACP pack = **executable governance procedure** — không phải static confighet.

Mỗi pack là:
- Quy trình có thể thực thi
- Có quyền (gọi đúng domain owner)
- Có validation rules
- Có audit trail

Lifecycle: `propose → validate → execute → audit`

Ai tạo ACP packs:
- **Phase 0–1:** Seed owner
- **Phase 2:** Domain owners (within their domain)
