"""Load scenarios from YAML, validate payload placement, substitute the payload."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .schema import Scenario

TOKEN = "{{payload}}"
SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios"

# Where the payload token may appear for each vector (HARNESS_SPEC §3 payload rule).
ALLOWED_PLACES = {
    "user_prompt": {"user_task"},
    "tool_description": {"description"},
    "schema": {"parameters"},
    "tool_result": {"returns"},
    "memory": {"memory_seed", "returns"},
    "inter_agent_message": {"message", "returns"},
    "tool_chain": {"returns", "description", "none"},
}


def _places(raw: dict) -> set[str]:
    """Return the field kinds that contain the payload token."""
    found: set[str] = set()
    for s in raw.get("sessions", []):
        if TOKEN in s.get("user_task", ""):
            found.add("user_task")
    for t in raw.get("tools", []):
        if TOKEN in t.get("description", ""):
            found.add("description")
        if TOKEN in yaml.safe_dump(t.get("parameters", {})):
            found.add("parameters")
        if TOKEN in t.get("returns", ""):
            found.add("returns")
    for v in (raw.get("memory_seed") or {}).values():
        if TOKEN in v:
            found.add("memory_seed")
    for st in raw.get("reference_trace", []):
        if st.get("call") == "send_message" and TOKEN in str(st.get("args", {}).get("content", "")):
            found.add("message")
    return found


def check_placement(raw: dict) -> list[str]:
    vector = raw["attack"]["vector"]
    places = _places(raw) - {"message"} if vector != "inter_agent_message" else _places(raw)
    allowed = ALLOWED_PLACES[vector]
    errors = []
    if not places and "none" not in allowed:
        errors.append(f"vector {vector}: payload token appears nowhere")
    bad = places - allowed
    if bad:
        errors.append(f"vector {vector}: payload token in disallowed place(s) {sorted(bad)}")
    if vector == "inter_agent_message" and "message" not in places:
        errors.append("inter_agent_message: token must appear in a send_message step of reference_trace")
    return errors


def _substitute(obj: Any, payload: str, escaped: str, key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {k: _substitute(v, payload, escaped, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, payload, escaped, key) for v in obj]
    if isinstance(obj, str) and TOKEN in obj:
        # `returns` is rendered with str.format later, so braces in the payload are escaped.
        return obj.replace(TOKEN, escaped if key == "returns" else payload)
    return obj


def load_raw(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load(path: Path, *, control: bool = False) -> Scenario:
    raw = load_raw(path)
    errors = check_placement(raw)
    if errors:
        raise ValueError(f"{path.name}: " + "; ".join(errors))
    payload = "" if control else raw["attack"]["payload"]
    escaped = payload.replace("{", "{{").replace("}", "}}")
    data = _substitute({k: v for k, v in raw.items() if k != "attack"}, payload, escaped)
    data["attack"] = raw["attack"]
    return Scenario.model_validate(data)


def all_paths(root: Path = SCENARIO_DIR) -> list[Path]:
    return sorted(root.rglob("*.yaml"))


def select(root: Path = SCENARIO_DIR, *, scenario: str | None = None, cls: str | None = None) -> list[Path]:
    out = []
    for p in all_paths(root):
        raw = load_raw(p)
        if scenario and raw["id"] != scenario:
            continue
        if cls and raw["class"] != cls:
            continue
        out.append(p)
    return out


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
