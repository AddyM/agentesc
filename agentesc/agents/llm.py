"""LLM tool-calling agents: Anthropic Messages API and OpenAI-compatible chat completions."""

from __future__ import annotations

import json
import os

from .base import AgentAPIError, BudgetExceeded, Invocation, Usage, post_json


class AnthropicAgent:
    name = "anthropic"

    def __init__(self, model: str, *, temperature: float = 1.0, max_tokens: int = 4096,
                 base_url: str = "https://api.anthropic.com", api_key: str | None = None):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise SystemExit("ANTHROPIC_API_KEY is not set")
        self.usage = Usage()

    def reset(self) -> None:
        pass

    def _request(self, inv: Invocation, messages: list) -> dict:
        tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                 for t in inv.tools]
        # Cache the stable prefix (tools + system) across turns.
        system = [{"type": "text", "text": inv.system, "cache_control": {"type": "ephemeral"}}]
        payload = {"model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature,
                   "system": system, "messages": messages}
        if tools:
            payload["tools"] = tools
        resp = post_json(f"{self.base_url}/v1/messages", payload,
                         {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        u = resp.get("usage", {})
        self.usage.add(Usage(u.get("input_tokens", 0), u.get("output_tokens", 0),
                             u.get("cache_read_input_tokens", 0) or 0,
                             u.get("cache_creation_input_tokens", 0) or 0, 1))
        return resp

    def run(self, inv: Invocation) -> str:
        messages: list = [{"role": "user", "content": inv.task}]
        text = ""
        for _ in range(inv.max_completions):
            inv.api.completion()
            resp = self._request(inv, messages)
            content = resp.get("content", [])
            messages.append({"role": "assistant", "content": content})
            text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            uses = [b for b in content if b.get("type") == "tool_use"]
            if resp.get("stop_reason") != "tool_use" or not uses:
                return text
            results = []
            for b in uses:
                out = inv.api.call(b["name"], b.get("input", {}))
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": out})
            messages.append({"role": "user", "content": results})
        return text


class OpenAICompatAgent:
    name = "openai"

    def __init__(self, model: str, *, base_url: str, temperature: float = 1.0,
                 max_tokens: int = 4096, api_key: str | None = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.environ.get("AGENTESC_API_KEY", "")
        self.usage = Usage()

    def reset(self) -> None:
        pass

    def run(self, inv: Invocation) -> str:
        tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                   "parameters": t["parameters"]}} for t in inv.tools]
        messages: list = [{"role": "system", "content": inv.system}, {"role": "user", "content": inv.task}]
        text = ""
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        for _ in range(inv.max_completions):
            inv.api.completion()
            payload = {"model": self.model, "messages": messages, "temperature": self.temperature,
                       "max_tokens": self.max_tokens}
            if tools:
                payload["tools"] = tools
            resp = post_json(f"{self.base_url}/chat/completions", payload, headers)
            u = resp.get("usage") or {}
            self.usage.add(Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), 0, 0, 1))
            try:
                msg = resp["choices"][0]["message"]
            except (KeyError, IndexError) as e:
                raise AgentAPIError(f"malformed response: {resp}") from e
            messages.append(msg)
            text = msg.get("content") or ""
            calls = msg.get("tool_calls") or []
            if not calls:
                return text
            for c in calls:
                fn = c.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = fn.get("arguments")  # gateway logs a parse_error
                out = inv.api.call(fn.get("name", ""), args)
                messages.append({"role": "tool", "tool_call_id": c.get("id"), "content": out})
        return text


__all__ = ["AnthropicAgent", "OpenAICompatAgent", "AgentAPIError", "BudgetExceeded"]
