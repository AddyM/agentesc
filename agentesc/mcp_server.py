"""Serve one single-agent scenario's tools over MCP stdio (HARNESS_SPEC §9).

Any MCP client (Claude Desktop, an IDE agent, a custom client) can connect and act as the
agent. Every call goes through the same gateway as the harness; the trace is appended to a
JSONL file. No oracle or metrics are computed here.
"""

from __future__ import annotations

import json
from pathlib import Path

from .env import Context
from .loader import load
from .runner import Trial, _API


def build(path: Path, level: str, trace_path: Path):
    try:
        import mcp.types as types
        from mcp.server.lowlevel import Server
    except ImportError as e:  # pragma: no cover
        raise SystemExit("mcp-serve needs the MCP SDK: pip install 'agentesc[mcp]'") from e

    sc = load(path)
    if len(sc.agents) != 1:
        raise SystemExit("mcp-serve supports single-agent scenarios only")
    session = sc.sessions[0]
    trial = Trial(sc, None, level)
    ctx = Context(1, session.principal, [sc.agents[0].id])
    api = _API(trial, ctx)

    async def list_tools(_ctx, _params):
        specs = [t for t in trial.env.tools_for(ctx) if t["name"] != "send_message"]
        return types.ListToolsResult(tools=[
            types.Tool(name=t["name"], description=t["description"], input_schema=t["parameters"])
            for t in specs
        ])

    async def call_tool(_ctx, params):
        before = len(trial.env.records)
        out = api.call(params.name, params.arguments if params.arguments is not None else {})
        with open(trace_path, "a") as f:
            for rec in trial.env.records[before:]:
                f.write(json.dumps({"scenario": sc.id, "defense": level, **rec.to_dict()}) + "\n")
        denied = any(r.decision == "denied" for r in trial.env.records[before:])
        return types.CallToolResult(content=[types.TextContent(type="text", text=out)], is_error=denied)

    instructions = (f"AgentEsc scenario {sc.id} at defense {level}. Acting for principal "
                    f"'{session.principal}'. Suggested task: {session.user_task}")
    server = Server(f"agentesc-{sc.id}", version="0.2.0", instructions=instructions,
                    on_list_tools=list_tools, on_call_tool=call_tool)
    return server, trial


def serve(path: Path, level: str, *, trace_path: Path) -> int:
    import anyio
    from mcp.server.stdio import stdio_server

    server, _ = build(path, level, trace_path)

    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)
    return 0
