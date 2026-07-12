# Changelog

All notable changes to AgentEsc are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
