"""Bounded worker operations, independent of FastMCP."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .paths import allowed_roots, load_protected
from .safety import SafetyError, checked_path, run_checked

DEFAULT_COMMANDS = {
    "basename", "cargo", "cat", "chmod", "cp", "date", "dirname",
    "df", "du", "find", "file", "free", "git", "grep", "head", "hostname",
    "id", "ln", "ls", "make", "md5sum", "mkdir", "mv", "node", "npm", "npx",
    "python", "python3", "pytest", "pwd", "realpath", "rm", "rmdir", "rustc",
    "sha256sum", "stat", "tail", "touch", "tree", "uname", "uptime", "wc",
    "which", "whoami",
}


class WorkerOperations:
    def __init__(self, config: dict):
        self.roots = allowed_roots(config.get("allowed_paths", ["~"]))
        self.protected = load_protected(config.get("protected_paths", []))
        self.commands = set(config.get("allowlist_commands", DEFAULT_COMMANDS))
        self.max_read = int(config.get("max_read_bytes", 262144))
        self.max_write = int(config.get("max_write_bytes", 5242880))
        self.command_timeout = float(config.get("command_timeout_sec", 120))
        self.max_command_output = int(config.get("max_command_output_bytes", 65536))
        configured_cwd = config.get("command_working_directory")
        self.command_cwd = (
            checked_path(configured_cwd, self.roots, self.protected)
            if configured_cwd else self.roots[0]
        )

    def list_path(self, path: str = "~") -> list[str]:
        target = checked_path(path, self.roots, self.protected)
        if not target.is_dir():
            raise SafetyError("path is not a directory")
        return sorted(p.name for p in target.iterdir())

    def read_file(self, path: str, max_bytes: int | None = None) -> str:
        target = checked_path(path, self.roots, self.protected)
        if not target.is_file():
            raise SafetyError("path is not a file")
        limit = min(self.max_read, max_bytes or self.max_read)
        if target.stat().st_size > limit:
            raise SafetyError(f"file exceeds limit ({limit} bytes)")
        return target.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> str:
        if not isinstance(content, str) or len(content.encode()) > self.max_write:
            raise SafetyError("content exceeds write limit")
        target = checked_path(path, self.roots, self.protected)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)

    def remove(self, path: str) -> str:
        target = checked_path(path, self.roots, self.protected)
        if any(target == root for root in self.roots):
            raise SafetyError("cannot remove an allowed root")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return str(target)

    def copy(self, source: str, destination: str) -> str:
        src = checked_path(source, self.roots, self.protected)
        dst = checked_path(destination, self.roots, self.protected)
        if src == dst or (src.is_dir() and dst.is_relative_to(src)):
            raise SafetyError("destination cannot be the source or inside it")
        if src.is_dir():
            if dst.exists() and dst.is_dir():
                dst = dst / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            if dst.exists() and dst.is_dir():
                dst = dst / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            raise SafetyError("source is not a regular file or directory")
        return str(dst)

    def move(self, source: str, destination: str) -> str:
        src = checked_path(source, self.roots, self.protected)
        dst = checked_path(destination, self.roots, self.protected)
        if src == dst or (src.is_dir() and dst.is_relative_to(src)):
            raise SafetyError("destination cannot be the source or inside it")
        if dst.exists() and dst.is_dir():
            dst = dst / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        return str(shutil.move(str(src), str(dst)))

    def command(self, command: str) -> str:
        return run_checked(
            command, self.commands, timeout=self.command_timeout,
            roots=self.roots, protected=self.protected, cwd=self.command_cwd,
            max_output_bytes=self.max_command_output,
        )

    def checksum(self, path: str) -> str:
        target = checked_path(path, self.roots, self.protected)
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
