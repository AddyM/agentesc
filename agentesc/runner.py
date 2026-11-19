"""Trial loop: sessions, agent invocation, messaging and budgets (HARNESS_SPEC §4)."""

from __future__ import annotations

from dataclasses import dataclass

from . import oracle, prompts
from .agents.base import AgentAPIError, BudgetExceeded, Invocation, Usage
from .env import Context, Environment
from .schema import Scenario

MAX_DEPTH = 3
MAX_SESSION_COMPLETIONS = 24
MAX_INVOCATION_COMPLETIONS = 8


@dataclass
class TrialResult:
    outcome: dict
    records: list
    usage: Usage
    error: str | None = None
    budget_hit: bool = False


class _API:
    def __init__(self, runner: "Trial", ctx: Context):
        self.runner, self.ctx = runner, ctx

    def completion(self) -> None:
        self.runner.session_completions += 1
        self.runner.env.completions += 1
        if self.runner.session_completions > MAX_SESSION_COMPLETIONS:
            raise BudgetExceeded("session completion budget")

    def call(self, name: str, args: object) -> str:
        env = self.runner.env
        rec, tool = env.call(self.ctx, name, args)
        if rec.decision == "denied":
            return rec.result
        if name == "send_message":
            to = rec.args["to"]
            if len(self.ctx.chain) > MAX_DEPTH:
                rec.decision, rec.reason, rec.result = "denied", "depth_exceeded", "ERROR: delegation depth exceeded"
                return rec.result
            child = Context(self.ctx.session, self.ctx.principal, self.ctx.chain + [to])
            task = prompts.MESSAGE_TASK.format(sender=self.ctx.agent, content=rec.args["content"])
            reply = self.runner.invoke(to, task, child)
            rec.executed, rec.result = True, reply
            return reply
        if name == "memory_write":
            env.memory[str(rec.args["key"])] = str(rec.args["text"])
            rec.executed, rec.result = True, "stored"
            return rec.result
        if name == "memory_read":
            key = rec.args.get("key")
            if key:
                out = env.memory.get(str(key), "(no note under that key)")
            else:
                out = "\n".join(f"[{k}] {v}" for k, v in env.memory.items()) or "(memory is empty)"
            rec.executed, rec.result = True, out
            return out
        return env.execute(rec, tool)


class Trial:
    def __init__(self, scenario: Scenario, agent, level: str, *, monitor: bool = False,
                 hide_unauthorized: bool = False):
        self.sc = scenario
        self.agent = agent
        self.level = level
        self.env = Environment(scenario, level, monitor=monitor, hide_unauthorized=hide_unauthorized)
        self.session_completions = 0

    def invoke(self, agent_id: str, task: str, ctx: Context) -> str:
        principal = self.sc.principal(ctx.principal)
        inv = Invocation(
            session=ctx.session, agent=agent_id, task=task,
            system=prompts.system_prompt(self.level, agent=agent_id, principal=principal.id,
                                         scopes=principal.scopes),
            tools=self.env.tools_for(ctx), api=_API(self, ctx),
            max_completions=MAX_INVOCATION_COMPLETIONS,
        )
        return self.agent.run(inv)

    def run(self) -> TrialResult:
        self.agent.reset()
        before = Usage()
        before.add(self.agent.usage)
        error, budget_hit = None, False
        for i, s in enumerate(self.sc.sessions, start=1):
            self.session_completions = 0
            ctx = Context(i, s.principal, [s.entry_agent])
            try:
                self.invoke(s.entry_agent, s.user_task, ctx)
            except BudgetExceeded:
                budget_hit = True
            except AgentAPIError as e:
                error = str(e)
                break
        used = Usage(**{k: getattr(self.agent.usage, k) - getattr(before, k) for k in before.__dataclass_fields__})
        outcome = oracle.evaluate(self.sc.success_predicate, self.sc.user_task_check, self.env.records)
        return TrialResult(outcome, [r.to_dict() for r in self.env.records], used, error, budget_hit)
