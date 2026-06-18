# Structure Log

> Nhật ký các quyết định về structure, lý do chọn/bỏ, phản biện từ các nguồn.

---

## 2026-06-18

### Quyết định 1: Root name là `knowledge-os/`

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `knowledge-os/` |
| **Bỏ** | `docs/` |
| **Lý do** | Tên gọi nói rõ ý định. `docs/` quá mơ hồ |
| **Phản biện** | Có thể bị cho là "kêu", quá tham vọng cho hệ thống chưa scale |

**Nguồn:** GPT#1, DS Pro (dùng knowledge-os). GPT#3 (đề xuất docs).

---

### Quyết định 2: ACP Packs trong `governance/acp-packs/`

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `governance/acp-packs/` |
| **Bỏ** | `operations/acp-packs/` (DS Pro) |
| **Lý do** | Governance và tools gắn chặt. Tách tạo implicit contract. V1 nên gộp |
| **Phản biện** | Nếu packs > 15-20, nên tách lại |
| **Độ tin cậy** | ~70% |

**Nguồn:** DS Pro (tách), GPT#3 (gộp trong governance).

---

### Quyết định 3: Thêm `knowledge/inbox/`

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Có `inbox/` |
| **Bỏ** | Hệ thống không có inbox |
| **Lý do** | Landing zone cho tri thức mới, tránh rác phân tán |
| **Phản biện** | Inbox có thể thành dumping ground nếu không xử lý kịp |
| **Nguồn** | Zettelkasten. Không có trong 3 file GPT/DS gốc |

---

### Quyết định 4: Research phân loại hậu kỳ

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `active/`, `abandoned/`, `superseded/`, `refuted/` |
| **Bỏ** | `research/tracking/` (log tay), `candidate/` (trạng thái ảo) |
| **Lý do** | Folder cho thấy trạng thái ngay. `refuted/` cần tách riêng vì là rác nguy hiểm |
| **Độ tin cậy** | ~85% |

**Nguồn:** GPT (active+archived), Claude (tách archived thành 3 loại).

---

### Quyết định 5: SSOT lifecycle qua frontmatter

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Frontmatter: `status`, `last-reviewed`, `review-by`, `sources`, `version`, `owner` |
| **Bỏ** | `ssot/validation/`, `governance/review-schedule.md` |
| **Lý do** | Metadata đi cùng file, query được, không thể tách rời |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 2).

---

### Quyết định 6: Provenance là đòn bẩy lớn nhất

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Rule: "Không có nội dung nào là chính thức nếu không nằm trong SSOT có sources" |
| **Lý do** | Giải quyết đồng thời nhiều vấn đề: research treo, provenance, orphan, duplicate |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 2, MVP).

---

### Quyết định 7: Orphan detection — 2-layer linking

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `links:` (dependency graph) + `sources:` (provenance) trong frontmatter |
| **Bỏ** | Markdown link thuần (thiếu ngữ nghĩa), chỉ sources (lệch orphan) |
| **Orphan definition** | `incoming_links = 0 AND not in root index` |
| **Enforce** | Script `knowledge-os validate-graph` (CI/local) |
| **Còn thiếu** | Link chết không được xử lý. Ai implement script? |
| **Độ tin cậy** | ~75%. `links:` cũng phải maintain tay — có thể thành rác |

**Nguồn:** GPT (vòng 3), Claude (lọc: cảnh báo link chết, maintain tay).

---

### Quyết định 8: Duplicate detection — Concept Registry

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `foundation/concept-registry.yaml` — single owner cho mỗi concept |
| **Rule** | Một concept chỉ một owner. Conflict → reject |
| **Enforce** | CI check: SSOT mới phải đăng ký concept trước |
| **Còn thiếu** | Ai maintain registry? Overlapping concepts? Cleanup khi SSOT deprecated? |
| **Độ tin cậy** | ~70% |

**Nguồn:** GPT (vòng 3), Claude (lọc: chi phí vận hành, overlapping).

---

