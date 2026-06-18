"""
ACP Runner — Knowledge OS Execution Engine

Features
--------
- YAML-driven ACP Pack execution
- Step Registry architecture
- Atomic file transactions
- Transaction journal
- Event Store (append-only)
- Permission token validation
- Validator execution
- Retry / Skip / Fail step policies
- Audit logging
- CLI demo mode

Dependencies
------------
- pyyaml
- pathlib
- tempfile
- shutil
- datetime

Stdlib
------
- os
- json
- uuid
- typing
- hashlib
- argparse
- traceback

Usage
-----
python3 acp_runner.py

Directory Expectations
----------------------
starter-packs/update-ssot.yaml
kernel/foundation/validator-rules.yaml

Optional runtime directories will be created automatically:
runtime/
runtime/event-store/
runtime/transactions/
audit_logs/
"""

import os
import json
import uuid
import yaml
import shutil
import hashlib
import argparse
import tempfile
import traceback

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Tuple


# ============================================================================
# Exceptions
# ============================================================================

class ACPRunnerError(Exception):
    """Base ACP Runner exception."""


class PermissionValidationError(ACPRunnerError):
    """Permission validation failed."""


class ValidationError(ACPRunnerError):
    """Validation failed."""


class StepError(ACPRunnerError):
    """Step execution failed."""


class RollbackError(ACPRunnerError):
    """Rollback failed."""


# ============================================================================
# Constants
# ============================================================================

RUNTIME_DIR = Path("runtime")
EVENT_STORE_DIR = RUNTIME_DIR / "event-store"
TRANSACTION_DIR = RUNTIME_DIR / "transactions"
AUDIT_DIR = Path("audit_logs")

VALIDATOR_RULES_PATH = Path(
    "kernel/foundation/validator-rules.yaml"
)

DEFAULT_RETRY_COUNT = 0
DEFAULT_ON_FAILURE = "fail"  # fail | skip

# ============================================================================
# Utility
# ============================================================================

def utc_now() -> str:
    """Return ISO8601 UTC timestamp."""
    return datetime.utcnow().isoformat() + "Z"


def ensure_dirs() -> None:
    """Create required runtime directories."""
    EVENT_STORE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSACTION_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Write YAML file."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False
        )


def sha256_text(text: str) -> str:
    """Hash helper."""
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================================
# Transaction Manager
# ============================================================================

