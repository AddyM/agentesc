# AgentEsc: A Taxonomy of Privilege-Escalation Threats in Tool-Calling and MCP-Based Agent Systems

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21327893.svg)](https://doi.org/10.5281/zenodo.21327893)

**AgentEsc** is an open, structured taxonomy — and a growing benchmark — for
**privilege-escalation (PE) threats** in agentic AI systems that call tools, use the
Model Context Protocol (MCP), or coordinate as multiple agents.

As LLM agents gain real privileges — file access, API calls, code execution,
money movement — the *authorization boundary* becomes a primary attack surface.
Prompt injection is a delivery mechanism; **privilege escalation is the effect on
that boundary**. Existing catalogs (CoSAI, OWASP) enumerate threats; AgentEsc adds a
*testable* organizing framework that separates whether a system was compromised,
whether it noticed, and whether it contained the attempt.

> **Status:** v0.2 — runnable harness with 15 scenarios, the D0–D3 defense ladder,
> Anthropic and OpenAI-compatible model adapters, and an MCP server. Cross-framework
> results (LangGraph, AutoGen) are next. We welcome contributions.

---

## Why this exists

Three gaps in current agentic-AI security resources:

1. **Enumeration without measurement.** Threat lists tell you what *could* happen but
   give no reproducible way to measure whether a given agent configuration is
   vulnerable.
2. **Injection ≠ escalation.** Most benchmarks measure whether an injected instruction
   is *followed*, not whether it results in an action that *exceeds the agent's
   intended privilege*. AgentEsc measures the authorization effect.
3. **Single-call thinking.** Real escalations often emerge from *composition* — a
   confused-deputy relay between agents, a poisoned memory triggered later, a chain of
   individually-benign tool calls. A per-call policy check misses these. AgentEsc
   models them explicitly.

## What's in this release (v0.2)

- **[`docs/THREAT_TAXONOMY.md`](docs/THREAT_TAXONOMY.md)** — the 5-class taxonomy
  (PE-1 … PE-5) with 15 testable sub-techniques.
- **[`scenarios/`](scenarios/)** — 15 executable scenarios, three per class.
- **[`docs/HARNESS_SPEC.md`](docs/HARNESS_SPEC.md)** — the harness specification:
  scenario format, defense ladder, oracle and metric definitions.
- **Metrics definition** — Escalation Success Rate (ESR), Detection Rate (DR),
  Containment Rate (CR), and a defense ladder (D0–D3) for structured comparison.

## The taxonomy at a glance

| Class | Name | Core idea |
|-------|------|-----------|
| **PE-1** | Authorization-boundary confusion | Agent conflates one principal's/context's privilege with another's |
| **PE-2** | Tool-schema / description manipulation | Attack lives in tool *metadata* the model reads, not the user prompt |
| **PE-3** | Multi-agent orchestration exploits | Escalation emerges from *composition* (confused deputy, message injection) |
| **PE-4** | Persistent-state / memory poisoning | Latent escalation: planted now, triggered later |
| **PE-5** | Tool-chaining / capability composition | Benign calls compose into a privileged effect |

See [`docs/THREAT_TAXONOMY.md`](docs/THREAT_TAXONOMY.md) for the full sub-technique
breakdown, metrics, and defense ladder.

## Roadmap

- [x] v0.1 — Taxonomy, scenario schema, metrics, defense ladder
- [x] v0.2 — Executable harness, 15 scenarios, D0–D3, model adapters, MCP server
- [ ] v0.3 — Full scenario set (~38) and first published model results
- [ ] v0.4 — Cross-framework results (MCP, LangGraph, AutoGen) under D0–D3
- [ ] Companion paper (systematization of knowledge)

## Contributing

Contributions are welcome — new sub-techniques, scenarios, framework adapters, or
corrections. Please open an issue or PR. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quickstart

```bash
git clone https://github.com/AddyM/agentesc && cd agentesc
pip install -e ".[dev,mcp]"

agentesc list                      # 15 scenarios, 3 per class
agentesc validate                  # harness self-check, no API key needed

# Smoke test against a real model (a few cents):
export ANTHROPIC_API_KEY=...
agentesc run --agent anthropic --model claude-haiku-5-5 --class PE-2 --trials 2 --control
agentesc report results/run-anthropic-*.jsonl -o results/report.md
```

Any OpenAI-compatible endpoint works too, including local models:

```bash
agentesc run --agent openai --base-url http://localhost:11434/v1 --model llama3.1 --class PE-3
```

To test an MCP client (Claude Desktop, an IDE agent) directly, serve a scenario's tools
over stdio and point the client at it:

```bash
agentesc mcp-serve --scenario PE-2.1-001 --defense D0 --trace trace.jsonl
```

### What a run measures

For each scenario, model and defense level D0–D3:

| Metric | Meaning |
|---|---|
| ASR | The agent attempted the privileged action |
| ESR | The privileged action executed |
| DR | Attempts that a defense flagged |
| CR | Flagged attempts that did not execute |
| Utility | The user's legitimate task still got done |

`--control` reruns every scenario with the attack text removed; the report shows ESR net
of that control. Scripted reference agents (`--agent scripted|benign`) are harness
self-checks and the report refuses to present them as results. See
[`docs/HARNESS_SPEC.md`](docs/HARNESS_SPEC.md) for exact definitions and
[`docs/VALIDATION.md`](docs/VALIDATION.md) for the construction check.

### Using the taxonomy without running anything

- **Threat-model review.** Walk each of your agent's tools and integrations through
  PE-1 … PE-5 and record which sub-techniques apply.
- **Red-team planning.** Write test cases in the scenario format
  ([`docs/HARNESS_SPEC.md`](docs/HARNESS_SPEC.md) §3) so results stay comparable.

## Used by and cited in

Using AgentEsc in a paper, tool, threat model or course? Open an issue or PR to be
listed here.

## Citing

If you use AgentEsc, please cite it. The concept DOI
[10.5281/zenodo.21327893](https://doi.org/10.5281/zenodo.21327893) always resolves to
the latest version; [`CITATION.cff`](CITATION.cff) has the full metadata, and GitHub's
"Cite this repository" button generates APA and BibTeX from it.

```bibtex
@software{mehra_agentesc_2026,
  author    = {Mehra, Aditya},
  title     = {{AgentEsc: A Taxonomy of Privilege-Escalation Threats in
               Tool-Calling and MCP-Based Agent Systems}},
  year      = {2026},
  version   = {0.2.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21327893},
  url       = {https://github.com/AddyM/agentesc}
}
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Chosen to encourage adoption in both
research and industry tooling.

## Responsible use

AgentEsc describes attack *classes* against agent *frameworks* to help defenders
measure and improve their systems. Scenarios target sandboxed test configurations, not
deployed third-party systems. The project is released to advance defensive
measurement; see [`docs/THREAT_TAXONOMY.md`](docs/THREAT_TAXONOMY.md) §responsible use.