### Quyết định 9: Correction loop

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `governance/corrections/` — correction event log |
| **Rule** | SSOT không bị overwrite trực tiếp. Mọi thay đổi qua correction event |
| **SSOT states** | `active` → `deprecated` → `superseded` |
| **Enforce** | CI: nếu SSOT content thay đổi mà không có correction event → fail |
| **Mẫu** | File event: date, affects, type, source, status, rationale |
| **Còn thiếu** | Ai được tạo correction event? Rollback nếu research sai? |
| **Độ tin cậy** | ~80%. Cần layer governance phía sau. |

**Nguồn:** GPT (vòng 3). Claude (lọc: rollback, quyền hạn).

---

### Quyết định 10: Governance model (3-tier)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | 3-tier: Authors, Domain Owners, System Guardian |
| **Lý do** | Cả 3 cơ chế (orphan, registry, correction) đều chết nếu không có accountability anchor |
| **Closure loop** | Detection → Proposal → Decision → Execution → Validation |
| **Authors** | Maintain SSOT, links. Implement corrections |
| **Domain Owners** | Resolve semantic conflicts. Approve corrections. Arbitrate concept overlap |
| **System Guardian** | Detect orphan, broken links. Enforce registry consistency, correction linkage |
| **Độ tin cậy** | ~85% |

**Nguồn:** GPT (vòng 4).

---

### Quyết định 11: Domain model

| Trường | Giá trị |
|--------|---------|
| **Chọn** | 3 domains: **Structural**, **Pedagogical**, **Evaluation** |
| **Định nghĩa** | Domain = vùng chịu trách nhiệm quyết định đúng/sai, không phải topic |
| **Overlap** | Là mặc định, không phải bug. Giải quyết bằng primary + secondary ownership |
| **Primary** | Quyết định definition correctness |
| **Secondary** | Consultation, không veto — cho structural/pedagogy/evaluation interpretation |
| **Ví dụ** | skill-graph.md: primary=evaluation, secondary=[structural, pedagogical] |
| **Độ tin cậy** | ~80%. Domain boundaries cần refine theo thực tế |

**Nguồn:** GPT (vòng 5). Overlap handling là insight quan trọng.

---

### Quyết định 12: Bootstrap 3-phase

| Trường | Giá trị |
|--------|---------|
| **Chọn** | 3 phases: Seed → Domain Assignment → Distributed |
| **Phase 0 (Day 0)** | Seed owner duy nhất. Define domains, assign owners, approve first SSOT |
| **Phase 1 (Day 1–7)** | Domain owners bắt đầu vận hành. Seed tạo domain registry |
| **Phase 2 (Day 7+)** | Seed thành observer. Domain owners govern, system enforces |
| **Rule** | Domain owner CANNOT self-assign |
| **Insight** | "Domain boundaries không tồn tại trước governance. Chúng được đẻ ra bởi bootstrap." |
| **Độ tin cậy** | ~85%. Đây là vấn đề thực tế của mọi system, giải pháp thực dụng |

**Nguồn:** GPT (vòng 5). Đánh giá là phase khó nhất.

---

### Quyết định 13: ACP là executable governance procedure

| Trường | Giá trị |
|--------|---------|
| **Chọn** | ACP pack = executable governance procedure (không phải static config) |
| **Lifecycle** | propose → validate → execute → audit |
| **Ai tạo** | Phase 0–1: Seed owner. Phase 2: Domain owners (within their domain) |
| **Bản chất** | Giống GitHub Actions / DB migrations / policy-as-code |
| **Độ tin cậy** | ~75%. Cần spec cụ thể về format pack và execution engine |

**Nguồn:** GPT (vòng 5).

---

## Tổng kết độ tin cậy