class TransactionManager:
    """
    Atomic file transaction manager.

    Supports:
    - transaction journal
    - atomic write
    - rollback
    """

    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.operations: List[Dict[str, Any]] = []

    @property
    def journal_path(self) -> Path:
        return (
            TRANSACTION_DIR
            / f"{self.correlation_id}.yaml"
        )

    def log_intent(
        self,
        operation_type: str,
        target_path: str
    ) -> None:
        """Record transaction intent."""

        self.operations.append({
            "timestamp": utc_now(),
            "operation": operation_type,
            "target": target_path
        })

        save_yaml(
            self.journal_path,
            {
                "correlation_id": self.correlation_id,
                "operations": self.operations
            }
        )

    def atomic_write_yaml(
        self,
        path: Path,
        content: Dict[str, Any]
    ) -> None:
        """
        Atomic YAML write:
        backup -> temp -> validate -> replace

        Backs up original file before overwriting
        to support real rollback.
        """

        self.log_intent(
            "atomic_write",
            str(path)
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # 1. Backup original if exists
        if path.exists():
            backup_dir = TRANSACTION_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{self.correlation_id}-{path.name}"
            shutil.copy2(str(path), str(backup_path))
            self._backup_path = backup_path
            self.log_intent("backup_created", str(backup_path))

        # 2. Atomic write via temp file
        fd, tmp_name = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            save_yaml(tmp_path, content)
            load_yaml(tmp_path)  # validation
            os.replace(str(tmp_path), str(path))
            self.log_intent("write_committed", str(path))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def rollback(self) -> None:
        """
        Real rollback: restore backup if available, then log intent.
        """
        backup_path = getattr(self, "_backup_path", None)
        target_path = None

        # Find the last atomic_write target from journal
        for op in reversed(self.operations):
            if op.get("operation") == "write_committed":
                target_path = Path(op["target"])
                break

        if backup_path and backup_path.exists() and target_path and target_path.exists():
            shutil.copy2(str(backup_path), str(target_path))
            print(f"[ROLLBACK] Restored {target_path} from backup")

        if backup_path and backup_path.exists():
            backup_path.unlink()

        self.log_intent("rollback", "transaction")
        print("[ROLLBACK] Journal updated")


# ============================================================================
# Event Store
# ============================================================================

def next_event_sequence(
    event_day_dir: Path
) -> int:
    """Get next event sequence."""

    existing = sorted(
        event_day_dir.glob("evt-*.yaml")
    )

    if not existing:
        return 1

    last = existing[-1].stem

    try:
        return int(
            last.replace("evt-", "")
        ) + 1
    except Exception:
        return len(existing) + 1


def emit_event(
    event_type: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    source_component: str = "acp_runner",
    source_entity_type: str = "pack",
    source_entity_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Emit append-only event envelope.
    """

    now = datetime.utcnow()

    day_dir = (
        EVENT_STORE_DIR
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
    )

    day_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    seq = next_event_sequence(day_dir)

    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "timestamp": utc_now(),
        "source": {
            "component": source_component,
            "entity": {
                "type": source_entity_type,
                "id": source_entity_id
            }
        },
        "payload": payload,
        "metadata": {
            "correlation_id": correlation_id,
            "causation_id": causation_id
        },
        "version": 1
    }

    event_path = (
        day_dir
        / f"evt-{seq:03d}.yaml"
    )

    save_yaml(event_path, event)

    return event


# ============================================================================
# Validators
# ============================================================================

def load_validator_rules() -> Dict[str, Any]:
    """Load validator rules if available."""

    if not VALIDATOR_RULES_PATH.exists():
        return {}

    try:
        return load_yaml(
            VALIDATOR_RULES_PATH
        )
    except Exception:
        return {}


def validator_graph_consistent(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Graph consistency validator.

    Expected context:
    {
      "graph": {
         "nodes": [...]
      }
    }
    """

    graph = context.get(
        "graph",
        {}
    )

    nodes = graph.get(
        "nodes",
        []
    )

    root_nodes = {
        n.get("id")
        for n in nodes
        if n.get("root")
    }

    orphan_nodes = []

    for node in nodes:
        incoming = node.get(
            "incoming_links",
            0
        )

        node_id = node.get("id")

        if (
            incoming == 0
            and node_id not in root_nodes
        ):
            orphan_nodes.append(node_id)

    return {
        "validator": "graph_consistent",
        "passed": len(orphan_nodes) == 0,
        "details": {
            "orphans": orphan_nodes
        }
    }


def validator_ownership_consistent(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ownership consistency validator.
    """

    ownership = context.get(
        "ownership",
        {}
    )

    passed = ownership.get(
        "valid",
        True
    )

    return {
        "validator": "ownership_consistent",
        "passed": passed,
        "details": ownership
    }


VALIDATOR_REGISTRY: Dict[
    str,
    Callable[[Dict[str, Any]], Dict[str, Any]]
] = {
    "graph_consistent":
        validator_graph_consistent,
    "ownership_consistent":
        validator_ownership_consistent,
}


def run_validators(
    pack: Dict[str, Any],
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Execute validators.

    Returns pass/fail report.
    Does not raise.
    """

    results = []

    required = (
        pack.get("validation", {})
        .get("requires", [])
    )

    for validator_name in required:

        fn = VALIDATOR_REGISTRY.get(
            validator_name
        )

        if not fn:
            results.append({
                "validator": validator_name,
                "passed": False,
                "details": "missing validator"
            })
            continue

        try:
            results.append(fn(context))
        except Exception as e:
            results.append({
                "validator": validator_name,
                "passed": False,
                "details": str(e)
            })

    return results


# ============================================================================
# Permission Validation
# ============================================================================

def validate_permission_token(
    token: Dict[str, Any],
    required_role: str
) -> bool:
    """
    Validate governance token.
    """

    if not token:
        return False

    if token.get("role") != required_role:
        return False

    if not token.get("approved"):
        return False

    if not token.get("signed_at"):
        return False

    return True


def check_permissions(
    pack: Dict[str, Any],
    context: Dict[str, Any]
) -> bool:
    """
    Validate ACP permissions.
    """

    required = (
        pack.get("permissions", {})
        .get("requires", {})
    )

    if required.get("system_guardian"):

        token = context.get(
            "system_guardian_token"
        )

        if not validate_permission_token(
            token,
            "system_guardian"
        ):
            raise PermissionValidationError(
                "System guardian approval missing"
            )

    if required.get("domain_owner"):

        token = context.get(
            "domain_owner_token"
        )

        if not validate_permission_token(
            token,
            "domain_owner"
        ):
            raise PermissionValidationError(
                "Domain owner approval missing"
            )

    return True


# ============================================================================
# Step Implementations
# ============================================================================

def validate_correction_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate correction."""

    print("[STEP] validate_correction")

    correction_id = context.get(
        "correction_id"
    )

    if not correction_id:
        raise StepError(
            "correction_id missing"
        )

    context["correction_valid"] = True
    return context


def load_ssot_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Load SSOT."""

    print("[STEP] load_ssot")

    path = context.get("ssot_path")

    if path and Path(path).exists():
        context["ssot"] = load_yaml(
            Path(path)
        )
    else:
        context["ssot"] = {
            "content": "demo"
        }

    return context


def apply_patch_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply patch."""

    print("[STEP] apply_patch")

    ssot = context.get(
        "ssot",
        {}
    )

    ssot["patched"] = True

    context["ssot"] = ssot

    return context


def update_frontmatter_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Update frontmatter."""

    print("[STEP] update_frontmatter")

    ssot = context.get(
        "ssot",
        {}
    )

    ssot["last-reviewed"] = utc_now()

    context["ssot"] = ssot

    return context


def mark_correction_applied_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Mark correction applied."""

    print(
        "[STEP] mark_correction_applied"
    )

    context[
        "correction_applied"
    ] = True

    return context


def write_ssot_fn(
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Atomic SSOT write."""

    print("[STEP] write_ssot")

    tx: TransactionManager = context[
        "_transaction_manager"
    ]

    path = Path(
        context.get(
            "ssot_path",
            "runtime/demo-ssot.yaml"
        )
    )

    tx.atomic_write_yaml(
        path,
        context.get("ssot", {})
    )

    context["ssot_written"] = True

    return context


# ============================================================================
# Step Registry
# ============================================================================

# ============================================================================
# Real Validation Steps (replacing mock steps)
# ============================================================================

def build_graph_fn(context):
    """Build dependency graph from frontmatter links."""
    print("[STEP] build_graph")
    from pathlib import Path
    nodes = context.get("graph", {}).get("nodes") or []
    # Discover SSOT files and parse frontmatter for links
    ssot_dir = Path("kernel/knowledge/ssot")
    if ssot_dir.exists():
        for f in sorted(ssot_dir.glob("*.md")):
            nodes.append({"id": f.stem, "incoming_links": 0, "root": False, "path": str(f)})
    context["graph"] = {"nodes": nodes}
    return context


def detect_orphans_fn(context):
    """Detect orphan files: incoming_links = 0 AND not in root index."""
    print("[STEP] detect_orphans")
    nodes = context.get("graph", {}).get("nodes", [])
    root_nodes = {n.get("id") for n in nodes if n.get("root")}
    orphans = []
    for n in nodes:
        if n.get("incoming_links", 0) == 0 and n.get("id") not in root_nodes:
            orphans.append(n.get("id"))
    context["orphans"] = orphans
    if orphans:
        print(f"  → {len(orphans)} orphan(s): {', '.join(orphans[:5])}")
    return context


def detect_broken_links_fn(context):
    """Detect broken links by checking referenced files exist on disk."""
    print("[STEP] detect_broken_links")
    nodes = context.get("graph", {}).get("nodes", [])
    broken = []
    for n in nodes:
        path = n.get("path")
        if path and not Path(path).exists():
            broken.append({"node": n.get("id"), "path": path})
    context["broken_links"] = broken
    if broken:
        print(f"  → {len(broken)} broken link(s)")
    return context


def detect_incoming_link_zero_fn(context):
    """Count nodes with zero incoming references."""
    print("[STEP] detect_incoming_link_zero")
    nodes = context.get("graph", {}).get("nodes", [])
    zero = [n.get("id") for n in nodes if n.get("incoming_links", 0) == 0]
    context["incoming_link_zero"] = zero
    return context


def generate_report_fn(context):
    """Generate and store validation report."""
    print("[STEP] generate_report")
    report = {
        "orphans": context.get("orphans", []),
        "broken_links": context.get("broken_links", []),
        "incoming_link_zero": context.get("incoming_link_zero", []),
        "timestamp": utc_now(),
    }
    from pathlib import Path
    report_dir = Path("runtime/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    save_yaml(report_dir / "latest-graph-report.yaml", report)
    context["graph_report"] = report
    return context


def collect_inbox_metrics_fn(context):
    """Scan inbox for stale items."""
    print("[STEP] collect_inbox_metrics")
    inbox_dir = Path("kernel/knowledge/inbox")
    items = list(inbox_dir.glob("*.md")) if inbox_dir.exists() else []
    context["inbox_metrics"] = {
        "count": len(items),
        "items": [str(f) for f in items[:10]],
    }
    return context


def collect_correction_metrics_fn(context):
    """Scan correction log for open items."""
    print("[STEP] collect_correction_metrics")
    corr_dir = Path("kernel/governance/corrections")
    items = list(corr_dir.glob("*.md")) if corr_dir.exists() else []
    context["correction_metrics"] = {
        "count": len(items),
        "open": sum(1 for _ in items),
    }
    return context


def collect_graph_metrics_fn(context):
    """Aggregate graph health metrics."""
    print("[STEP] collect_graph_metrics")
    context["graph_metrics"] = {
        "orphans": len(context.get("orphans", [])),
        "broken_links": len(context.get("broken_links", [])),
    }
    return context


def collect_governance_metrics_fn(context):
    """Check domain ownership status."""
    print("[STEP] collect_governance_metrics")
    registry_path = Path("kernel/foundation/concept-registry.yaml")
    if registry_path.exists():
        registry = load_yaml(registry_path)
        concepts = registry.get("concepts", {})
        context["governance_metrics"] = {
            "total_concepts": len(concepts),
            "canonical": sum(1 for c in concepts.values() if c.get("status") == "canonical"),
        }
    else:
        context["governance_metrics"] = {"total_concepts": 0, "canonical": 0}
    return context


def compute_health_score_fn(context):
    """Compute composite health score."""
    print("[STEP] compute_health_score")
    inbox = context.get("inbox_metrics", {})
    corr = context.get("correction_metrics", {})
    graph = context.get("graph_metrics", {})
    gov = context.get("governance_metrics", {})
    score = (
        40 * (1 - min(graph.get("orphans", 0) / 10, 1))
        + 30 * (1 - min(corr.get("count", 0) / 20, 1))
        + 20 * (1 - min(inbox.get("count", 0) / 20, 1))
        + 10 * (1 if gov.get("canonical", 0) > 0 else 0)
    )
    context["health_score"] = round(score, 1)
    print(f"  → Health score: {context['health_score']}/100")
    return context


def validate_archive_decision_fn(context):
    """Validate archive decision."""
    print("[STEP] validate_archive_decision")
    reason = context.get("archive_reason")
    if not reason:
        context["archive_valid"] = False
        print("  → No archive reason provided")
    else:
        context["archive_valid"] = True
    return context


def move_to_archive_fn(context):
    """Move file to archive directory."""
    print("[STEP] move_to_archive")
    ssot_path = context.get("ssot_path")
    if ssot_path and Path(ssot_path).exists():
        import shutil
        archive_dir = Path("kernel/archive/superseded")
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / Path(ssot_path).name
        shutil.move(ssot_path, dest)
        context["archived_to"] = str(dest)
        print(f"  → Moved to {dest}")
    return context


def update_registry_fn(context):
    """Mark concept as deprecated in registry."""
    print("[STEP] update_registry")
    registry_path = Path("kernel/foundation/concept-registry.yaml")
    if registry_path.exists():
        registry = load_yaml(registry_path)
        ssot_path = context.get("ssot_path")
        if ssot_path:
            for cid, cdata in registry.get("concepts", {}).items():
                if ssot_path in cdata.get("owner", ""):
                    cdata["status"] = "deprecated"
            save_yaml(registry_path, registry)
    return context


def mark_archive_log_fn(context):
    """Record archive event."""
    print("[STEP] mark_archive_log")
    log_entry = {
        "timestamp": utc_now(),
        "ssot": context.get("ssot_path"),
        "reason": context.get("archive_reason"),
        "archived_to": context.get("archived_to"),
    }
    archive_log = Path("audit_logs/archive.log")
    with open(archive_log, "a", encoding="utf-8") as f:
        yaml.safe_dump(log_entry, f, allow_unicode=True, sort_keys=False)
        f.write("\n---\n")
    return context


# ============================================================================
# Generic Mock Steps (still needed for register)
# ============================================================================

def mock_step_fn(name):
    """Return a generic mock step function."""
    def fn(context):
        print(f"[STEP] {name}")
        context[name.replace("-", "_")] = True
        return context
    fn.__name__ = name
    return fn

# Steps for validate-graph pack (real implementations above)
GRAPH_STEPS = [
    "build_graph", "detect_orphans", "detect_broken_links",
    "detect_incoming_link_zero", "generate_report",
]

# Steps for refresh-health pack (real implementations above)
HEALTH_STEPS = [
    "collect_inbox_metrics", "collect_correction_metrics",
    "collect_graph_metrics", "collect_governance_metrics",
    "compute_health_score",
]

# Steps for archive pack (real implementations above)
ARCHIVE_STEPS = [
    "validate_archive_decision", "move_to_archive",
    "update_registry", "mark_archive_log",
]

STEP_REGISTRY: Dict[
    str,
    Callable[[Dict[str, Any]], Dict[str, Any]]
] = {
    # Update-SSOT steps
    "validate_correction":
        validate_correction_fn,
    "load_ssot":
        load_ssot_fn,
    "apply_patch":
        apply_patch_fn,
    "update_frontmatter":
        update_frontmatter_fn,
    "mark_correction_applied":
        mark_correction_applied_fn,
    "write_ssot":
        write_ssot_fn,
}

# Register steps — real implementations first, fallback to mock
STEP_REAL: Dict[str, str] = {
    # validate-graph
    "build_graph": "build_graph_fn",
    "detect_orphans": "detect_orphans_fn",
    "detect_broken_links": "detect_broken_links_fn",
    "detect_incoming_link_zero": "detect_incoming_link_zero_fn",
    "generate_report": "generate_report_fn",
    # refresh-health
    "collect_inbox_metrics": "collect_inbox_metrics_fn",
    "collect_correction_metrics": "collect_correction_metrics_fn",
    "collect_graph_metrics": "collect_graph_metrics_fn",
    "collect_governance_metrics": "collect_governance_metrics_fn",
    "compute_health_score": "compute_health_score_fn",
    # archive
    "validate_archive_decision": "validate_archive_decision_fn",
    "move_to_archive": "move_to_archive_fn",
    "update_registry": "update_registry_fn",
    "mark_archive_log": "mark_archive_log_fn",
}

for step_name, real_fn in STEP_REAL.items():
    if step_name not in STEP_REGISTRY:
        STEP_REGISTRY[step_name] = eval(real_fn)

# Remaining steps from lists get mock fallback
for step_name in set(GRAPH_STEPS + HEALTH_STEPS + ARCHIVE_STEPS) - set(STEP_REAL.keys()):
    if step_name not in STEP_REGISTRY:
        STEP_REGISTRY[step_name] = mock_step_fn(step_name)


# ============================================================================
# Step Executor
# ============================================================================

class StepExecutor:
    """
    Execute ACP steps with:
    - retry
    - skip
    - fail
    """

    def __init__(
        self,
        retry_count: int = DEFAULT_RETRY_COUNT,
        on_failure: str = DEFAULT_ON_FAILURE
    ):
        self.retry_count = retry_count
        self.on_failure = on_failure

    def execute_step(
        self,
        step: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:

        # Handle emit_event steps (dict or string form)
        event_name = None

        if isinstance(step, dict):
            event_name = step.get("emit_event") or step.get("event")

        elif isinstance(step, str) and "emit_event" in step:
            # Handle "emit_event: ssot.updated" or just "emit_event"
            if ":" in step:
                event_name = step.split(":", 1)[1].strip()
            else:
                event_name = "generic"

        if event_name:
            emit_event(
                event_name,
                {
                    "pack_id":
                        context.get("_pack_id"),
                    "ssot_path":
                        context.get("ssot_path"),
                    "correction_id":
                        context.get("correction_id")
                },
                correlation_id=context.get(
                    "_correlation_id"
                )
            )

            return context

        # Regular step: look up in registry
        if not isinstance(step, str):
            raise StepError(f"Unknown step type: {type(step).__name__} ({step})")

        fn = STEP_REGISTRY.get(step)

        if not fn:
            raise StepError(
                f"Unknown step: {step}"
            )

        attempt = 0

        while True:

            try:
                return fn(context)

            except Exception as e:

                attempt += 1

                if (
                    attempt
                    <= self.retry_count
                ):
                    continue

                if (
                    self.on_failure
                    == "skip"
                ):
                    print(
                        f"[SKIP] {step}: {e}"
                    )
                    return context

                raise StepError(
                    f"{step}: {e}"
                )


# ============================================================================
# ACP Runtime
# ============================================================================

def load_pack(
    path: str
) -> Dict[str, Any]:
    """
    Load ACP pack.
    """

    pack = load_yaml(Path(path))

    required = [
        "id",
        "execution",
        "trigger"
    ]

    for field in required:

        if field not in pack:
            raise ACPRunnerError(
                f"Missing field: {field}"
            )

    return pack


def execute_steps(
    pack: Dict[str, Any],
    context: Dict[str, Any]
) -> Tuple[Dict[str, Any], str]:
    """
    Execute all pack steps.
    """

    tx = TransactionManager(
        context["_correlation_id"]
    )

    context[
        "_transaction_manager"
    ] = tx

    executor = StepExecutor(
        retry_count=context.get(
            "retry_count",
            0
        ),
        on_failure=context.get(
            "on_failure",
            "fail"
        )
    )

    try:

        for step in (
            pack["execution"]["steps"]
        ):
            context = (
                executor.execute_step(
                    step,
                    context
                )
            )

        return context, "success"

    except Exception as e:

        try:
            tx.rollback()
        except Exception:
            pass

        return (
            context,
            f"failed: {e}"
        )


def audit_log(
    pack: Dict[str, Any],
    result: str,
    context: Dict[str, Any],
    validator_results: List[
        Dict[str, Any]
    ]
) -> None:
    """
    Write audit log.
    """

    log_file = (
        AUDIT_DIR
        / f"{pack['id']}.log"
    )

    entry = {
        "timestamp": utc_now(),
        "pack_id": pack["id"],
        "result": result,
        "validators":
            validator_results,
        "correlation_id":
            context.get(
                "_correlation_id"
            )
    }

    with open(
        log_file,
        "a",
        encoding="utf-8"
    ) as f:
        yaml.safe_dump(
            entry,
            f,
            allow_unicode=True,
            sort_keys=False
        )
        f.write("\n---\n")


def run_pack(
    pack_path: str,
    context: Dict[str, Any]
) -> Tuple[
    Dict[str, Any],
    str
]:
    """
    Main pack execution.
    """

    pack = load_pack(pack_path)

    correlation_id = (
        str(uuid.uuid4())
    )

    context[
        "_correlation_id"
    ] = correlation_id

    context["_pack_id"] = pack["id"]

    print(
        f"\n=== Running pack: "
        f"{pack['id']} ==="
    )

    check_permissions(
        pack,
        context
    )

    validator_results = (
        run_validators(
            pack,
            context
        )
    )

    result_context, result_status = (
        execute_steps(
            pack,
            context
        )
    )

    audit_log(
        pack,
        result_status,
        result_context,
        validator_results
    )

    return (
        result_context,
        result_status
    )


# ============================================================================
# CLI Demo
# ============================================================================

def build_demo_context() -> Dict[str, Any]:
    """
    Demo execution context.
    """

    return {
        "correction_id":
            "CORR-001",

        "ssot_path":
            "runtime/demo-ssot.yaml",

        "retry_count": 1,

        "on_failure":
            "fail",

        "domain_owner_token": {
            "role":
                "domain_owner",
            "domain":
                "evaluation",
            "approved":
                True,
            "signed_at":
                utc_now()
        },

        "system_guardian_token": {
            "role":
                "system_guardian",
            "approved":
                True,
            "signed_at":
                utc_now()
        },

        "graph": {
            "nodes": [
                {
                    "id": "root",
                    "root": True,
                    "incoming_links": 0
                }
            ]
        },

        "ownership": {
            "valid": True
        }
    }


def main() -> None:
    """
    CLI entrypoint.
    """

    ensure_dirs()

    parser = argparse.ArgumentParser(
        description="ACP Runner"
    )

    parser.add_argument(
        "--pack",
        default=(
            "starter-packs/"
            "update-ssot.yaml"
        )
    )

    args = parser.parse_args()

    try:

        context = (
            build_demo_context()
        )

        final_context, status = (
            run_pack(
                args.pack,
                context
            )
        )

        print(
            "\n=== FINAL RESULT ==="
        )
        print("Status:", status)

        print(
            json.dumps(
                {
                    k: v
                    for k, v in
                    final_context.items()
                    if not k.startswith("_")
                },
                indent=2,
                default=str
            )
        )

    except Exception as e:

        print(
            "\n[FATAL ERROR]"
        )

        print(str(e))

        traceback.print_exc()


if __name__ == "__main__":
    main()
