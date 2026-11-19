"""Scripted reference agents that replay reference_trace or benign_trace (HARNESS_SPEC §7)."""

from __future__ import annotations

from ..schema import Scenario, Step
from .base import Invocation, Usage


class ScriptedAgent:
    """Replays a trace. On each invocation of agent X it executes the next contiguous
    block of that session's steps belonging to X."""

    model = None

    def __init__(self, scenario: Scenario, which: str = "reference"):
        self.name = "scripted" if which == "reference" else "benign"
        trace = scenario.reference_trace if which == "reference" else scenario.benign_trace
        self.steps: dict[int, list[Step]] = {}
        for st in trace:
            self.steps.setdefault(st.session, []).append(st)
        self.usage = Usage()
        self.reset()

    def reset(self) -> None:
        self.cursor: dict[int, int] = {}

    def run(self, inv: Invocation) -> str:
        steps = self.steps.get(inv.session, [])
        i = self.cursor.get(inv.session, 0)
        last = "done"
        while i < len(steps) and steps[i].agent == inv.agent:
            st = steps[i]
            i += 1
            self.cursor[inv.session] = i
            inv.api.completion()
            last = inv.api.call(st.call, dict(st.args))
            i = self.cursor[inv.session]  # a receiver may have advanced the cursor
        return last
