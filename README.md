# Knowledge Kernel

Event-sourced, governance-bound, AI-executable knowledge kernel.

Not a document system or project structure — an operating system for AI-driven knowledge workflows.

## Architecture

```
Foundation → Governance → ACP Packs → Knowledge → Archive
```

- **Event-sourced** — all state changes via immutable correction events
- **Governance-bound** — 3-tier authority (Authors, Domain Owners, System Guardian)
- **AI-executable** — ACP (Agent Contract Protocol) for deterministic multi-agent execution
- **Deterministic pipeline** — M1 Validator → M2.1 Diagnostics → M3 Auditor → M4 Arbiter
- **Frozen ontology** — 12 diagnostic categories, locked by contract tests

## Quick Start

```bash
# Health check — full M1→M4 pipeline in one command
python3 cli/health.py
python3 cli/health.py --json     # CI-friendly JSON output

# Run all tests (scenarios + contract tests)
python3 tests/harness.py --all

# Validate knowledge graph
python3 acp_runner.py validate-graph

# Event bus (dev mode)
python3 acp_event_bus.py --listen
```

## Test Suite

```
15 tests, 0 failures

Scenarios (7):  chaos-cold-start, chaos-invalid-graph, chaos-partial-validity,
                chaos-validator-kill, refresh-health-only, update-ssot-flow,
                validate-graph-only

Contracts (8):  test_action_lock      — FM-ARCH-002: 4 actions enforced
                test_determinism       — C1/C2: pipeline determinism certified
                test_escalation_events — ADR-004: event communication channel
                test_failure_injection — D1/D2/D3: failure mode classification
                test_health            — CLI: human + JSON output, trace recording
                test_layer_isolation   — A1: import allowlist across all layers
                test_ontology_freeze   — B1/B2/B3: 12-category lock
                test_policy_format     — FM-ARCH-001: policy structure enforced
```

## Pipeline

```
M1 Validator    — deterministic constraint engine (42 invariants, ~750 lines)
M2 Tracer       — append-only trace recorder (causal chain, immutable)
M2.1 Projection — pure view compiler (timeline, trends, snapshots)
M2.2 Diagnostics — violation normalizer (12 categories, fingerprinting)
M3 Auditor      — stateless policy engine (15 policies, 3 types)
M4 Arbiter      — deterministic action router (4 actions: NONE|MONITOR|BLOCK|ESCALATE)
```

## Structure

```
kernel/          ← Invariant. Kernel-managed.
  runtime/       ← M1–M4 pipeline + tracer + projection
  foundation/    ← Events, invariants, contracts, concept registry
  governance/    ← Policies, subscriptions, escalation policy
starter-packs/   ← ACP pack templates
adapters/        ← Swappable (file / postgres / cloud)
plugins/         ← Optional (AI, dashboard, B2B, B2C)
cli/             ← knowledge-os CLI (health check)
tests/
  contracts/     ← ADR enforcement tests (8 files, 1 README)
  scenarios/     ← YAML scenario tests (7 files)
```

## Bootstrap Phases

| Phase | Timeline | Description |
|-------|----------|-------------|
| 🟢 Phase 0 | Day 0 | Seed Authority — define domains, assign owners |
| 🟡 Phase 1 | Day 1–7 | Domain Bootstrap — owners begin operating |
| 🔵 Phase 2 | Day 7+ | Distributed Governance — seed becomes observer |

## Architecture Decision Records

| ADR | Decision | Enforcement |
|-----|----------|-------------|
| ADR-001 | Validator is deterministic constraint engine | `test_determinism.py`, `test_layer_isolation.py` |
| ADR-002 | Projection is pure view compiler | `test_determinism.py`, `test_layer_isolation.py` |
| ADR-003 | Auditor must not create ontology | `test_ontology_freeze.py`, `test_layer_isolation.py` |
| ADR-004 | Arbiter is externalized, event-driven | `test_action_lock.py`, `test_escalation_events.py` |
| ADR-005 | Architecture closed, failure modes documented | `test_policy_format.py`, `test_action_lock.py` |

## License

MIT
