"""Pydantic models for AgentEsc scenarios (HARNESS_SPEC §3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Vector = Literal[
    "user_prompt",
    "tool_description",
    "schema",
    "tool_result",
    "inter_agent_message",
    "memory",
    "tool_chain",
]
Level = Literal["D0", "D1", "D2", "D3"]
BUILTIN_TOOLS = {"send_message", "memory_write", "memory_read"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(Strict):
    id: str
    scopes: list[str]


class Agent(Strict):
    id: str
    scopes: list[str]
    tools: list[str]
    can_message: list[str] = []


class Effect(Strict):
    type: str
    when: dict[str, Any] = {}
    set: dict[str, Any] = {}
    fields: dict[str, Any] = {}


class Tool(Strict):
    name: str
    server: str = "default"
    trust: Literal["trusted", "untrusted"] = "trusted"
    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    requires_scope: list[str] = []
    returns: str = "ok"
    effects: list[Effect] = []


class Session(Strict):
    principal: str
    entry_agent: str
    user_task: str


class Attack(Strict):
    vector: Vector
    payload: str
    from_agent: str | None = None


class Predicate(Strict):
    type: Literal["tool_executed", "side_effect"]
    tool: str | None = None
    args: dict[str, Any] = {}
    effect: str | None = None
    where: dict[str, Any] = {}

    @model_validator(mode="after")
    def _check(self) -> "Predicate":
        if self.type == "tool_executed" and not self.tool:
            raise ValueError("tool_executed predicate needs 'tool'")
        if self.type == "side_effect" and not self.effect:
            raise ValueError("side_effect predicate needs 'effect'")
        return self


class Step(Strict):
    session: int = 1
    agent: str
    call: str
    args: dict[str, Any] = {}


class Scenario(Strict):
    id: str
    class_: str = Field(alias="class")
    subtechnique: str
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    scope_rationale: str
    principals: list[Principal]
    agents: list[Agent]
    delegation_grants: dict[str, list[str]] = {}
    world: dict[str, Any] = {}
    tools: list[Tool]
    memory_seed: dict[str, str] = {}
    sessions: list[Session]
    attack: Attack
    success_predicate: Predicate
    user_task_check: Predicate
    reference_trace: list[Step]
    benign_trace: list[Step]
    scripted_expected: dict[Literal["D0", "D2", "D3"], Literal["escalates", "contained"]]
    trials: int = 10

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def principal(self, pid: str) -> Principal:
        return next(p for p in self.principals if p.id == pid)

    def agent(self, aid: str) -> Agent:
        return next(a for a in self.agents if a.id == aid)

    def tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)

    @model_validator(mode="after")
    def _refs(self) -> "Scenario":
        pids = {p.id for p in self.principals}
        aids = {a.id for a in self.agents}
        tnames = {t.name for t in self.tools}
        if len(tnames) != len(self.tools):
            raise ValueError("duplicate tool names")
        for a in self.agents:
            for t in a.tools:
                if t not in tnames and t not in BUILTIN_TOOLS:
                    raise ValueError(f"agent {a.id} lists unknown tool {t}")
            for m in a.can_message:
                if m not in aids:
                    raise ValueError(f"agent {a.id} can_message unknown agent {m}")
        for s in self.sessions:
            if s.principal not in pids or s.entry_agent not in aids:
                raise ValueError(f"session refers to unknown principal/agent: {s}")
        for key in self.delegation_grants:
            a, _, b = key.partition("->")
            if a not in aids or b not in aids:
                raise ValueError(f"bad delegation_grants key {key}")
        for st in self.reference_trace + self.benign_trace:
            if st.agent not in aids:
                raise ValueError(f"trace step agent unknown: {st.agent}")
            if st.session < 1 or st.session > len(self.sessions):
                raise ValueError(f"trace step session out of range: {st.session}")
        if self.attack.vector == "inter_agent_message" and self.attack.from_agent not in aids:
            raise ValueError("inter_agent_message attack needs a valid from_agent")
        return self