| Quyết định | Score | Rủi ro chính |
|-----------|-------|-------------|
| Root name | ~85% | Kêu |
| ACP trong governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research phân loại | ~85% | — |
| SSOT frontmatter | ~90% | Migration file cũ |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` maintain tay |
| Concept registry | ~70% | Chi phí vận hành |
| Correction loop | ~80% | Governance phía sau |
| Governance 3-tier | ~85% | Domain owner không làm tròn |
| Domain model | ~80% | Boundaries cần refine |
| Bootstrap | ~85% | Seed owner chọn sai |
| ACP executable | ~75% | Cần spec execution |

---

### Quyết định 14: Inbox anti-death (TTL + WIP + sink)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Inbox TTL 7 ngày, WIP limit 20, bắt buộc outcome (promote/convert/discard) |
| **Bỏ** | Inbox là folder không ràng buộc |
| **Lý do** | Inbox chết vì không có throughput guarantee. Cần forcing function để đẩy item đi tiếp |
| **Anti-pattern** | Nếu inbox không processed → system auto-generates stagnation report |
| **Độ tin cậy** | ~80%. Số cụ thể (7 days, 20 items) cần refine theo thực tế |

**Nguồn:** GPT (vòng 6 — anti-death layer).

---

### Quyết định 15: Correction anti-death (3-tier + batch + cap)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | 3-tier correction system: L1 auto-merge, L2 domain review, L3 multi-domain |
| **Bỏ** | Mọi correction qua domain owner (bottleneck) |
| **Cycle** | Review every 48h, cap 20 per domain per cycle |
| **Excess** | Deferred queue |
| **Lý do** | Correction log explosion là decision bottleneck ở domain owner, không phải số lượng correction |
| **Độ tin cậy** | ~80%. Cần refine L1/L2/L3 boundaries |

**Nguồn:** GPT (vòng 6).

---

### Quyết định 16: Seed owner anti-death (expiring authority)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Seed owner: TTL 30 ngày, tự động mất quyền write |
| **Bỏ** | Seed owner "có thể rời" nhưng không cơ chế cưỡng bức |
| **Domain creation** | Seed không tạo domain mới sau Day 7. Domain creation → domain proposal + council approval |
| **Orphan domain** | System auto-detect domain không owner → BLOCKED STATE |
| **Lý do** | Seed owner là unresolved authority residue. Phải bị gradually deprecated by design |
| **Độ tin cậy** | ~85%. Realistic cho hệ nhỏ |

**Nguồn:** GPT (vòng 6).

---

## Tổng kết độ tin cậy (mở rộng)

| Quyết định | Score | Rủi ro chính |
|-----------|-------|-------------|
| Root name | ~85% | Kêu |
| ACP trong governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research phân loại | ~85% | — |
| SSOT frontmatter | ~90% | Migration file cũ |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` maintain tay |
| Concept registry | ~70% | Chi phí vận hành |
| Correction loop | ~80% | Governance phía sau |
| Governance 3-tier | ~85% | Domain owner không làm tròn |
| Domain model | ~80% | Boundaries cần refine |
| Bootstrap | ~85% | Seed owner chọn sai |
| ACP executable | ~75% | Cần spec execution |
| **Inbox anti-death** | **~80%** | Số cụ thể cần refine |
| **Correction tiering** | **~80%** | L1/L2/L3 boundaries |
| **Seed expiry** | **~85%** | Realistic cho hệ nhỏ |

---

### Quyết định 17: ACP execution runtime spec

| Trường | Giá trị |
|--------|---------|
| **Chọn** | ACP = declarative execution contract + permission-bound action unit |
| **Format** | YAML: id, trigger, context, inputs, permissions, execution steps, outputs, rollback, audit |
| **Engine** | Loader → Context Builder → Permission Checker → Step Executor → State Writer → Audit Logger |
| **Critical rule** | AI propose execution plan. Execution engine mới commit. ACP không tự thay đổi ngoài execution boundary |
| **Độ tin cậy** | ~80%. Cần reference implementation (~250 lines Python) |

**Nguồn:** GPT (vòng 7 — runtime spec).

---

### Quyết định 18: System health metrics (4 vital signs)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | 4 metrics: inbox health, correction health, graph health, governance health |
| **Composite** | 40% graph + 30% correction + 20% inbox + 10% governance |
| **Dead detection** | orphan_rate > 10% OR correction backlog > threshold OR inbox stagnant > 7 days → DEGRADED |
| **Dashboard** | Minimal YAML spec: score, status, 4 metrics |
| **Độ tin cậy** | ~85%. Weight có thể refine sau |

