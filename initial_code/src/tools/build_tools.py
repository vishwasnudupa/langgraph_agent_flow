"""
Build Tools — patch application and build simulation.

Phase 1: Mock build that validates the patch is well-formed.
Phase 2+: Real cross-compilation with make / gcc.
"""
from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import tool


@tool
def apply_patch(repo_path: str, patch_diff: str) -> str:
    """
    Apply a unified diff patch to the source tree (dry-run in Phase 1).

    Args:
        repo_path: Root directory of the source tree.
        patch_diff: Unified diff string.

    Returns:
        Result message indicating success or parse errors.
    """
    if not patch_diff or not patch_diff.strip():
        return "Error: empty patch"

    file_pattern = re.compile(r'^(?:---|\+\+\+)\s+[ab]/(.+)$', re.MULTILINE)
    hunk_pattern = re.compile(r'^@@\s+.*\s+@@', re.MULTILINE)

    files = file_pattern.findall(patch_diff)
    hunks = hunk_pattern.findall(patch_diff)

    if not files:
        return "Error: no file targets found in patch."
    if not hunks:
        return "Error: no @@ hunk headers found."

    repo = Path(repo_path)
    missing = []
    target_files = list(set(files))
    for f in target_files:
        if f != "/dev/null" and not (repo / f).exists():
            missing.append(f)

    lines_added = patch_diff.count("\n+") - patch_diff.count("\n+++")
    lines_removed = patch_diff.count("\n-") - patch_diff.count("\n---")

    result_lines = [
        "Patch analysis:",
        f"  Files: {', '.join(target_files)}",
        f"  Hunks: {len(hunks)}",
        f"  +{max(0, lines_added)} / -{max(0, lines_removed)} lines",
    ]
    if missing:
        result_lines.append(f"  Warning: missing files (new?): {', '.join(missing)}")
    result_lines.append("  Status: APPLIED (dry-run)")
    return "\n".join(result_lines)


@tool
def build_kernel(repo_path: str, arch: str = "arm64", target: str = "vmlinux") -> str:
    """Build the kernel (mock in Phase 1). Returns build log."""
    repo = Path(repo_path)
    has_makefile = (repo / "Makefile").exists()

    return "\n".join([
        f"=== Build: {target} (arch={arch}) ===",
        f"  Source: {repo_path}",
        f"  Makefile: {has_makefile}",
        "  [MOCK] Compilation simulated",
        "  [MOCK] 0 errors, 0 warnings",
        "=== Build Status: PASS ===",
    ])


@tool
def build_module(repo_path: str, module_path: str) -> str:
    """Build a single kernel module (mock in Phase 1)."""
    mod_dir = Path(repo_path) / module_path
    c_files = list(mod_dir.rglob("*.c")) if mod_dir.is_dir() else []
    return "\n".join([
        f"=== Module Build: {module_path} ===",
        f"  C sources: {len(c_files)}",
        "  [MOCK] Module compilation simulated",
        "=== Module Build Status: PASS ===",
    ])


@tool
def check_build_errors(build_log: str) -> str:
    """Parse a build log for errors and warnings."""
    errors = re.findall(r'(?:error|fatal):\s*(.+)', build_log, re.IGNORECASE)
    warnings = re.findall(r'warning:\s*(.+)', build_log, re.IGNORECASE)

    lines = [f"Build Log Analysis:", f"  Errors: {len(errors)}", f"  Warnings: {len(warnings)}"]
    for e in errors[:10]:
        lines.append(f"    x {e.strip()}")
    if not errors:
        lines.append("  Verdict: BUILD CLEAN")
    else:
        lines.append("  Verdict: BUILD FAILED")
    return "\n".join(lines)
