#!/usr/bin/env python3
"""
Contract Enforcement Tests — A1: Layer Isolation

Verifies that each layer only imports what it's allowed to import.
Prevents M3 from accidentally depending on M4 internals, etc.
"""

import sys
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = PROJECT_ROOT / "kernel" / "runtime"

# ============================================================================
# IMPORT ALLOWLIST (which modules each layer MAY import)
# ============================================================================

ALLOWLIST = {
    "validator.py": {
        "allowed": {"yaml", "hashlib", "json", "pathlib", "datetime", "os", "sys", "argparse", "time"},
        "forbidden_modules": {"tracer", "projection", "diagnostics", "auditor", "arbiter"},
    },
    "tracer.py": {
        "allowed": {"yaml", "hashlib", "json", "pathlib", "datetime", "os", "sys", "argparse", "typing"},
        "forbidden_imports": {"projection", "diagnostics", "auditor", "arbiter"},
        # tracer MAY import validator (it wraps it)
        "allowed_runtime_imports": {"validator"},
    },
    "projection.py": {
        "allowed": {"yaml", "hashlib", "json", "pathlib", "datetime", "os", "sys", "argparse", "typing"},
        "forbidden_imports": {"diagnostics", "auditor", "arbiter"},
        # projection reads traces and events directly (file-level, not import)
    },
    "diagnostics.py": {
        "allowed": {"yaml", "json", "pathlib", "datetime", "sys", "argparse", "collections", "typing"},
        "forbidden_imports": {"auditor", "arbiter"},
        # diagnostics is the LAST data-plane layer — it imports nothing beyond stdlib
    },
    "auditor.py": {
        "allowed": {"yaml", "json", "hashlib", "pathlib", "datetime", "sys", "argparse", "collections", "typing"},
        "forbidden_imports": {"arbiter"},
        # auditor reads diagnostics + projection via file-level, not import
    },
}


def get_imports(file_path):
    """Extract all imported module names from a Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def test_layer_isolation():
    """Verify each layer's imports comply with its allowlist."""
    failures = []

    for filename, rules in ALLOWLIST.items():
        filepath = RUNTIME / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} does not exist yet")
            continue

        imports = get_imports(filepath)
        allowed = rules["allowed"]

        # Check for forbidden module-level imports
        forbidden = rules.get("forbidden_imports", set())
        allowed_runtime = rules.get("allowed_runtime_imports", set())

        for imp in imports:
            # stdlib modules are always allowed
            if imp in allowed:
                continue
            # Check if it's a forbidden import
            if imp in forbidden:
                failures.append(f"{filename}: imports '{imp}' which is FORBIDDEN")
            # If not in allowed and not a local kernel.runtime import, flag it
            elif imp not in allowed_runtime and imp not in ("kernel",):
                # It might be a local relative import — check
                if imp in {"validator", "tracer", "projection", "diagnostics", "auditor", "arbiter"}:
                    if imp not in allowed_runtime:
                        failures.append(f"{filename}: imports '{imp}' without explicit allowlist entry")

        if not failures:
            print(f"  ✅ {filename}: imports clean")

    if failures:
        print(f"\n  LAYER ISOLATION VIOLATIONS:")
        for f in failures:
            print(f"    ❌ {f}")
        sys.exit(1)
    else:
        print(f"  ✅ All layers isolated correctly")


if __name__ == "__main__":
    test_layer_isolation()