**Nguồn:** GPT (vòng 7).

---

### Quyết định 19: Conflict resolution protocol

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Hierarchical override with escalation. Primary domain wins mặc định |
| **Bỏ** | Voting, consensus, peer-to-peer resolution (dẫn đến deadlock) |
| **Secondary** | Không block trực tiếp. Chỉ escalate lên System Guardian |
| **System Guardian** | Final arbiter |
| **Rule** | No peer-to-peer resolution at governance level |
| **Độ tin cậy** | ~85%. Đơn giản, tránh deadlock |

**Nguồn:** GPT (vòng 7).

---

### Quyết định 20: Final system architecture

| Trường | Giá trị |
|--------|---------|
| **Flow** | AI propose → ACP Engine validate → Domain Owner approve → System Guardian enforce → State update → Audit log |
| **Độ tin cậy** | ~85%. Đây là tổng kết cuối cùng của toàn bộ system design |

**Nguồn:** GPT (vòng 7).

---

## Tổng kết độ tin cậy (final)

| Quyết định | Score | Rủi ro chính |
|-----------|-------|-------------|
| Root name | ~85% | Kêu |
| ACP trong governance | ~70% | Scale |
| Inbox | ~80% | Dumping ground |
| Research phân loại | ~85% | — |
| SSOT frontmatter | ~90% | Migration file cũ |
| Provenance rule | ~90% | — |
| Orphan (2-layer) | ~75% | `links:` maintain tay |
| Concept registry | ~70% | Chi phí vận hành |
| Correction loop | ~80% | Governance phía sau |
| Governance 3-tier | ~85% | Domain owner không làm tròn |
| Domain model | ~80% | Boundaries cần refine |
| Bootstrap | ~85% | Seed owner chọn sai |
| ACP executable | ~75% | Cần spec execution |
| Inbox anti-death | ~80% | Số cụ thể cần refine |
| Correction tiering | ~80% | L1/L2/L3 boundaries |
| Seed expiry | ~85% | Realistic cho hệ nhỏ |
| **ACP runtime** | **~80%** | Cần reference implementation |
| **Health metrics** | **~85%** | Weight có thể refine |
| **Conflict resolution** | **~85%** | — |
| **Final architecture** | **~85%** | — |
| **ACP runner impl** | **~100%** | Step registry real, atomic write, event emission, permission token, validator, retry/skip |
| **Event Bus** | **~95%** | Subscription loader, event matcher, sequential scheduler, listen mode, manual mode |
| **End-to-end chain** | **~95%** | correction.approved → update-ssot → ssot.updated → validate-graph + refresh-health |

---

### Quyết định 21: System là knowledge kernel, không phải product platform

| Trường | Giá trị |
|--------|---------|
| **Tầm nhìn** | Event-sourced, governance-bound, AI-executable knowledge kernel |
| **Làm được** | Runtime governance kernel (SSOT + governance + ACP + audit) |
| **Chưa làm được** | Product platform — cần 3-layer separation |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 8 — stress test cuối).

---

### Quyết định 22: 3-layer separation (core / adapters / plugins)

| Trường | Giá trị |
|--------|---------|
| **Core kernel** | Knowledge model, governance model, execution model, graph model — platform-agnostic invariants |
| **Runtime adapters** | file-system (dev), postgresql (scale), cloud-api (distributed) |
| **Plugin layer** | AI agents, UI, B2B/B2C governance profiles, CI integrations |
| **Rule** | Giữ core thuần khiết. Mọi implementation bias đẩy xuống adapter |
| **Độ tin cậy** | ~85% |

**Nguồn:** GPT (vòng 8).

---

### Quyết định 23: Missing OS layer — Event bus / IPC

