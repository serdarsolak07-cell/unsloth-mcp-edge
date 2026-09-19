"""Pure, bounded filesystem and command helpers used by the worker."""
from __future__ import annotations

import shlex
import subprocess
import selectors
import time
from pathlib import Path
from typing import Sequence

from .paths import inside_allowed, is_protected


class SafetyError(ValueError):
    """An operation violates the worker policy."""


def checked_path(raw: str, roots: list[Path], protected: list[Path]) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise SafetyError("path must be a non-empty string")
    path = Path(raw).expanduser()
    if not inside_allowed(path, roots) or is_protected(path, protected):
        raise SafetyError("path is outside allowed roots or protected")
    return path.resolve()


def checked_command(command: str, allowlist: set[str]) -> list[str]:
    if not isinstance(command, str) or len(command) > 4096:
        raise SafetyError("command must be a short string")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise SafetyError(f"invalid command syntax: {exc}") from exc
    if not argv or argv[0] not in allowlist:
        raise SafetyError(f"command is not allowlisted: {argv[0] if argv else ''}")
    if argv[0] in {"ash", "bash", "cmd", "fish", "pwsh", "sh", "zsh"}:
        raise SafetyError("shell interpreters are not permitted")
    if any(token in {"sudo", "dd", "mkfs", "shutdown", "reboot", ">|"} for token in argv):
        raise SafetyError("dangerous command token")
    if any(ch in command for ch in (";", "|", "&", "`", "$(", "\n", "\r")):
        raise SafetyError("shell operators are not permitted")
    return argv


def run_checked(
    command: str,
    allowlist: set[str],
    timeout: float = 120,
    roots: list[Path] | None = None,
    protected: list[Path] | None = None,
    cwd: Path | None = None,
    max_output_bytes: int = 65536,
) -> str:
    argv = checked_command(command, allowlist)
    if roots is not None and protected is not None:
        path_commands = {
            "cat", "chmod", "cp", "du", "find", "grep", "head", "ln", "ls",
            "md5sum", "mv", "realpath", "rm", "rmdir", "stat", "tail", "touch",
            "tree", "wc",
        }
        if argv[0] in path_commands:
            for argument in argv[1:]:
                if not argument.startswith("-"):
                    checked_path(argument, roots, protected)
    if timeout <= 0 or max_output_bytes <= 0:
        raise SafetyError("timeout and output limit must be positive")
    workdir = cwd or (roots[0] if roots else Path.home())
    if roots is not None and protected is not None:
        workdir = checked_path(str(workdir), roots, protected)
    if not workdir.is_dir():
        raise SafetyError("command working directory is not a directory")
    try:
        process = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=False, shell=False, cwd=str(workdir),
        )
    except OSError as exc:
        raise SafetyError(f"command could not be started: {exc}") from exc
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    chunks: list[bytes] = []
    total = 0
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.wait()
                raise SafetyError("command timed out")
            for key, _ in selector.select(remaining):
                data = key.fileobj.read(8192)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if total < max_output_bytes:
                    keep = data[: max_output_bytes - total]
                    chunks.append(keep)
                    total += len(keep)
        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except (OSError, subprocess.TimeoutExpired) as exc:
        process.kill()
        process.wait()
        raise SafetyError("command failed while collecting output") from exc
    output = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if total >= max_output_bytes:
        output += "\n[output truncated]"
    return f"exit={returncode}\n{output}"
