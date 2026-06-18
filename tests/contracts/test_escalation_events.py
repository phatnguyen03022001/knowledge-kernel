#!/usr/bin/env python3
"""
Escalation Event Flow Verification — ADR-004

Verifies the escalation event communication channel:
  1. escalation.created and escalation.resolved exist in event-types.yaml
  2. The subscription for escalation.created exists and is loadable
  3. The arbiter-resolve pack exists and follows pack schema
  4. Arbiter.emit_to_event_store() produces valid event envelopes
  5. SubscriptionRegistry loads escalation.created handlers
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# TEST 1: Event types exist
# ============================================================================

def test_escalation_types_exist():
    """Verify escalation.created and escalation.resolved are defined."""
    from acp_event_bus import load_yaml

    types_path = PROJECT_ROOT / "kernel" / "foundation" / "events" / "event-types.yaml"
    assert types_path.exists(), "event-types.yaml not found"

    doc = load_yaml(types_path)
    event_types = doc.get("event-types", [])
    type_ids = {e.get("id") for e in event_types}

    assert "escalation.created" in type_ids, \
        "escalation.created not defined in event-types.yaml"
    assert "escalation.resolved" in type_ids, \
        "escalation.resolved not defined in event-types.yaml"

    print(f"  [OK] escalation.created and escalation.resolved defined in event-types.yaml")


# ============================================================================
# TEST 2: Subscription exists
# ============================================================================

def test_escalation_subscription_exists():
    """Verify subscription for escalation.created exists and is loadable."""
    from acp_event_bus import load_yaml

    sub_path = PROJECT_ROOT / "kernel" / "governance" / "subscriptions" / "escalation-arbiter.yaml"
    assert sub_path.exists(), "escalation-arbiter.yaml subscription not found"

    doc = load_yaml(sub_path)

    assert doc.get("event") == "escalation.created", \
        f"Subscription event should be escalation.created, got {doc.get('event')}"

    handlers = doc.get("handlers", [])
    assert len(handlers) >= 1, "Subscription must have at least 1 handler"
    assert any(h.get("pack") == "arbiter-resolve" for h in handlers), \
        "Subscription must route to arbiter-resolve pack"

    print(f"  [OK] escalation-arbiter.yaml subscription exists and routes to arbiter-resolve")


# ============================================================================
# TEST 3: Pack exists
# ============================================================================

def test_arbiter_resolve_pack_exists():
    """Verify arbiter-resolve pack exists and has valid structure."""
    from acp_event_bus import load_yaml

    pack_path = PROJECT_ROOT / "starter-packs" / "arbiter-resolve.yaml"
    assert pack_path.exists(), "arbiter-resolve.yaml pack not found"

    doc = load_yaml(pack_path)

    assert doc.get("id") == "arbiter-resolve", \
        f"Pack id should be arbiter-resolve, got {doc.get('id')}"
    assert doc.get("version") is not None, "Pack must have version"

    steps = doc.get("execution", {}).get("steps", [])
    assert len(steps) >= 1, "Pack must have at least 1 execution step"

    # Verify expected steps are present
    step_names = [s for s in steps if isinstance(s, str)]
    assert "extract_audit_report" in step_names, \
        f"Missing step: extract_audit_report, got {step_names}"
    assert "invoke_arbiter" in step_names, \
        f"Missing step: invoke_arbiter, got {step_names}"
    assert "write_escalation_resolved" in step_names, \
        f"Missing step: write_escalation_resolved, got {step_names}"

    print(f"  [OK] arbiter-resolve.yaml pack exists with {len(steps)} steps")


# ============================================================================
# TEST 4: emit_to_event_store produces valid event envelope
# ============================================================================

def test_arbiter_emit_to_event_store():
    """Verify Arbiter.emit_to_event_store produces a valid event envelope."""
    from kernel.runtime.arbiter import Arbiter

    # Build a mock audit object
    MockAudit = type('MockAudit', (object,), {})
    mock_audit = MockAudit()
    mock_audit.audit_id = 'test-audit-001'
    mock_audit.verdict = 'PASS'
    mock_audit.risk_score = 0.0
    mock_audit.policy_hits = []

    arb = Arbiter()
    resolution = arb.route(mock_audit)
    event = arb.emit_to_event_store(resolution)

    # Verify event envelope structure
    assert "id" in event, "Event missing 'id'"
    assert event.get("type") == "escalation.resolved", \
        f"Event type should be escalation.resolved, got {event.get('type')}"
    assert "timestamp" in event, "Event missing 'timestamp'"
    assert "source" in event, "Event missing 'source'"
    assert event["source"].get("component") == "arbiter", \
        f"Event source.component should be arbiter, got {event['source'].get('component')}"
    assert "payload" in event, "Event missing 'payload'"
    assert event["payload"].get("action") == "NONE", \
        f"Payload action should be NONE (PASS verdict), got {event['payload'].get('action')}"
    assert "metadata" in event, "Event missing 'metadata'"
    assert event.get("version") == 1, "Event version should be 1"

    # Verify event was written to disk (filenames use sequence, not UUID)
    from acp_runner import EVENT_STORE_DIR
    import datetime as _dt
    today = _dt.datetime.utcnow()
    day_dir = EVENT_STORE_DIR / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.day:02d}"
    event_files = sorted(day_dir.glob("evt-*.yaml")) if day_dir.exists() else []
    assert len(event_files) >= 1, f"No event files found in {day_dir}"

    # The most recent file should be an escalation.resolved event
    import yaml as _yaml
    last_event = None
    for ef in reversed(event_files):
        with open(ef) as fh:
            doc = _yaml.safe_load(fh)
        if doc and doc.get("type") == "escalation.resolved":
            last_event = doc
            break
    assert last_event is not None, "No escalation.resolved event found on disk"
    assert last_event["payload"].get("action") == "NONE", \
        f"Payload action should be NONE, got {last_event['payload'].get('action')}"

    print(f"  [OK] Arbiter.emit_to_event_store produces valid escalation.resolved event (id={event['id'][:8]}...)")


# ============================================================================
# TEST 5: SubscriptionRegistry loads escalation handlers
# ============================================================================

def test_subscription_registry_loads():
    """Verify SubscriptionRegistry can load escalation.created handlers."""
    from acp_event_bus import SubscriptionRegistry

    registry = SubscriptionRegistry()
    registry.load()

    # dump() returns {event_type: [handlers, ...]}
    mapping = registry.dump()
    assert "escalation.created" in mapping, \
        "escalation.created not in subscription registry mapping"

    handlers = registry.match("escalation.created")
    assert len(handlers) >= 1, \
        f"escalation.created should have at least 1 handler, got {len(handlers)}"

    # At least one handler should route to arbiter-resolve
    has_arbiter = any(
        h.get("pack") == "arbiter-resolve" or h.get("handler") == "arbiter-resolve"
        for h in handlers
    )
    assert has_arbiter, "No handler routes to arbiter-resolve"

    print(f"  [OK] SubscriptionRegistry loads escalation.created with {len(handlers)} handler(s)")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_escalation_types_exist()
    test_escalation_subscription_exists()
    test_arbiter_resolve_pack_exists()
    test_arbiter_emit_to_event_store()
    test_subscription_registry_loads()
    print(f"\n  [PASS] Escalation event flow verified — ADR-004 enforced")
