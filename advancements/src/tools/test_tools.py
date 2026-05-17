"""
Test Tools — static analysis and testing (mock for Phase 1).
"""
from __future__ import annotations

import re
from langchain_core.tools import tool


@tool
def run_checkpatch(patch_diff: str) -> str:
    """Run checkpatch.pl style checks on a patch (mock). Returns warnings/errors."""
    issues = []
    for i, line in enumerate(patch_diff.splitlines(), 1):
        if len(line) > 100:
            issues.append(f"  WARNING:{i}: line over 100 characters")
        if "\t" in line and line.startswith("+"):
            pass  # tabs are fine in kernel
        if line.startswith("+") and "  " in line and not line.startswith("+++"):
            pass  # double spaces might be alignment

    if not issues:
        return "checkpatch: 0 errors, 0 warnings\nStatus: PASS"
    return "checkpatch:\n" + "\n".join(issues[:15]) + f"\nTotal: {len(issues)} warnings\nStatus: PASS (warnings only)"


@tool
def run_sparse(repo_path: str, filepath: str) -> str:
    """Run sparse static analysis on a C file (mock). Returns analysis results."""
    return f"[MOCK] sparse: {filepath} — 0 errors, 0 warnings\nStatus: PASS"


@tool
def run_coccinelle(repo_path: str, filepath: str) -> str:
    """Run Coccinelle semantic analysis (mock). Returns results."""
    return f"[MOCK] coccinelle: {filepath} — no semantic issues found\nStatus: PASS"


@tool
def run_boot_test(kernel_image: str = "", arch: str = "arm64") -> str:
    """Run QEMU boot test (mock). Returns boot log summary."""
    return "\n".join([
        f"[MOCK] QEMU boot test — arch={arch}",
        "  Booting kernel...",
        "  [    0.000000] Booting Linux on physical CPU 0x0",
        "  [    1.234567] VFS: Mounted root (ext4 filesystem) readonly",
        "  [    2.345678] systemd[1]: Started",
        "  Boot completed successfully.",
        "Status: PASS",
    ])
