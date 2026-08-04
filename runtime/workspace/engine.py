"""Engine discovery implementation for OniRoute Workspace Architecture (ACR-003 Phase W2).

Provides deterministic resolution of the OniRoute Engine Root directory.
"""

from __future__ import annotations

from pathlib import Path

from .contracts import EngineResolverContract


class EngineResolver(EngineResolverContract):
    """Deterministic engine root resolver."""

    ENGINE_MARKER_FILES = (".oniroute_engine", "oniroute.engine")
    ENGINE_FOLDER_NAMES = ("OniRoute_SwarmAgents", "oniroute_swarmagents")

    def resolve_engine_root(self, candidate_path: Path | None = None) -> Path:
        """Resolve absolute path to installed OniRoute Engine Root deterministically.

        Priority order:
        1. Explicit candidate_path (if provided, check self, embedded folder, and parents)
        2. Current working directory (check self, embedded folder, and parents)
        3. Built-in package root location
        """
        # 1. Check explicit candidate path
        if candidate_path is not None:
            cand = candidate_path.resolve()
            found = self._find_engine_in_hierarchy(cand)
            if found:
                return found

        # 2. Check CWD and hierarchy
        cwd = Path.cwd().resolve()
        found = self._find_engine_in_hierarchy(cwd)
        if found:
            return found

        # 3. Fallback: package installation location
        package_root = Path(__file__).resolve().parents[2]
        if self._is_engine_root(package_root):
            return package_root

        # Ultimate fallback
        return package_root

    def _find_engine_in_hierarchy(self, start_path: Path) -> Path | None:
        """Search start_path, embedded subfolders, and parent directories for Engine Root."""
        curr = start_path if start_path.is_dir() else start_path.parent
        visited: set[Path] = set()

        while curr not in visited:
            visited.add(curr)

            # Check if current dir is engine root
            if self._is_engine_root(curr):
                return curr

            # Check for embedded engine directory inside current dir
            for sub_name in self.ENGINE_FOLDER_NAMES:
                sub_path = curr / sub_name
                if sub_path.is_dir() and self._is_engine_root(sub_path):
                    return sub_path

            # Move up to parent
            if curr.parent == curr:
                break
            curr = curr.parent

        return None

    def _is_engine_root(self, path: Path) -> bool:
        """Check if path satisfies Engine Root structural or marker criteria without modifying disk."""
        if not path.is_dir():
            return False

        # 1. Explicit marker file check
        for marker in self.ENGINE_MARKER_FILES:
            if (path / marker).is_file():
                return True

        # 2. Structural heuristics check: must contain runtime/ and (agents/ or cli/ or pyproject.toml)
        runtime_dir = path / "runtime"
        agents_dir = path / "agents"
        cli_main = path / "cli" / "main.py"
        pyproject = path / "pyproject.toml"
        agents_doc = path / "AGENTS.md"

        if runtime_dir.is_dir() and (agents_dir.is_dir() or cli_main.is_file() or pyproject.is_file() or agents_doc.is_file()):
            return True

        return False

    def is_engine_read_only(self, engine_root: Path) -> bool:
        """Verify Engine Root boundary and ensure engine is not mutated."""
        return engine_root.exists() and engine_root.is_dir()
