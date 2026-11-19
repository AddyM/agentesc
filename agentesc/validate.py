"""Harness construction checks (HARNESS_SPEC §8): schema, payload placement,
scripted_expected, and benign-trace false positives."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .agents.scripted import ScriptedAgent
from .loader import load
from .runner import Trial

LEVELS = ["D0", "D1", "D2", "D3"]


@dataclass
class ScenarioCheck:
    id: str
    errors: list[str] = field(default_factory=list)
    scripted: dict[str, str] = field(default_factory=dict)
    benign: dict[str, dict] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def check(path: Path) -> ScenarioCheck:
    try:
        sc = load(path)
    except Exception as e:  # schema or placement failure
        return ScenarioCheck(id=path.stem, errors=[f"load: {e}"])
    res = ScenarioCheck(id=sc.id)
    for level, expected in sc.scripted_expected.items():
        out = Trial(sc, ScriptedAgent(sc, "reference"), level).run().outcome
        got = "escalates" if out["escalated"] else "contained"
        res.scripted[level] = got
        if got != expected:
            res.errors.append(f"scripted {level}: expected {expected}, got {got}")
    for level in LEVELS:
        out = Trial(sc, ScriptedAgent(sc, "benign"), level).run().outcome
        res.benign[level] = {"denials": out["denials"], "task_completed": out["task_completed"]}
        if out["escalated"]:
            res.errors.append(f"benign {level}: benign trace satisfies the success predicate")
        if level != "D3":
            if out["denials"]:
                res.errors.append(f"benign {level}: {out['denials']} denial(s) on the benign trace")
            if not out["task_completed"]:
                res.errors.append(f"benign {level}: user_task_check failed on the benign trace")
    return res


def d3_false_positive_ids(results: list[ScenarioCheck]) -> list[str]:
    return [r.id for r in results if r.benign.get("D3", {}).get("denials")]
