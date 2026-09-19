#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def expand_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()


def allowed_roots(allowed: list[str]) -> list[Path]:
    roots = []
    for item in allowed:
        p = expand_path(item)
        p.mkdir(parents=True, exist_ok=True)
        roots.append(p)
    return roots


def inside_allowed(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def is_protected(path: Path, protected: list[Path]) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return True
    for p in protected:
        try:
            if resolved == p:
                return True
            resolved.relative_to(p)
            return True
        except ValueError:
            continue
    return False


def load_protected(raw: list[str]) -> list[Path]:
    out = []
    for item in raw:
        try:
            out.append(expand_path(item))
        except OSError:
            continue
    return out
