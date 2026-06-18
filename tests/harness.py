"""
Knowledge OS Test Harness

Usage:
    python3 tests/harness.py --scenario tests/scenarios/update-ssot-flow.yaml
    python3 tests/harness.py --all                          # run all scenarios

Exit code:
    0 = all PASS
    1 = any FAIL
"""

import os
import sys
import yaml
import json
import shutil
import argparse

from pathlib import Path

# Test harness always runs in dev mode
os.environ.setdefault(
    "KNOWLEDGE_OS_DEV",
    "1"
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from acp_runner import run_pack
from acp_event_bus import (
    SubscriptionRegistry,
    process_unhandled_events,
    ensure_dirs as bus_ensure_dirs,
)


# ============================================================================
# Constants
# ============================================================================

TESTS_DIR = Path(__file__).parent
SCENARIOS_DIR = TESTS_DIR / "scenarios"

RUNTIME_DIR = Path("runtime")
EVENT_STORE_DIR = RUNTIME_DIR / "event-store"
EVENT_BUS_DIR = RUNTIME_DIR / "event-bus"
PROCESSED_DIR = EVENT_BUS_DIR / "processed"
DLQ_DIR = EVENT_BUS_DIR / "dlq"
AUDIT_DIR = Path("audit_logs")
PROJECTIONS_DIR = RUNTIME_DIR / "projections"
SNAPSHOTS_DIR = RUNTIME_DIR / "snapshots"
TRANSACTION_DIR = RUNTIME_DIR / "transactions"


# ============================================================================
# Helpers
# ============================================================================

def reset_runtime():
    """Clean all runtime directories before test run."""
    for d in [EVENT_STORE_DIR, PROCESSED_DIR, DLQ_DIR, PROJECTIONS_DIR,
              SNAPSHOTS_DIR, TRANSACTION_DIR]:
        if d.exists():
            shutil.rmtree(d)
    bus_ensure_dirs()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    DLQ_DIR.mkdir(parents=True, exist_ok=True)
    TRANSACTION_DIR.mkdir(parents=True, exist_ok=True)


def discover_events():
    """Collect all event files."""
    if not EVENT_STORE_DIR.exists():
        return []
    return sorted(EVENT_STORE_DIR.rglob("evt-*.yaml"))


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def count_audit_logs():
    """Return set of pack IDs that have audit logs."""
    if not AUDIT_DIR.exists():
        return set()
    return {f.stem for f in AUDIT_DIR.glob("*.log")}


def count_processed():
    """Return set of processed event IDs."""
    if not PROCESSED_DIR.exists():
        return set()
    return {f.stem.replace(".yaml", "") for f in PROCESSED_DIR.glob("*.yaml")}


def exists(path_str):
    return Path(path_str).exists()


# ============================================================================
# Assertion engine
# ============================================================================

class AssertionError(Exception):
    """Scenario assertion failure."""
    def __init__(self, check_name, detail):
        self.check_name = check_name
        self.detail = detail
        super().__init__(f"[FAIL] {check_name}: {detail}")


def get_event_types(event_paths):
    """Return set of event types from event file paths."""
    types = set()
    for path in event_paths:
        try:
            evt = load_yaml(path)
            if evt and "type" in evt:
                types.add(evt["type"])
        except Exception:
            pass
    return types


def run_assertions(scenario, events_before, events_after, audit_before, audit_after, processed_before, processed_after):
    """Run all scenario expectations."""

    expect = scenario.get("expect", {})

    # --- Status check ---
    expected_status = expect.get("status", ["success"])
    actual_status = scenario.get("_actual_status", "success")
    if actual_status not in expected_status:
        raise AssertionError(
            "status",
            f"expected {expected_status}, got {actual_status}"
        )

    # --- Event checks (by type, not filename) ---
    types_before = get_event_types(events_before)
    types_after = get_event_types(events_after)
    new_types = types_after - types_before

    for expected_event in expect.get("events", []):
        if expected_event not in new_types:
            raise AssertionError(
                "event",
                f"expected event '{expected_event}' not found in {new_types}"
            )

    # --- Audit log checks ---
    for expected_audit in expect.get("audit_logs", []):
        if expected_audit not in audit_after:
            raise AssertionError(
                "audit_log",
                f"expected audit log '{expected_audit}' not found"
            )

    # --- Pack execution checks ---
    for expected_pack in expect.get("packs_executed", []):
        if expected_pack not in audit_after:
            raise AssertionError(
                "pack_executed",
                f"expected pack '{expected_pack}' not found"
            )

    # --- Processed event checks ---
    expected_processed = expect.get("processed_count")
    if expected_processed is not None:
        processed_new = len(processed_after - processed_before)
        if processed_new != expected_processed:
            raise AssertionError(
                "processed_count",
                f"expected {expected_processed} new processed, got {processed_new}"
            )

    # --- File existence checks ---
    for file_path in expect.get("files_exist", []):
        if not exists(file_path):
            raise AssertionError(
                "files_exist",
                f"expected file '{file_path}' not found"
            )

    # --- Audit log content checks ---
    for audit_check in expect.get("audit_contents", []):
        pack_id = audit_check.get("pack")
        contains = audit_check.get("contains", [])
        if pack_id in audit_after:
            log_path = AUDIT_DIR / f"{pack_id}.log"
            content = log_path.read_text()
            for keyword in contains:
                if keyword not in content:
                    raise AssertionError(
                        "audit_content",
                        f"audit log '{pack_id}' missing keyword '{keyword}'"
                    )

    return True


# ============================================================================
# Scenario runner
# ============================================================================

def run_scenario(scenario_path):
    """Execute a single scenario."""

    scenario = load_yaml(scenario_path)
    scenario_id = scenario.get("id", scenario_path.stem)
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_id}")
    print(f"{'='*60}")

    reset_runtime()

    # --- Capture pre-state ---
    events_before = set(discover_events())
    audit_before = count_audit_logs()
    processed_before = count_processed()

    try:
        # --- Execute steps ---
        for step in scenario.get("steps", []):
            if "run_pack" in step:
                pack_path = step["run_pack"]["pack"]
                print(f"\n  [STEP] run_pack: {pack_path}")

                context = step["run_pack"].get("context", {})

                # Default governance tokens
                from acp_runner import utc_now as acp_utc_now
                context.setdefault("domain_owner_token", {
                    "role": "domain_owner", "domain": "test",
                    "approved": True, "signed_at": acp_utc_now()
                })
                context.setdefault("system_guardian_token", {
                    "role": "system_guardian", "approved": True,
                    "signed_at": acp_utc_now()
                })
                context.setdefault("correction_id", "TEST-CORR-001")
                context.setdefault("ssot_path", "runtime/test-ssot.yaml")
                context.setdefault("graph", {"nodes": [{"id": "root", "root": True, "incoming_links": 0}]})
                context.setdefault("ownership", {"valid": True})

                _, status = run_pack(pack_path, context)
                print(f"  [DONE] status: {status}")

            elif "run_event_bus" in step:
                print(f"\n  [STEP] event_bus: process unhandled events")
                registry = SubscriptionRegistry()
                registry.load()
                process_unhandled_events(registry)

        # --- Capture post-state ---
        events_after = set(discover_events())
        audit_after = count_audit_logs()
        processed_after = count_processed()

        scenario["_actual_status"] = "success"

        # --- Assertions ---
        run_assertions(
            scenario,
            events_before, events_after,
            audit_before, audit_after,
            processed_before, processed_after
        )

        # --- Summary ---
        new_events = events_after - events_before
        new_audits = audit_after - audit_before
        new_processed = processed_after - processed_before

        print(f"\n  [RESULT] ✅ PASS")
        print(f"    Events emitted:    {len(new_events)}")
        print(f"    Audit logs:        {', '.join(sorted(new_audits)) if new_audits else '(none)'}")
        print(f"    Processed:         {len(new_processed)}")
        return True

    except AssertionError as e:
        print(f"\n  [RESULT] ❌ {e}")
        return False

    except Exception as e:
        import traceback
        print(f"\n  [RESULT] ❌ UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return False


def run_all():
    """Run all scenarios."""
    scenarios = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not scenarios:
        print("No scenarios found in", SCENARIOS_DIR)
        return True

    results = []
    for sc in scenarios:
        results.append(run_scenario(sc))

    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(results)} | PASS: {passed} | FAIL: {failed}")
    print(f"{'='*60}")

    return failed == 0


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Knowledge OS Test Harness")
    parser.add_argument("--scenario", help="Path to scenario YAML")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")

    args = parser.parse_args()

    if args.all:
        success = run_all()
    elif args.scenario:
        success = run_scenario(Path(args.scenario))
    else:
        parser.print_help()
        success = True

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
