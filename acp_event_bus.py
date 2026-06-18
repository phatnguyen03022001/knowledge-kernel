"""
acp_event_bus.py

Knowledge OS Event Bus Runtime

Features
--------
1. Subscription Loader
   - Loads YAML subscriptions from:
     kernel/governance/subscriptions/

2. Event Matcher
   - Resolves event type -> ACP handlers

3. Scheduler
   - Sequential ACP execution via acp_runner.run_pack()

4. Listen Mode
   - Polls runtime/event-store/
   - Finds unprocessed events
   - Executes matching handlers
   - Tracks processed events

5. Single Run Mode
   - Execute event manually

Requirements
------------
- File based
- No DB
- No network

Dependencies
------------
- pyyaml
- pathlib
- time
- os
- argparse
- datetime

Integration
-----------
Requires:

from acp_runner import run_pack

Usage
-----
Listen Mode:

    python3 acp_event_bus.py --listen

Manual Event:

    python3 acp_event_bus.py \
        --event-type ssot.updated

Custom Poll Interval:

    python3 acp_event_bus.py \
        --listen \
        --interval 5
"""

import os
import time
import yaml
import copy
import argparse

from pathlib import Path
from datetime import datetime

from acp_runner import run_pack

# ============================================================================
# Constants
# ============================================================================

SUBSCRIPTION_DIR = Path(
    "kernel/governance/subscriptions"
)

EVENT_STORE_DIR = Path(
    "runtime/event-store"
)

EVENT_BUS_DIR = Path(
    "runtime/event-bus"
)

PROCESSED_DIR = EVENT_BUS_DIR / "processed"
DLQ_DIR = EVENT_BUS_DIR / "dlq"

DEFAULT_INTERVAL = 3

DEV_MODE = (
    os.environ.get(
        "KNOWLEDGE_OS_DEV",
        "0"
    )
    == "1"
)


# ============================================================================
# Utility
# ============================================================================

def ensure_dirs() -> None:
    """Create runtime directories."""

    EVENT_BUS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    DLQ_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def utc_now() -> str:
    """UTC timestamp."""

    return (
        datetime.utcnow()
        .isoformat()
        + "Z"
    )