| Trường | Giá trị |
|--------|---------|
| **Vấn đề** | Có processes (ACP), memory (SSOT), governance (domain) — thiếu event-driven coordination |
| **Giải pháp** | ACP trigger field mở rộng: `trigger.type: event`, `trigger.event: correction.created` |
| **Ý nghĩa** | ACP executions = IPC cho knowledge OS. Packs giao tiếp qua events |
| **Độ tin cậy** | ~80%. Cần design spec trước khi implement |

**Nguồn:** GPT (vòng 8).

---

### Quyết định 24: 3 deployment modes — cùng 1 kernel

| Trường | Giá trị |
|--------|---------|
| **Dev** | File + YAML + Git + local Python |
| **Scale** | PostgreSQL + server |
| **Cloud** | Distributed + async ACP engine |
| **Invariant** | ACP + SSOT + correction loop = event-sourced immutable model. Migrate không phá design |
| **Độ tin cậy** | ~85% |

**Nguồn:** GPT (vòng 8).

---

### Quyết định 25: B2B vs B2C — cùng kernel, khác policy + exposure

| Trường | Giá trị |
|--------|---------|
| **Kernel** | Chung (SSOT, governance, ACP, audit) |
| **B2B** | Strict governance, full audit, exposed correction loop, explicit domain ownership |
| **B2C** | Hidden governance, partial audit, internal correction, abstracted domain |
| **UX layer** | B2B: irrelevant. B2C: critical |
| **Độ tin cậy** | ~90%. Đây là insight kiến trúc chắc chắn |

**Nguồn:** GPT (vòng 8).

---

### Quyết định 26: Event Bus là kernel component riêng

| Trường | Giá trị |
|--------|---------|
| **Chọn** | Event Bus = first-class kernel component, không nằm trong ACP |
| **Lý do** | ACP = execution unit, Event Bus = coordination layer. Là hai abstraction khác nhau |
| **Format** | Envelope: id, type, timestamp, source, payload, metadata (correlation_id, causation_id) |
| **Subscription** | Declarative YAML: `governance/subscriptions/` — event → handler mapping |
| **Replay** | `knowledge-os replay --from evt-001 --to evt-050`, event store append-only |
| **Dev mode** | File-based: `runtime/event-store/YYYY/MM/DD/evt-NNN.yaml` + queue/pending/ |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 9 — self-review). Đây là missing piece quan trọng nhất.

---

### Quyết định 27: Guardian decomposition

| Trường | Giá trị |
|--------|---------|
| **Chọn** | "Giải thể" System Guardian thành 3 services: Validator, Auditor, Arbiter |
| **Bỏ** | System Guardian god-object (overload: vừa CI, vừa audit, vừa phán xử) |
| **Validator** | Automatic enforcement — schema, graph, orphan, link, ownership. Trả về valid: true/false |
| **Auditor** | Observation — audit logs, metrics, health dashboard, stagnation reports. Không block, không approve |
| **Arbiter** | Escalation only — resolve domain conflicts. Không nằm trên happy path |
| **Thư mục** | Không thêm governance/guardian/. Validator/Auditor/Arbiter là runtime services, không phải knowledge objects |
| **Độ tin cậy** | ~95% |

**Nguồn:** GPT (vòng 9 — self-review).

---

Từ một folder structure → một **event-sourced, governance-bound knowledge kernel** có thể trở thành universal template cho AI-native projects.

---

### Quyết định 28: 3-layer distribution (kernel / adapters / plugins)

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `knowledge-kernel/`: kernel/ + starter-packs/ + adapters/ + plugins/ + cli/ |
| **Bỏ** | Template là "project rỗng" (sẽ lẫn kernel evolution vs project evolution) |
| **Kernel** | Invariant. Bắt buộc. Kernel-managed. Không sửa trực tiếp |
| **Starter-packs** | ACP packs mẫu. Có thể tùy chỉnh |
| **Adapters** | Swappable: filesystem (dev), postgres (scale), cloud (distributed) |
| **Plugins** | Optional: ai-agent, dashboard, github-actions, b2b, b2c |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 10 — đóng gói).

---

### Quyết định 29: ACP spec là core, ACP packs là starter content

