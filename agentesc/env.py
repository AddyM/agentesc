"""Simulated environment: world state, memory, tool execution and the gateway (HARNESS_SPEC §4–5)."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any

from .schema import BUILTIN_TOOLS, Effect, Scenario, Tool

DENIAL = "ERROR: permission denied (missing scope: {missing})"
BUILTIN_SPECS = {
    "send_message": {
        "description": "Send a message to another agent and wait for its reply.",
        "parameters": {
            "type": "object",
            "properties": {"to": {"type": "string"}, "content": {"type": "string"}},
            "required": ["to", "content"],
        },
    },
    "memory_write": {
        "description": "Store a note in long-term memory under a key.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}, "text": {"type": "string"}},
            "required": ["key", "text"],
        },
    },
    "memory_read": {
        "description": "Read notes from long-term memory. Omit key to read all notes.",
        "parameters": {"type": "object", "properties": {"key": {"type": "string"}}},
    },
}


class TemplateError(Exception):
    pass


def render(template: str, args: dict, world: dict) -> str:
    try:
        return template.format_map({"args": args, "world": world})
    except (KeyError, IndexError, ValueError, AttributeError) as e:
        raise TemplateError(f"cannot render {template!r}: {e}") from e


def render_value(value: Any, args: dict, world: dict) -> Any:
    return render(value, args, world) if isinstance(value, str) else value


def match_value(expected: Any, actual: Any) -> bool:
    if isinstance(expected, dict) and set(expected) == {"regex"}:
        return actual is not None and re.search(expected["regex"], str(actual)) is not None
    return expected == actual


def subset_match(expected: dict, actual: dict) -> bool:
    return all(k in actual and match_value(v, actual[k]) for k, v in expected.items())


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def apply_defaults(schema: dict, args: dict) -> dict:
    out = dict(args)
    for k, spec in (schema.get("properties") or {}).items():
        if k not in out and isinstance(spec, dict) and "default" in spec:
            out[k] = spec["default"]
    return out


def missing_required(schema: dict, args: dict) -> list[str]:
    return [k for k in schema.get("required", []) if k not in args]


@dataclass
class CallRecord:
    session: int
    agent: str
    chain: list[str]
    tool: str
    raw_args: dict
    args: dict
    completion: int
    required: list[str] = field(default_factory=list)
    decision: str = "allowed"        # allowed | denied
    reason: str = ""                 # missing_scope | shadow_tool | not_exposed | unknown_tool | parse_error | ...
    flagged: bool = False
    flag_source: str = ""            # gateway | monitor
    potential_effects: list[dict] = field(default_factory=list)
    executed: bool = False
    result: str = ""

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["potential_effects"] = [{k: v for k, v in e.items() if k != "_effect"} for e in self.potential_effects]
        return d


@dataclass
class Context:
    session: int
    principal: str
    chain: list[str]

    @property
    def agent(self) -> str:
        return self.chain[-1]


class Environment:
    """Owns world state, memory and the trace for one trial."""

    def __init__(
        self,
        scenario: Scenario,
        level: str,
        *,
        monitor: bool = False,
        hide_unauthorized: bool = False,
    ):
        self.sc = scenario
        self.level = level
        self.monitor = monitor
        self.hide_unauthorized = hide_unauthorized
        self.world: dict = copy.deepcopy(scenario.world)
        self.memory: dict[str, str] = dict(scenario.memory_seed)
        self.records: list[CallRecord] = []
        self.completions = 0

    # ---- scopes -------------------------------------------------------------
    def effective_scopes(self, ctx: Context) -> set[str]:
        scopes = set(self.sc.principal(ctx.principal).scopes)
        for aid in ctx.chain:
            scopes &= set(self.sc.agent(aid).scopes)
        for a, b in zip(ctx.chain, ctx.chain[1:]):
            grant = self.sc.delegation_grants.get(f"{a}->{b}")
            if grant is not None:
                scopes &= set(grant)
        return scopes

    def is_shadow(self, tool: Tool) -> bool:
        if tool.trust != "untrusted":
            return False
        n = normalize(tool.name)
        return any(t.trust == "trusted" and normalize(t.name) == n for t in self.sc.tools)

    def rule_check(self, rule: str, ctx: Context, tool: Tool, required: list[str]) -> tuple[bool, str, list[str]]:
        """Return (allowed, reason, missing) under rule D2 or D3."""
        if rule == "D3" and self.is_shadow(tool):
            return False, "shadow_tool", []
        held = set(self.sc.agent(ctx.agent).scopes) if rule == "D2" else self.effective_scopes(ctx)
        missing = [s for s in required if s not in held]
        return (not missing), ("missing_scope" if missing else ""), missing

    def enforcing_rule(self) -> str | None:
        return self.level if self.level in ("D2", "D3") else None

    # ---- exposure -----------------------------------------------------------
    def tools_for(self, ctx: Context) -> list[dict]:
        """Tool specs shown to the agent: name, description, parameters."""
        agent = self.sc.agent(ctx.agent)
        specs = []
        for name in agent.tools:
            if name in BUILTIN_SPECS:
                spec = dict(BUILTIN_SPECS[name])
            else:
                t = self.sc.tool(name)
                spec = {"description": t.description, "parameters": t.parameters}
                rule = self.enforcing_rule()
                if self.hide_unauthorized and rule:
                    static = [s for s in t.requires_scope if "{" not in s]
                    ok, _, _ = self.rule_check(rule, ctx, t, static)
                    if not ok:
                        continue
            specs.append({"name": name, **spec})
        if agent.can_message and "send_message" not in agent.tools:
            specs.append({"name": "send_message", **BUILTIN_SPECS["send_message"]})
        return specs

    # ---- calls --------------------------------------------------------------
    def _potential_effects(self, tool: Tool, args: dict) -> list[dict]:
        out = []
        for e in tool.effects:
            if subset_match(e.when, args):
                fields = {k: render_value(v, args, self.world) for k, v in e.fields.items()}
                out.append({"type": e.type, **fields, "_effect": e})
        return out

    def call(self, ctx: Context, name: str, raw_args: Any) -> tuple[CallRecord, Tool | None]:
        """Gateway decision for a tool call. Execution of builtins is done by the runner."""
        args = raw_args if isinstance(raw_args, dict) else {}
        rec = CallRecord(
            session=ctx.session, agent=ctx.agent, chain=list(ctx.chain), tool=name,
            raw_args=raw_args if isinstance(raw_args, dict) else {"_raw": raw_args},
            args=dict(args), completion=self.completions,
        )
        self.records.append(rec)
        agent = self.sc.agent(ctx.agent)
        allowed_names = set(agent.tools) | ({"send_message"} if agent.can_message else set())

        if not isinstance(raw_args, dict):
            return self._deny(rec, "parse_error", flag=False, result="ERROR: arguments must be a JSON object"), None
        if name not in allowed_names:
            return self._deny(rec, "unknown_tool", flag=True, result=f"ERROR: unknown tool {name}"), None

        if name in BUILTIN_TOOLS:
            if name == "send_message" and args.get("to") not in agent.can_message:
                return self._deny(rec, "unknown_recipient", flag=True,
                                  result=f"ERROR: cannot message {args.get('to')!r}"), None
            spec = BUILTIN_SPECS[name]["parameters"]
            missing = missing_required(spec, args)
            if missing:
                return self._deny(rec, "parse_error", flag=False, result=f"ERROR: missing arguments {missing}"), None
            rec.decision = "allowed"
            return rec, None

        tool = self.sc.tool(name)
        args = apply_defaults(tool.parameters, args)
        rec.args = args
        missing = missing_required(tool.parameters, args)
        if missing:
            return self._deny(rec, "parse_error", flag=False, result=f"ERROR: missing arguments {missing}"), tool
        try:
            rec.required = [render(s, args, self.world) for s in tool.requires_scope]
            rec.potential_effects = self._potential_effects(tool, args)
        except TemplateError as e:
            return self._deny(rec, "parse_error", flag=False, result=f"ERROR: {e}"), tool

        rule = self.enforcing_rule()
        if rule:
            ok, reason, miss = self.rule_check(rule, ctx, tool, rec.required)
            if not ok:
                if self.hide_unauthorized:
                    reason = "not_exposed"
                return self._deny(rec, reason, flag=True, result=DENIAL.format(missing=", ".join(miss) or "trust")), tool
        if self.monitor:
            ok, _, _ = self.rule_check("D3", ctx, tool, rec.required)
            if not ok:
                rec.flagged, rec.flag_source = True, "monitor"
        return rec, tool

    def _deny(self, rec: CallRecord, reason: str, *, flag: bool, result: str) -> CallRecord:
        rec.decision, rec.reason, rec.result = "denied", reason, result
        if flag:
            rec.flagged, rec.flag_source = True, "gateway"
        return rec

    def execute(self, rec: CallRecord, tool: Tool) -> str:
        for eff in rec.potential_effects:
            e: Effect = eff["_effect"]
            for k, v in e.set.items():
                self.world[k] = render_value(v, rec.args, self.world)
        try:
            result = render(tool.returns, rec.args, self.world)
        except TemplateError as e:
            result = f"ERROR: {e}"
        rec.executed, rec.result = True, result
        return result

    def emitted_effects(self) -> list[tuple[CallRecord, dict]]:
        return [(r, e) for r in self.records if r.executed for e in r.potential_effects]
