# ACP — Agent Contract Protocol v1.0

> *A deterministic interface protocol for stateless multi-agent LLM orchestration.*
>
> **Core insight:** Different models think differently. But they can all speak the same protocol.
>
> Pack = Task. Contract = Interface. Verification = Law.

---

## Table of Contents

1. [Why ACP Exists](#1-why-acp-exists)
2. [Core Principle](#2-core-principle)
3. [The Innovation: Contract over Prompt](#3-the-innovation-contract-over-prompt)
4. [Protocol Layers](#4-protocol-layers)
5. [Protocol Flow](#5-protocol-flow)
6. [The Handshake](#6-the-handshake)
7. [Validator-First Architecture](#7-validator-first-architecture)
8. [Decision Provenance](#8-decision-provenance)
9. [Model Routing & Cost](#9-model-routing--cost)
10. [Failure Handling](#10-failure-handling)
11. [Cold-Start Guarantee](#11-cold-start-guarantee)
12. [Comparison: ACP vs. Other Approaches](#12-comparison-acp-vs-other-approaches)
13. [FAQ](#13-faq)
14. [Change Log](#14-change-log)

---

## 1. Why ACP Exists

### The Real Problem

In multi-agent AI systems, **80% of failures are not agents doing the wrong task. They are the next agent not understanding what the previous agent did.**

| Agent A output | Agent B interprets as |
|---------------|----------------------|
| `status: completed` | "Code builds? Tests pass? Just implementation?" |
| `memory_list: []` | "Empty result? Or bug?" |

This ambiguity is the **scalability bottleneck** of multi-agent systems.

### The ACP Solution

ACP replaces ambiguous natural-language handoffs with a **deterministic protocol**.

Instead of:

> "Here's what I did. Can you review it and let me know if there are any issues?"

ACP produces:

```yaml
handshake:
  interface_signature: sha256:de9f2c7f...
  success_criteria:
    - output_schema: PASS
    - invariants: PASS
    - violations: NONE
  verdict: PASS
```

Any model — Claude, GPT, DeepSeek — reading this understands **exactly** what happened and what to do next.

---

## 2. Core Principle

> **No AI is memory.**

| Principle | Meaning |
|-----------|---------|
| **Git is SSOT** | All artifacts live in Git. Not in chat history. |
| **Contract over prompt** | Schema is law. Instruction is suggestion. |
| **Validator first** | Trust the validator, not the model. |
| **Stateless execution** | Every execution starts fresh. No session state. |
| **Deterministic interface** | Models can think differently but must output the same shape. |

### What ACP does NOT do

- ❌ Does not make models "think better"
- ❌ Does not enforce identical reasoning
- ❌ Does not require specific models
- ❌ Does not depend on chat history
- ❌ Does not require human-in-the-loop for every task

---

## 3. The Innovation: Contract over Prompt

### The Old Way (Prompt Engineering)

```
You are a Python developer working on a flashcard app.
Please implement the MemoryRepository class.
It should have save() and findByStudent() methods.
Make sure to follow the repository pattern.
...
```

- ❌ Ambiguous priorities
- ❌ Model-dependent interpretation
- ❌ No machine-verifiable criteria
- ❌ Quality varies with model version

### The ACP Way (Contract Protocol)

```yaml
contract:
  input_schema:
    student_id: { type: uuid, required: true }
    memories: { type: array, max_items: 50 }

  output_schema:
    saved_ids: { type: array, of: uuid, length == input.memories.length }
    timestamp: { type: iso8601 }

  invariants:
    - "saved_ids.length == input.memories.length"  # mathematical guarantee
    - "all saved_ids are unique"

  violations:
    - "invalid uuid → return error, don't crash"
    - "duplicate memory → reject, don't silently overwrite"
```

- ✅ Machine-verifiable
- ✅ Model-independent
- ✅ Self-contained
- ✅ Deterministic interface

### The Difference

| | Prompt | Contract |
|--|--------|----------|
| **What it is** | A suggestion | An interface |
| **Verification** | Subjective ("looks good") | Objective (schema match) |
| **Model dependency** | High (each model interprets differently) | Low (schema is schema) |
| **Version tolerance** | Fragile (prompt injection over time) | Stable (contract hashes don't drift) |

---

## 4. Protocol Layers

ACP has 12 layers. Each layer solves one specific problem.

```
┌──────────────────────────────────────────────────────────┐
│  0. IDENTITY         Pack ID, spec hash, parent ref       │
├──────────────────────────────────────────────────────────┤
│  1. CONTRACT         Input schema + output schema +       │
│                      invariants + violations              │
├──────────────────────────────────────────────────────────┤
│  2. HANDSHAKE        Interface signature, success         │
│                      criteria, acceptance criteria        │
├──────────────────────────────────────────────────────────┤
│  3. EXECUTION        Permitted files, forbidden ops,      │
│                      dependencies, IO boundary            │
├──────────────────────────────────────────────────────────┤
│  4. LAYER-ZERO       Project context in 1 paragraph,      │
│                      CoT prefix, anti-patterns            │
├──────────────────────────────────────────────────────────┤
│  5. SELF-VERIFY      Static checks, auto-pass/reject,     │
│                      auto-repair with retry               │
├──────────────────────────────────────────────────────────┤
│  6. EVIDENCE         Provenance trail, execution log,     │
│                      attempt history                      │
├──────────────────────────────────────────────────────────┤
│  7. DECISIONS        Architectural decisions with         │
│                      rationale and impact                 │
├──────────────────────────────────────────────────────────┤
│  8. FAILURE          Known patterns, recovery strategy,   │
│                      escalation rules                     │
├──────────────────────────────────────────────────────────┤
│  9. ATTENTION        Priority directives, ignore list,    │
│                      token allocation                     │
├──────────────────────────────────────────────────────────┤
│ 10. CLOSED-LOOP      Verification pipeline (6 steps),     │
│                      escalation & auto-merge conditions   │
├──────────────────────────────────────────────────────────┤
│ 11. COST             Model routing, budget, overflow      │
├──────────────────────────────────────────────────────────┤
│ 12. PHASE            Temporal awareness, phase-specific   │
│                      contracts, entry/exit criteria       │
└──────────────────────────────────────────────────────────┘
```

### Layer Summary

| Layer | Problem it solves | Why it matters |
|-------|------------------|----------------|
| **0** | "Which pack is this?" | Deterministic identity across sessions |
| **1** | "What do I produce?" | The core — contract, not prompt |
| **2** | "What counts as done?" | Shared definition of success |
| **3** | "What am I allowed to do?" | Bounded execution scope |
| **4** | "I don't know this project" | Goldfish-brain compatibility |
| **5** | "Is my output correct?" | Self-validation before submit |
| **6** | "What happened?" | Audit trail without chat history |
| **7** | "Why was this built this way?" | Architectural memory |
| **8** | "What if something goes wrong?" | Predictable failure recovery |
| **9** | "What should I focus on?" | Attention allocation |
| **10** | "Is this ready to merge?" | Final verification pipeline |
| **11** | "How much does this cost?" | Resource governance |
| **12** | "What phase are we in?" | Temporal awareness |

---

## 5. Protocol Flow

### The ACP Execution Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                    1. PACK CREATION                      │
│  Claude/DeepSeek reads SSOT → produces context pack     │
│  Output: ACP-PACK-TASK-001-v1.yaml                      │
│  Verification: pack.identity.spec matches SSOT hash     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   2. EXECUTION (any model)               │
│  Model reads contract → produces output                 │
│  Self-verify: run static checks, invariants, schema     │
│  Auto-repair: up to 3 retries on failure                │
│  Output: code + tests + evidence entry                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               3. VERIFICATION PIPELINE                   │
│  Step 1: Schema validation (structural match)           │
│  Step 2: Invariant validation (semantic match)          │
│  Step 3: Rule enforcement (forbidden patterns)          │
│  Step 4: Interface handshake (signature match)          │
│  Step 5: Test execution (if defined)                    │
│  Step 6: Evidence append (trail update)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
               ┌───────┴───────┐
               │               │
               ▼               ▼
        ┌────────────┐  ┌──────────────┐
        │ AUTO-MERGE  │  │  ESCALATE    │
        │ All 6 steps │  │ Requires     │
        │ pass        │  │ claude: true │
        │ No flag     │  │ >3 retries   │
        └────────────┘  │ Architecture  │
                        │ drift         │
                        └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ 4. CLAUDE GATE   │
                    │ Architecture      │
                    │ review only      │
                    │ PASS / FAIL      │
                    └──────────────────┘
```

### What each model does

| Model | Role | Input | Output | Frequency |
|-------|------|-------|--------|-----------|
| **Claude (Architect)** | Design system, verify overall | SSOT, evidence chain | Pack specs, verdicts | ~5% of tasks |
| **DeepSeek (Packer)** | Build context packs, summarize | SSOT, requirements | ACP packs, summaries | ~15% of tasks |
| **GPT (Executor)** | Implement from contract | ACP pack | Code + tests | ~80% of tasks |
| **GPT (Verifier)** | Verify single task | ACP pack + output | PASS/FAIL | Every task |

---

## 6. Pack Generation Strategy

> *"Ai build pack?" — là câu hỏi trước khi ai execute pack.*

ACP nhận thức rõ đây là bottleneck và thiết kế **two-phase approach** để scale từ 22 tasks lên 500+ mà không sập.

### Phase 1: Hand-authored with checklist (<50 tasks)

```
Claude Code đọc SSOT → viết pack tay → checklist enforce consistency
                            ↓
               Layer-zero, anti_patterns, invariants
               được ghi theo template mental model
                            ↓
               Explicit bottleneck: O(~10 phút/pack)
               Nhưng 22 tasks × 10 phút = 3.7 tiếng → acceptable
```

**Cơ chế:** Checklist thay vì automation. Mỗi pack phải pass self-review checklist trước khi commit:

```yaml
checklist:
  - layer_zero.what_is_this: "1 paragraph, no project jargon"
  - contract.invariants: "≥2 business rules that would catch common errors"
  - execution.forbidden: "covers known anti-patterns from past failures"
  - handshake.success_criteria: "every criterion has auto: true or explicit skip_if"
  - acceptance_criteria.objective: "≥3 machine-verifiable checks"
```

**Tại sao không automate ngay?**
- SSOT đang hình thành (chưa stable schema để extract)
- Chưa biết template nào hiệu quả — cần human iteration để discovery
- 22 tasks × 10 phút = ~3.7 tiếng — không phải bottleneck lớn nhất

### Phase 2: Auto-generated from SSOT (>50 tasks)

```
DeepSeek đọc SSOT → template extraction → ACP pack
                            ↓
  layer_zero.project_context = template, not free-text paragraph
  "{{project.name}} is a {{project.type}} using {{project.stack}}"
                            ↓
  extraction_rule recorded during Phase 1 drives automation
  "map SSOT entity 'Memo' → output_schema. FK from relationship 'belongs_to'"
```

**Template extraction rule** thay vì free-text paragraph:

```yaml
# Phase 1: human note
extraction_rule: "map SSOT entity 'Memo' → output_schema fields"

# Phase 2: executable template
extraction_rule:
  source: "ssot/02-domain.yaml"
  selector: "entities[?name == 'Memo']"
  mapping:
    fields: "entity.attributes → contract.output_schema.fields"
    invariants: "entity.relationships → FK invariants"
    description: "entity.description → layer_zero.what_is_this"
```

### Accumulation principle

Mỗi pack hand-written ở Phase 1 **phải** ghi lại `extraction_rule` (dù chỉ là note 1 dòng). Qua 30-40 packs, các extraction rules này hợp thành template catalog đủ để Phase 2 tự động hóa.

| | Phase 1 | Phase 2 |
|---|---|---|
| **Method** | Hand + checklist | DeepSeek auto-gen |
| **Scale** | <50 tasks | 50+ tasks |
| **Consistency** | Checklist-enforced | Template-enforced |
| **Bottleneck** | Human time (10 min/pack) | SSOT quality |
| **Key artifact** | extraction_rule note | extraction template |

---

## 6. The Handshake

The handshake is what makes ACP a **protocol** rather than a **prompt format**.

### How it works

```
Model A produces output → output goes through verification pipeline
                       → interface_signature is computed
                       → evidence entry is appended
                       
Model B reads evidence chain → checks interface_signature match
                            → reads success_criteria verdicts
                            → knows EXACTLY what happened
```

### What the handshake verifies

```yaml
handshake:
  interface_signature: "sha256 of normalized field signatures"
  
  success_criteria:
    - output matches output_schema → PASS
    - all invariants hold → PASS
    - no contract violations → PASS
  
  acceptance_criteria:
    # 95% machine-decidable — validator enforces automatically
    objective_acceptance:
      - All repositories inherit BaseRepository                    → PASS
      - Zero direct database calls in service layer                → PASS
      - Core path test coverage ≥ 80%                              → NOT_RUN
      - No forbidden patterns (subprocess, eval, os.system)        → PASS
      - Output matches interface_signature                         → PASS
    
    # 5% reviewer-dependent — Claude/human decides
    subjective_acceptance:
      - Code readability and maintainability                       → PENDING
      - Architectural consistency with SSOT vision                 → PENDING
```

**Key property:** Model B does not need to re-read Model A's output. It reads the handshake result and knows:
- Whether the contract was fulfilled (success criteria)
- Which criteria are machine-decided and which need review (acceptance split)
- Where to continue

### Why the split matters

Before split:
> `human_review` — entropy enters the system. Claude A says "fine", Claude B says "refactor".

After split:
> 95% of criteria are **auto-verified** — machine-decidable, zero opinion.
> 5% explicitly flagged as **subjective** — the system acknowledges they need judgment, and minimizes them.

This is the difference between "we'll figure it out in review" and "we know exactly what's left to decide."

---

## 7. Validator-First Architecture

> **Prompt is a hint. Validator is the law.**

### The Pattern

```
LLM → Schema Validator → Auto Repair → Schema Validator → PASS
       ↑_________ validation error feedback loop __________│
```

### Why this works when models change

When OpenAI updates GPT free (changes behavior, degrades instruction following):

| Component | Effect |
|-----------|--------|
| **Prompt** | Accuracy drops |
| **Validator** | Accuracy unchanged |

The validator is **independent of the model**. Schema validation runs the same code regardless of which model produced the output.

### The validator pyramid

```
                    ┌──────────┐
                    │ INTEGRA- │  ← Catches logic errors (human-defined)
                    │  TION    │
                    │  TESTS   │
                   ┌┴──────────┴┐
                   │ INVARIANT  │  ← Catches business rule violations
                   │ VALIDATOR  │
                  ┌┴────────────┴┐
                  │   SCHEMA    │  ← Catches structural mismatches
                  │  VALIDATOR  │
                 ┌┴──────────────┴┐
                 │  SYNTAX CHECK │  ← Catches compilation errors
                 └───────────────┘
```

**Each layer catches failures the layer above misses.**

---

## 8. Decision Provenance

> *"6 weeks later, Claude reads the code and wonders: why was it built this way?"*

Decision provenance answers that question.

### What gets recorded

```yaml
decisions:
  - decision_id: DEC-001
    question: "Should repository return null or Result<T>?"
    alternatives:
      - null
      - Result<T>
    selected: Result<T>
    rationale: "Project rule: errors returned, not thrown"
    impact:
      affects: [memory_repository, card_repository, user_repository]
```

### Why this matters

Without decision provenance:
> Code is a sequence of arbitrary choices. Every refactor is archaeology.

With decision provenance:
> Code is a sequence of justified choices. Every refactor starts with rationale.

### For cold-read Claude sessions

Claude opens the project 6 weeks later and reads:
- `identity.pack_id` → which task this is
- `decisions[].rationale` → why it exists in this form
- `evidence.execution_trail` → what happened during execution

**Claude understands the architecture in 2 minutes, not 2 hours.**

---

## 9. Model Routing & Cost

### Routing logic

```yaml
cost_governor:
  model_routing:
    recommended: "gpt-4o-free"  # default: free resource
    fallback_chain:
      - "gpt-4o-free"           # $0
      - "deepseek API"          # $0.003
      - "gpt-4o-mini API"       # $0.01
      - "claude-sonnet API"     # $0.03-0.05
```

### When to use which

| Model | Best for | Cost | Notes |
|-------|----------|------|-------|
| **GPT free** | Execution (80% of tasks) | $0 | Unlimited, goldfish brain |
| **DeepSeek** | Packing, summarization | $0.003/task | Structured output, cheap |
| **GPT API** | Fallback when free fails | $0.01/task | Reliable, consistent |
| **Claude** | Architecture, gate | $0.03-0.05 | Strategic decisions only |

### Budget constraints

One ACP pack is designed to fit within:
- **Max 2000 tokens input** (the pack itself)
- **Max 3000 tokens output** (code/tests)
- **Max 5000 tokens total** (self-contained)

This ensures any model — including GPT free with its limited context — can process it.

---

## 10. Failure Handling

### Failure taxonomy

| Pattern | Detection | Recovery | Needs Claude? |
|---------|-----------|----------|---------------|
| Interface mismatch | Schema validator | Auto-repair (3x) | No |
| Logic violation | Invariant runner | Auto-repair (2x) | No |
| Architecture drift | Rule enforcer | Escalate | **Yes** |
| Ambiguous requirement | Invariant failure | Escalate | **Yes** |
| Dependency conflict | Rule enforcer | Reject | **Yes** |

### Circuit breaker

```
5 failures in 60 minutes → pause chain → notify human
```

### The 80/20 rule

- **80% of failures** → auto-repair → resolve without human
- **15% of failures** → auto-reject → need new contract
- **5% of failures** → escalate → need Claude/human review

---

## 11. Cold-Start Guarantee

> *"A model that has never seen this project can execute this task correctly."*

### Requirements

For a pack to be "cold-start compatible":
1. `layer_zero.project_context` must answer "what is this project?" in 1 paragraph
2. `contract.input_schema` must define every input field with constraints
3. `contract.output_schema` must define every output field with constraints
4. `execution.dependencies.files_read` must list all context files needed
5. `execution.dependencies.files_written` must list all target files
6. `layer_zero.anti_patterns` must list all forbidden patterns
7. `handshake.success_criteria` must define what counts as done

### Test

```
Give this pack to a model with zero project context.
If it produces correct output → pack passes cold-start test.
If it asks "what is this?" or makes wrong assumptions → pack fails.
```

---

## 12. Comparison: ACP vs. Other Approaches

| | Traditional Prompt | Context Pack (v1) | ACP |
|--|------------------|-------------------|-----|
| **Core mechanism** | Instruction following | Structured input | **Contract + Validator** |
| **Determinism** | None (model-dependent) | Partial (format helps) | **Structural + Semantic** |
| **Verification** | Human review | Human review | **Automated pipeline** |
| **Cold-start** | Impossible | Possible with docs | **Guaranteed by design** |
| **Model coupling** | Tight | Loose | **Decoupled** |
| **Failure handling** | "Try again" | Retry | **Known patterns + recovery** |
| **Cost control** | None | Implicit | **Explicit governor** |
| **Audit trail** | Chat history | Git log | **Evidence chain** |
| **Scalability** | Linear to convos | Near-linear | **Logarithmic to Claude** |

---

## 13. FAQ

### Q: Does ACP require all 12 layers every time?

No. Minimum viable pack is **Layers 0-3** (Identity + Contract + Handshake + Execution). The other layers are situational.

### Q: What if the model ignores the contract?

The **validator enforces** it. If schema mismatches → auto-repair or escalate. The model doesn't get to "ignore" the contract — the pipeline catches it.

### Q: Can I use ACP with a single model?

Yes. ACP works as a single-model framework too — the contract is still better than a prompt even for one model.

### Q: What about non-deterministic LLM output?

ACP doesn't make output deterministic. It makes the **interface deterministic**. The output values can vary; the output shape must not.

### Q: How does this handle model updates?

When a model updates, prompt accuracy drops. But **validator accuracy stays the same**. The system degrades gracefully — more auto-repair cycles, same quality floor.

### Q: Is ACP over-engineered for small projects?

Yes — for <5 tasks, just use prompts. ACP starts paying off at ~10+ tasks when coordination overhead exceeds execution overhead.

### Q: What are the known gaps in ACP v1.0?

Two implementation-level gaps are acknowledged but not resolved in this spec:

**Gap 1 — `interface_signature` normalization is underspecified.**
The handshake layer defines `algorithm: normalized_schema_hash` without pinning the normalization standard. If two validators serialize fields in different orders (alphabetical vs. declaration order), they produce different hashes for the same schema — breaking the handshake.

*Status:* Pinned for implementation-time resolution. Candidates: JSON Canonicalization Scheme (RFC 8785), alphabetical deterministic ordering, protobuf-style schema fingerprint.

**Gap 2 — Invariant expressions are pseudo-code, not executable.**
`"all(output.items, lambda x: x.id is not None)"` looks like Python but has no execution engine. The "validator is law" principle requires invariants to be machine-enforceable, but v1.0 leaves the engine unspecified.

*Status:* Pinned for implementation-time resolution. Candidates: Python eval() with sandbox, Pydantic model validators, JSONPath expressions.

Both gaps are implementation details, not protocol flaws. The contract interface is stable; the execution engine is what needs building.

### Q: What if GPT free changes policy or dies?

ACP treats GPT free as the **default execution tier, not the only tier**. The fallback chain (`GPT free → DeepSeek API → GPT-4o-mini API → Claude API`) ensures continuity.

If GPT free becomes unreliable:
- **Per-task cost:** $0 → ~$0.01 (GPT-4o-mini)
- **Per-22-tasks cost:** $0 → ~$0.22
- **Protocol impact:** Zero. Contract format unchanged. Validator unchanged. Only the model label changes.
- **Pack design impact:** Minimal. GPT-4o-mini API has longer context, so pack budgets can expand — but the protocol prefers staying lean for compatibility.

The philosophy: **free while it works, cheap when it doesn't.**

---

## 14. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-17 | Initial specification |

---

## License

ACP is a methodology, not a product. Use freely, modify as needed, credit appreciated.

> *"No AI is memory. Git is source of truth. Contract is interface. Validator is law."*
