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

## Quick Start

```bash
# Run all tests
python3 tests/harness.py --all

# Validate knowledge graph
python3 acp_runner.py validate-graph

# Event bus (dev mode)
python3 acp_event_bus.py --listen
```

## Structure

```
kernel/          ← Invariant. Kernel-managed.
starter-packs/   ← ACP pack templates
adapters/        ← Swappable (file / postgres / cloud)
plugins/         ← Optional (AI, dashboard, B2B, B2C)
cli/             ← knowledge-os CLI
```

## Bootstrap Phases

| Phase | Timeline | Description |
|-------|----------|-------------|
| 🟢 Phase 0 | Day 0 | Seed Authority — define domains, assign owners |
| 🟡 Phase 1 | Day 1–7 | Domain Bootstrap — owners begin operating |
| 🔵 Phase 2 | Day 7+ | Distributed Governance — seed becomes observer |

## License

MIT
