"""Agent driver interface shared by scripted and LLM agents."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class BudgetExceeded(Exception):
    """Session completion budget exhausted; ends the session, trial is still scored."""


class AgentAPIError(Exception):
    """Model API failed after retries; the trial is marked as an error."""


class ToolAPI(Protocol):
    def call(self, name: str, args: object) -> str: ...
    def completion(self) -> None: ...


@dataclass
class Invocation:
    session: int
    agent: str
    task: str
    system: str
    tools: list[dict]
    api: ToolAPI
    max_completions: int = 8


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    requests: int = 0

    def add(self, other: "Usage") -> None:
        for k in self.__dataclass_fields__:
            setattr(self, k, getattr(self, k) + getattr(other, k))


class Agent(Protocol):
    name: str
    model: str | None
    usage: Usage

    def reset(self) -> None: ...
    def run(self, inv: Invocation) -> str: ...


def post_json(url: str, payload: dict, headers: dict, *, retries: int = 3, timeout: float = 120) -> dict:
    data = json.dumps(payload).encode()
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            last = AgentAPIError(f"HTTP {e.code}: {body}")
            if e.code not in (408, 409, 429, 500, 502, 503, 504, 529):
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = AgentAPIError(str(e))
        if attempt < retries:
            time.sleep(min(2 ** attempt * 2, 30))
    raise last or AgentAPIError("unknown error")