| Trường | Giá trị |
|--------|---------|
| **Core** | `kernel/foundation/pack-schema.yaml` — định nghĩa pack format |
| **Starter** | `starter-packs/update-ssot.yaml` — implementation cụ thể |
| **Tương tự** | Kubernetes API (core) vs Deployment.yaml (template content) |
| **Độ tin cậy** | ~95% |

**Nguồn:** GPT (vòng 10).

---

### Quyết định 30: Kernel-managed vs Project-owned

| Trường | Giá trị |
|--------|---------|
| **Managed-by header** | `managed-by: knowledge-kernel`, `managed-version: 1.0.0` |
| **Kernel-managed** | `kernel/foundation/*`, `kernel/governance/*`, `kernel/runtime/*` |
| **Project-owned** | `knowledge/*`, `archive/*`, `corrections/*` |
| **Upgrade** | `knowledge-os upgrade` → chỉ update kernel-managed files, không động project content |
| **Init** | `knowledge-os init my-project` → generate project structure + `.knowledge-os/` manifest |
| **Độ tin cậy** | ~90% |

**Nguồn:** GPT (vòng 10).

---

### Quyết định 31: Spec additions (Projection, DAG, DLQ, Idempotency)

| Trường | Giá trị |
|--------|---------|
| **Projection** | Event Store → Projection Builder → Current State. Snapshot 100 events/24h. V1: concept-registry, ownership-registry, graph-health |
| **ACP DAG** | `execution.graph` YAML format. Topological order. Dependency failed → downstream skipped. V1 single-thread |
| **DLQ** | `runtime/event-bus/dlq/`. Retry 3 → DLQ. Manual reprocess only |
| **Idempotency** | At-Least-Once. `event_id + handler_id` → processed registry. Pack phải idempotent |
| **Độ tin cậy** | ~95% |

**Nguồn:** GPT (vòng 11 — final).

---

### Quyết định 32: Test harness

| Trường | Giá trị |
|--------|---------|
| **Chọn** | `tests/harness.py` + `tests/scenarios/*.yaml` |
| **Format** | YAML scenario: steps (run_pack, run_event_bus) + expectations (events, audit_logs, packs_executed, processed_count) |
| **V1 scenarios** | update-ssot-flow, validate-graph-only, refresh-health-only |
| **Kết quả** | 3/3 PASS |

---

## Kết thúc Phase 1

Tổng: **32 quyết định** qua **11 vòng GPT + lọc của Claude**.

```text
Giai đoạn 1 (vòng 1-3):   Structure + cơ chế chống rác
Giai đoạn 2 (vòng 4-5):   Governance + domain + bootstrap
Giai đoạn 3 (vòng 6):     Anti-death constraints
Giai đoạn 4 (vòng 7):     ACP runtime + metrics + conflict resolution
Giai đoạn 5 (vòng 8):     Platform architecture + standalone template vision
Giai đoạn 6 (vòng 9):     Event Bus + Guardian decomposition
Giai đoạn 7 (vòng 10):    Kernel distribution packaging
Giai đoạn 8 (vòng 11):    Final spec (Projection, DAG, DLQ, Idempotency) + Test harness
```

```text
Giai đoạn 1 (vòng 1-3):   Structure + cơ chế chống rác
Giai đoạn 2 (vòng 4-5):   Governance + domain + bootstrap
Giai đoạn 3 (vòng 6):     Anti-death constraints
Giai đoạn 4 (vòng 7):     ACP runtime + metrics + conflict resolution
Giai đoạn 5 (vòng 8):     Platform architecture + standalone template vision
Giai đoạn 6 (vòng 9):     Event Bus + Guardian decomposition
Giai đoạn 7 (vòng 10):    Kernel distribution packaging
```

Từ một folder structure → một **event-sourced, governance-bound knowledge kernel** có thể trở thành universal template cho AI-native projects.

### Nguyên tắc cuối cùng

> **Kernel owns behavior. Project owns knowledge.**
>
> Template chỉ chứa những thứ định nghĩa cách hệ thống vận hành.
> Project chỉ chứa những thứ hệ thống vận hành lên.
