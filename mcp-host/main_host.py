#!/usr/bin/env python3
"""CLI bridge between an OpenAI-compatible Unsloth endpoint and the worker."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("config must be an object")
    return value


def tool_schema(tool: Any) -> dict:
    name = getattr(tool, "name", None) or tool.get("name")
    description = getattr(tool, "description", None) or tool.get("description", "")
    schema = getattr(tool, "inputSchema", None) or tool.get("inputSchema", {})
    return {"type": "function", "function": {
        "name": name, "description": description or "", "parameters": schema or {"type": "object"}
    }}


def configured_tool_round_limit(config: dict) -> int | None:
    """Return an optional orchestration limit; None deliberately means unlimited."""
    value = config.get("max_tool_rounds")
    if value is None:
        return None
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_tool_rounds must be null or a positive integer") from exc
    if limit <= 0:
        raise ValueError("max_tool_rounds must be null or a positive integer")
    return limit


async def _run(config: dict, prompt: str) -> str:
    try:
        from openai import OpenAI
        from fastmcp import Client
    except ImportError as exc:
        raise RuntimeError("install mcp-host/requirements.txt first") from exc
    api_key = os.environ.get(config.get("unsloth_api_key_env", "UNSLOTH_STUDIO_AUTH_TOKEN"), "")
    if not api_key:
        raise RuntimeError("Unsloth API key environment variable is not set")
    bearer = os.environ.get(config.get("bearer_token_env", "MCP_BEARER_TOKEN"), "")
    if not bearer:
        token_file = Path("~/.config/mcp-bearer.token").expanduser()
        if token_file.exists():
            bearer = token_file.read_text(encoding="utf-8").strip()
    if not bearer:
        raise RuntimeError("MCP bearer token is not set")

    client = Client(config["worker_url"], auth=bearer)
    async with client:
        tools = await client.list_tools()
        messages: list[dict] = [{"role": "user", "content": prompt}]
        model = config.get("unsloth_model") or "default"
        round_limit = configured_tool_round_limit(config)
        llm = OpenAI(base_url=config["unsloth_base_url"], api_key=api_key,
                     timeout=float(config.get("request_timeout_sec", 120)))
        rounds = 0
        while round_limit is None or rounds < round_limit:
            rounds += 1
            response = llm.chat.completions.create(
                model=model, messages=messages, tools=[tool_schema(t) for t in tools]
            )
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            if not message.tool_calls:
                return message.content or ""
            for call in message.tool_calls:
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    result = await client.call_tool(call.function.name, arguments)
                    content = getattr(result, "content", result)
                    serialized = json.dumps(content, ensure_ascii=False, default=str)
                except Exception as exc:
                    serialized = json.dumps({"error": str(exc)})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": serialized})
        raise RuntimeError("maximum tool rounds exceeded by configuration")


def run(config: dict, prompt: str) -> str:
    return asyncio.run(_run(config, prompt))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--once", metavar="PROMPT")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.once:
        print(run(config, args.once))
        return
    print("Unsloth MCP host; /q exits")
    for line in sys.stdin:
        prompt = line.strip()
        if prompt == "/q":
            break
        if prompt:
            try:
                print(run(config, prompt))
            except Exception as exc:
                print(f"error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
