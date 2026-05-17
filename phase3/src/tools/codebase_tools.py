"""
Codebase Tools — file operations for exploring kernel / firmware source trees.

These are REAL tools that work on the local filesystem.
No kernel download required — they work on any directory.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def semantic_search(repo_path: str, query: str) -> str:
    """
    Perform a semantic search across the codebase using vector embeddings.
    (Phase 3 Stub: Will use sentence-transformers and FAISS)

    Args:
        repo_path: Root directory of the source tree.
        query: Natural language query (e.g., 'how is i2c timeout handled')

    Returns:
        The most semantically relevant code snippets.
    """
    return (
        f"[SEMANTIC SEARCH MOCK] Results for '{query}'\n"
        f"── drivers/i2c/i2c-core.c:140 ──\n"
        f"// Semantic match (score 0.89)\n"
        f"int i2c_transfer_timeout(struct i2c_adapter *adap, struct i2c_msg *msgs, int num)\n"
        f"{{\n"
        f"    // ... implementation\n"
        f"}}\n"
    )


@tool
def search_code(repo_path: str, query: str, file_glob: str = "*.c") -> str:
    """
    Search for a pattern in the codebase using grep.

    Args:
        repo_path: Root directory of the source tree.
        query: Text or regex pattern to search for.
        file_glob: File glob to filter (default: *.c).

    Returns:
        Matching lines (max 30) in 'file:line: content' format.
    """
    repo = Path(repo_path)
    if not repo.is_dir():
        return f"Error: {repo_path} is not a valid directory"

    try:
        result = subprocess.run(
            ["grep", "-rnI", "--include", file_glob, query, str(repo)],
            capture_output=True, text=True, timeout=15,
            cwd=str(repo),
        )
        lines = result.stdout.strip().split("\n")[:30]
        return "\n".join(lines) if lines[0] else f"No matches for '{query}'"
    except FileNotFoundError:
        # grep not available — fall back to Python
        matches = []
        for root, _, files in os.walk(repo):
            for fname in files:
                if not _glob_match(fname, file_glob):
                    continue
                fpath = Path(root) / fname
                try:
                    for i, line in enumerate(fpath.read_text(errors="ignore").splitlines(), 1):
                        if query in line:
                            rel = fpath.relative_to(repo)
                            matches.append(f"{rel}:{i}: {line.rstrip()}")
                            if len(matches) >= 30:
                                return "\n".join(matches)
                except Exception:
                    continue
        return "\n".join(matches) if matches else f"No matches for '{query}'"
    except subprocess.TimeoutExpired:
        return "Error: search timed out after 15s"


@tool
def read_file(repo_path: str, filepath: str, start_line: int = 1, end_line: int = 100) -> str:
    """
    Read a file from the source tree.

    Args:
        repo_path: Root directory of the source tree.
        filepath: Relative path within the repo.
        start_line: First line to return (1-indexed, inclusive).
        end_line: Last line to return (1-indexed, inclusive).

    Returns:
        File contents with line numbers.
    """
    fpath = Path(repo_path) / filepath
    if not fpath.is_file():
        return f"Error: {filepath} not found in {repo_path}"

    try:
        lines = fpath.read_text(errors="ignore").splitlines()
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        numbered = [f"{i + 1:4d} | {lines[i]}" for i in range(start, end)]
        header = f"── {filepath} (lines {start_line}-{end_line} of {len(lines)}) ──"
        return header + "\n" + "\n".join(numbered)
    except Exception as e:
        return f"Error reading {filepath}: {e}"


@tool
def list_directory(repo_path: str, path: str = ".") -> str:
    """
    List directory contents in the source tree.

    Args:
        repo_path: Root directory of the source tree.
        path: Relative path within the repo (default: root).

    Returns:
        Listing with [DIR] / [FILE] markers and sizes.
    """
    target = Path(repo_path) / path
    if not target.is_dir():
        return f"Error: {path} is not a directory in {repo_path}"

    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    lines = []
    for entry in entries[:80]:  # cap at 80 entries
        rel = entry.relative_to(Path(repo_path))
        if entry.is_dir():
            count = sum(1 for _ in entry.iterdir()) if entry.is_dir() else 0
            lines.append(f"  [DIR]  {rel}/  ({count} items)")
        else:
            size = entry.stat().st_size
            lines.append(f"  [FILE] {rel}  ({size:,} bytes)")
    header = f"── {path}/ ({len(entries)} entries) ──"
    return header + "\n" + "\n".join(lines)


@tool
def git_log(repo_path: str, path: str = ".", n: int = 10) -> str:
    """
    Show recent git commits touching a path.

    Args:
        repo_path: Root directory of the git repo.
        path: Relative path to filter commits.
        n: Number of commits to show.

    Returns:
        Formatted commit log.
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-n{n}", "--oneline", "--", path],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
        )
        return result.stdout.strip() or "No commits found."
    except Exception as e:
        return f"Error running git log: {e}"


@tool
def git_blame(repo_path: str, filepath: str, start_line: int = 1, end_line: int = 20) -> str:
    """
    Show git blame for specific lines of a file.

    Args:
        repo_path: Root directory of the git repo.
        filepath: Relative path to the file.
        start_line: First line (1-indexed).
        end_line: Last line (1-indexed).

    Returns:
        Blame output with commit hashes and authors.
    """
    try:
        result = subprocess.run(
            ["git", "blame", f"-L{start_line},{end_line}", filepath],
            capture_output=True, text=True, timeout=10,
            cwd=repo_path,
        )
        return result.stdout.strip() or "No blame data."
    except Exception as e:
        return f"Error running git blame: {e}"


def _glob_match(filename: str, pattern: str) -> bool:
    """Simple glob matching for file extensions."""
    if pattern == "*":
        return True
    if pattern.startswith("*."):
        return filename.endswith(pattern[1:])
    return filename == pattern
