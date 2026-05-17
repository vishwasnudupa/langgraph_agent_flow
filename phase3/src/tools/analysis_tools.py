"""
Analysis Tools — code structure analysis for C kernel/firmware code.

Phase 1: uses basic regex-based parsing (no tree-sitter dependency).
Phase 2+: swap in tree-sitter for proper AST parsing.
"""
from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import tool


@tool
def parse_c_ast(repo_path: str, filepath: str) -> dict:
    """
    Extract C symbols (functions, structs, macros) using Tree-sitter AST.
    (Phase 3 Stub: Will use native tree-sitter-c bindings)

    Args:
        repo_path: Root directory of the source tree.
        filepath: Relative path to the C file.

    Returns:
        Dict with keys: functions, structs, macros, includes.
    """
    fpath = Path(repo_path) / filepath
    if not fpath.is_file():
        return {"error": f"{filepath} not found"}

    content = fpath.read_text(errors="ignore")

    # [PHASE 3 STUB] - Native AST parsing replaces Regex
    # tree_sitter.Language(tree_sitter_c.language())
    # parser.parse(content.encode()) ...
    
    return {
        "file": filepath,
        "functions": ["[MOCK AST] void example_func()", "[MOCK AST] int main()"],
        "structs": ["[MOCK AST] struct example"],
        "macros": ["[MOCK AST] #define EXAMPLE 1"],
        "includes": ["[MOCK AST] <linux/module.h>"],
    }


@tool
def find_callers(repo_path: str, function_name: str, file_glob: str = "*.c") -> str:
    """
    Find all call sites of a function in the codebase.

    Args:
        repo_path: Root directory of the source tree.
        function_name: Name of the function to search for.
        file_glob: File glob filter.

    Returns:
        Matching call sites with file and line numbers.
    """
    repo = Path(repo_path)
    pattern = re.compile(rf'\b{re.escape(function_name)}\s*\(')
    matches = []

    for fpath in repo.rglob(file_glob):
        try:
            for i, line in enumerate(fpath.read_text(errors="ignore").splitlines(), 1):
                if pattern.search(line):
                    rel = fpath.relative_to(repo)
                    matches.append(f"{rel}:{i}: {line.strip()}")
                    if len(matches) >= 25:
                        return "\n".join(matches) + "\n... (truncated)"
        except Exception:
            continue

    return "\n".join(matches) if matches else f"No callers found for {function_name}"


@tool
def find_definitions(repo_path: str, symbol: str, file_glob: str = "*.c") -> str:
    """
    Find where a symbol (function, struct, macro) is defined.

    Args:
        repo_path: Root directory.
        symbol: Symbol name to find.
        file_glob: File filter (also searches .h files).

    Returns:
        Definition locations.
    """
    repo = Path(repo_path)
    patterns = [
        re.compile(rf'^\s*[\w\s\*]+\s+{re.escape(symbol)}\s*\(', re.MULTILINE),   # function
        re.compile(rf'struct\s+{re.escape(symbol)}\s*\{{'),                          # struct
        re.compile(rf'#define\s+{re.escape(symbol)}\b'),                             # macro
        re.compile(rf'typedef\s+.*\b{re.escape(symbol)}\s*;'),                       # typedef
    ]
    matches = []
    globs = [file_glob, "*.h"] if file_glob == "*.c" else [file_glob]

    for glob in globs:
        for fpath in repo.rglob(glob):
            try:
                content = fpath.read_text(errors="ignore")
                for pat in patterns:
                    for m in pat.finditer(content):
                        lineno = content[:m.start()].count("\n") + 1
                        rel = fpath.relative_to(repo)
                        line_text = content.splitlines()[lineno - 1].strip()
                        matches.append(f"{rel}:{lineno}: {line_text}")
            except Exception:
                continue

    seen = set()
    deduped = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    return "\n".join(deduped[:20]) if deduped else f"No definition found for '{symbol}'"


@tool
def analyze_kconfig(repo_path: str, config_symbol: str) -> str:
    """
    Analyze Kconfig dependency chain for a CONFIG_ symbol.

    Args:
        repo_path: Root of kernel source.
        config_symbol: e.g. "I2C_BCM2835" (without CONFIG_ prefix).

    Returns:
        Kconfig entry with dependencies, help text, etc.
    """
    repo = Path(repo_path)
    target = config_symbol.replace("CONFIG_", "")
    results = []

    for kconfig in repo.rglob("Kconfig*"):
        try:
            content = kconfig.read_text(errors="ignore")
            # Find "config SYMBOL" blocks
            pattern = re.compile(
                rf'^config\s+{re.escape(target)}\b(.*?)(?=^config\s|\Z)',
                re.MULTILINE | re.DOTALL
            )
            for m in pattern.finditer(content):
                rel = kconfig.relative_to(repo)
                results.append(f"── {rel} ──\nconfig {target}{m.group(1).rstrip()}")
        except Exception:
            continue

    return "\n\n".join(results) if results else f"No Kconfig entry found for {target}"


@tool
def analyze_makefile(repo_path: str, dir_path: str) -> str:
    """
    Parse Makefile or Kbuild in a directory to show obj-y/obj-m entries.

    Args:
        repo_path: Root of kernel source.
        dir_path: Relative directory containing the Makefile.

    Returns:
        Parsed obj-y and obj-m entries.
    """
    target_dir = Path(repo_path) / dir_path
    results = []

    for name in ["Makefile", "Kbuild"]:
        mf = target_dir / name
        if mf.is_file():
            content = mf.read_text(errors="ignore")
            obj_y = re.findall(r'obj-\$\(CONFIG_\w+\)\s*\+=\s*(.+)', content)
            obj_y += re.findall(r'obj-y\s*\+=\s*(.+)', content)
            obj_m = re.findall(r'obj-m\s*\+=\s*(.+)', content)

            results.append(f"── {dir_path}/{name} ──")
            if obj_y:
                results.append("Built-in objects (obj-y):")
                results.extend(f"  {o.strip()}" for o in obj_y)
            if obj_m:
                results.append("Module objects (obj-m):")
                results.extend(f"  {o.strip()}" for o in obj_m)
            if not obj_y and not obj_m:
                results.append("(no obj-y/obj-m entries found)")

    return "\n".join(results) if results else f"No Makefile/Kbuild in {dir_path}"
