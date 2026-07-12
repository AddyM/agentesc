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

> **Status:** v0.1 — taxonomy + scenario schema. Benchmark harness and cross-framework
> results are in active development. This is an early, citable release; the structure
> is stable and we welcome contributions.

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

## What's in this release (v0.1)

- **[`docs/THREAT_TAXONOMY.md`](docs/THREAT_TAXONOMY.md)** — the 5-class taxonomy
  (PE-1 … PE-5) with 15 testable sub-techniques.
- **[`data/scenarios/SCHEMA_AND_EXAMPLES.md`](data/scenarios/SCHEMA_AND_EXAMPLES.md)** —
  a declarative scenario schema and two fully-worked example attack scenarios.
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
- [ ] v0.2 — Executable scenario dataset (~38 scenarios across all 5 classes)
- [ ] v0.3 — Evaluation harness + first framework adapter (MCP)
- [ ] v0.4 — Cross-framework results (MCP, LangGraph, AutoGen) under D0–D3
- [ ] Companion paper (systematization of knowledge)

## Contributing

Contributions are welcome — new sub-techniques, scenarios, framework adapters, or
corrections. Please open an issue or PR. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Citing

If you use AgentEsc, please cite it — see [`CITATION.cff`](CITATION.cff). A DOI will be
minted via Zenodo on first tagged release.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Chosen to encourage adoption in both
research and industry tooling.

## Responsible use

AgentEsc describes attack *classes* against agent *frameworks* to help defenders
measure and improve their systems. Scenarios target sandboxed test configurations, not
deployed third-party systems. The project is released to advance defensive
measurement; see [`docs/THREAT_TAXONOMY.md`](docs/THREAT_TAXONOMY.md) §responsible use.
