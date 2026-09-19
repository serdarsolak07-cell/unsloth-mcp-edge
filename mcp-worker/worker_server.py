#!/usr/bin/env python3
"""FastMCP worker with an authenticated health endpoint."""
from __future__ import annotations

import argparse
import hmac
import json
import os
from pathlib import Path

from tools.operations import WorkerOperations


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    return config


def create_app(config: dict):
    try:
        from fastapi import FastAPI, Header, HTTPException
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("install mcp-worker/requirements.txt first") from exc

    token = os.environ.get("MCP_BEARER_TOKEN", "").strip()
    if not token:
        token_file = Path(
            os.environ.get("MCP_TOKEN_FILE", "~/.config/mcp-bearer.token")
        ).expanduser()
        token = token_file.read_text(encoding="utf-8").strip() if token_file.exists() else ""
    if not token:
        raise RuntimeError("MCP_BEARER_TOKEN or MCP_TOKEN_FILE is required")

    ops = WorkerOperations(config)
    mcp = FastMCP("unsloth-worker")

    @mcp.tool()
    def list_files(path: str = "~") -> list[str]:
        return ops.list_path(path)

    @mcp.tool()
    def read_file(path: str) -> str:
        return ops.read_file(path)

    @mcp.tool()
    def write_file(path: str, content: str) -> str:
        return ops.write_file(path, content)

    @mcp.tool()
    def remove(path: str) -> str:
        return ops.remove(path)

    @mcp.tool()
    def copy_file(source: str, destination: str) -> str:
        return ops.copy(source, destination)

    @mcp.tool()
    def move_file(source: str, destination: str) -> str:
        return ops.move(source, destination)

    @mcp.tool()
    def run_command(command: str) -> str:
        return ops.command(command)

    @mcp.tool()
    def sha256(path: str) -> str:
        return ops.checksum(path)

    app = FastAPI(title="Unsloth MCP worker")

    def authorized(value: str | None):
        expected = "Bear" + "er " + token
        if value is None or not hmac.compare_digest(value.strip(), expected):
            raise HTTPException(status_code=401, detail="invalid authorization")

    @app.middleware("http")
    async def protect_mcp(request, call_next):
        if request.url.path == "/mcp" or request.url.path.startswith("/mcp/"):
            authorized(request.headers.get("authorization"))
        return await call_next(request)

    @app.get("/health")
    def health(authorization: str | None = Header(default=None)):
        authorized(authorization)
        return {"status": "ok", "service": "unsloth-mcp-worker"}

    app.mount("/mcp", mcp.http_app(transport="streamable-http"))
    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    config = load_config(args.config)
    app = create_app(config)
    import uvicorn

    uvicorn.run(
        app,
        host=args.host or config.get("host", "127.0.0.1"),
        port=args.port or int(config.get("port", 8788)),
    )


if __name__ == "__main__":
    main()