def load_yaml(path: Path):
    """Load YAML file."""

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data):
    """Save YAML file."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False
        )


# ============================================================================
# Subscription Runtime
# ============================================================================

class SubscriptionRegistry:
    """
    Event -> Handler mapping.

    Example:

    correction.approved:
      handlers:
        - pack: update-ssot

    ssot.updated:
      handlers:
        - pack: validate-graph
        - pack: refresh-health
    """

    def __init__(self):
        self.mapping = {}

    def load(self):
        """
        Load all subscriptions.
        """

        self.mapping = {}

        if not SUBSCRIPTION_DIR.exists():
            return

        for file in sorted(
            SUBSCRIPTION_DIR.glob("*.yaml")
        ):

            try:
                doc = load_yaml(file)

                if not doc:
                    continue

                event_type = doc.get(
                    "event"
                )

                handlers = doc.get(
                    "handlers",
                    []
                )

                if not event_type:
                    continue

                self.mapping.setdefault(
                    event_type,
                    []
                )

                self.mapping[
                    event_type
                ].extend(
                    handlers
                )

            except Exception as e:
                print(
                    f"[WARN] Failed loading "
                    f"{file}: {e}"
                )

    def match(self, event_type):
        """
        Resolve event handlers.
        """

        return self.mapping.get(
            event_type,
            []
        )

    def dump(self):
        """Debug helper."""

        return self.mapping


# ============================================================================
# Event Discovery
# ============================================================================

def discover_event_files():
    """
    Discover all event files.

    Returns sorted list.
    """

    if not EVENT_STORE_DIR.exists():
        return []

    files = list(
        EVENT_STORE_DIR.rglob(
            "evt-*.yaml"
        )
    )

    return sorted(files)


def load_event(event_path: Path):
    """
    Load event envelope.
    """

    return load_yaml(event_path)


# ============================================================================
# Processed Event Tracking
# ============================================================================

def processed_marker_path(
    event_id: str
) -> Path:
    """
    Marker path.
    """

    return (
        PROCESSED_DIR
        / f"{event_id}.yaml"
    )


def is_processed(
    event_id: str
) -> bool:
    """
    Check processed.
    """

    return (
        processed_marker_path(
            event_id
        ).exists()
    )


def mark_processed(
    event_id: str,
    event_type: str
):
    """
    Mark processed.
    """

    save_yaml(
        processed_marker_path(
            event_id
        ),
        {
            "event_id": event_id,
            "event_type": event_type,
            "processed_at": utc_now()
        }
    )


def write_dlq(
    event_id: str,
    event_type: str,
    event_doc
):
    """
    Write failed event to
    Dead Letter Queue.
    """

    dlq_path = (
        DLQ_DIR
        / f"{event_id}.yaml"
    )

    save_yaml(
        dlq_path,
        {
            "event_id": event_id,
            "event_type": event_type,
            "original_event": event_doc,
            "failed_at": utc_now()
        }
    )


# ============================================================================
# Context Builder
# ============================================================================

def build_context_from_event(
    event_doc
):
    """
    Convert event payload
    into ACP context.
    """

    payload = (
        event_doc.get(
            "payload",
            {}
        )
    )

    if not isinstance(payload, dict):
        print(
            "[WARN] Event payload "
            "is not a dict — "
            "using empty context"
        )
        payload = {}

    metadata = (
        event_doc.get(
            "metadata",
            {}
        )
    )

    context = {}

    context.update(payload)

    context["_event"] = event_doc

    context["_event_id"] = (
        event_doc.get("id")
    )

    context["_event_type"] = (
        event_doc.get("type")
    )

    context["_correlation_id"] = (
        metadata.get(
            "correlation_id"
        )
    )

    #
    # Dev-mode governance tokens
    # Only injected when
    # KNOWLEDGE_OS_DEV=1.
    # Production must supply
    # real tokens via event
    # payload.
    #
    if DEV_MODE:
        context.setdefault(
            "domain_owner_token",
            {
                "role":
                    "domain_owner",
                "domain":
                    "default",
                "approved":
                    True,
                "signed_at":
                    utc_now()
            }
        )

        context.setdefault(
            "system_guardian_token",
            {
                "role":
                    "system_guardian",
                "approved":
                    True,
                "signed_at":
                    utc_now()
            }
        )

    #
    # Dev-mode validator context
    #
    if DEV_MODE:
        context.setdefault(
            "graph",
            {
                "nodes": [
                    {
                        "id": "root",
                        "root": True,
                        "incoming_links": 0
                    }
                ]
            }
        )

    context.setdefault(
        "ownership",
        {
            "valid": True
        }
    )

    return context


# ============================================================================
# Scheduler
# ============================================================================

class EventScheduler:
    """
    Sequential scheduler.
    """

    def __init__(
        self,
        registry: SubscriptionRegistry
    ):
        self.registry = registry

    def resolve_handlers(
        self,
        event_type: str
    ):
        """
        Resolve matching handlers.
        """

        return self.registry.match(
            event_type
        )

    def execute_handler(
        self,
        handler,
        context
    ):
        """
        Execute ACP pack.

        Returns True on success,
        False on failure.
        """

        pack_name = handler.get(
            "pack"
        )

        if not pack_name:
            return True

        pack_path = (
            Path("starter-packs")
            / f"{pack_name}.yaml"
        )

        if not pack_path.exists():

            alt = Path(pack_name)

            if alt.exists():
                pack_path = alt
            else:
                print(
                    "[WARN] Pack not found:",
                    pack_name
                )
                return False

        print(
            f"[PACK] "
            f"{pack_path}"
        )

        try:

            _, status = run_pack(
                str(pack_path),
                copy.deepcopy(context)
            )

            print(
                "[RESULT]",
                status
            )

            return True

        except Exception as e:

            print(
                "[ERROR]",
                pack_name,
                e
            )

            return False

    def process_event(
        self,
        event_doc
    ):
        """
        Execute handlers.

        Only marks event processed
        when ALL handlers succeed.
        Failed events go to DLQ.
        """

        event_type = (
            event_doc.get(
                "type"
            )
        )

        event_id = (
            event_doc.get(
                "id"
            )
        )

        handlers = (
            self.resolve_handlers(
                event_type
            )
        )

        if not handlers:

            print(
                f"[NO MATCH] "
                f"{event_type}"
            )

            mark_processed(
                event_id,
                event_type
            )

            return

        print(
            f"[EVENT] "
            f"{event_type}"
        )

        context = (
            build_context_from_event(
                event_doc
            )
        )

        all_succeeded = True

        for handler in handlers:
            ok = self.execute_handler(
                handler,
                context
            )
            if not ok:
                all_succeeded = False

        if all_succeeded:
            mark_processed(
                event_id,
                event_type
            )
        else:
            print(
                f"[DLQ] "
                f"{event_type} "
                f"({event_id}) — "
                f"one or more handlers "
                f"failed"
            )
            write_dlq(
                event_id,
                event_type,
                event_doc
            )


# ============================================================================
# Listen Runtime
# ============================================================================

def process_unhandled_events(
    registry
):
    """
    Scan event store.
    """

    scheduler = EventScheduler(
        registry
    )

    files = (
        discover_event_files()
    )

    for file in files:

        try:

            event_doc = load_event(
                file
            )

            if not event_doc:
                continue

            event_id = (
                event_doc.get(
                    "id"
                )
            )

            if not event_id:
                continue

            if is_processed(
                event_id
            ):
                continue

            scheduler.process_event(
                event_doc
            )

        except Exception as e:

            print(
                f"[ERROR] "
                f"{file}: {e}"
            )


def listen_loop(
    interval
):
    """
    Polling event bus.
    """

    registry = (
        SubscriptionRegistry()
    )

    registry.load()

    print(
        "[EVENT BUS] "
        "Listening..."
    )

    print(
        "[SUBSCRIPTIONS]",
        len(registry.mapping)
    )

    while True:

        try:

            process_unhandled_events(
                registry
            )

        except Exception as e:

            print(
                "[LOOP ERROR]",
                e
            )

        time.sleep(interval)


# ============================================================================
# Manual Event Mode
# ============================================================================

def run_manual_event(
    event_type
):
    """
    Execute event manually
    without reading event store.
    """

    registry = (
        SubscriptionRegistry()
    )

    registry.load()

    handlers = (
        registry.match(
            event_type
        )
    )

    if not handlers:

        print(
            "[NO SUBSCRIPTION]",
            event_type
        )

        return

    event_doc = {
        "id":
            f"manual-{utc_now()}",
        "type":
            event_type,
        "timestamp":
            utc_now(),
        "payload": {},
        "metadata": {}
    }

    scheduler = (
        EventScheduler(
            registry
        )
    )

    scheduler.process_event(
        event_doc
    )


# ============================================================================
# CLI
# ============================================================================

def main():

    ensure_dirs()

    parser = argparse.ArgumentParser(
        description=
        "Knowledge OS Event Bus"
    )

    parser.add_argument(
        "--listen",
        action="store_true"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL
    )

    parser.add_argument(
        "--event-type",
        help="Manual event"
    )

    parser.add_argument(
        "--pack",
        help="Compatibility argument"
    )

    args = parser.parse_args()

    if args.listen:

        listen_loop(
            args.interval
        )

        return

    if args.event_type:

        run_manual_event(
            args.event_type
        )

        return

    parser.print_help()


if __name__ == "__main__":
    main()
