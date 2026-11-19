# Changelog

All notable changes to AgentEsc are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-11-18

First executable release. Design revised after an adversarial review; see
`docs/HARNESS_SPEC.md`.

### Added
- `agentesc` Python package and CLI: `list`, `validate`, `run`, `report`, `mcp-serve`.
- 15 scenarios, three per taxonomy class, with reference and benign traces.
- Simulated environment: world state, memory across sessions, synchronous agent messaging.
- Defense ladder D0–D3 with argument-aware scopes, delegation grants, origin-principal
  tracking and a shadow-tool rule; optional audit-mode monitor and tool hiding.
- Metrics: ASR, ESR, DR, CR, utility and TTC, with Wilson intervals per scenario and a
  no-attack control condition.
- Model adapters for the Anthropic Messages API and any OpenAI-compatible endpoint, with
  token usage and cost estimates.
- MCP server that routes any MCP client's calls through the same gateway.
- Test suite (39 tests) and CI workflow.

### Changed
- Scenario format replaces the v0.1 draft schema in `data/scenarios/SCHEMA_AND_EXAMPLES.md`.

## [0.1.0] - 2026-07-12

Initial public release.

### Added
- Five-class privilege-escalation taxonomy (PE-1 … PE-5) with 15 testable
  sub-techniques (`docs/THREAT_TAXONOMY.md`).
- Declarative scenario schema with two fully-worked example scenarios
  (`data/scenarios/SCHEMA_AND_EXAMPLES.md`).
- Metrics definitions: Escalation Success Rate (ESR), Detection Rate (DR),
  Containment Rate (CR).
- Defense ladder (D0–D3) for structured cross-configuration comparison.
- Project scaffolding: README, LICENSE (Apache-2.0), CITATION.cff, CONTRIBUTING.

### Planned
- v0.2 — Executable scenario dataset (~38 scenarios).
- v0.3 — Evaluation harness + MCP framework adapter.
- v0.4 — Cross-framework results (MCP, LangGraph, AutoGen) under the defense ladder.
