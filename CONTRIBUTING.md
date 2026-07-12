# Contributing to AgentEsc

AgentEsc aims to be a community reference for privilege-escalation threats in agentic
AI systems. Contributions are welcome and valued.

## Ways to contribute

- **New sub-techniques** — propose additions or refinements to the taxonomy
  (`docs/THREAT_TAXONOMY.md`). Open an issue describing the escalation pattern, why it
  is distinct from existing sub-techniques, and (ideally) a real-world example.
- **Scenarios** — author new attack scenarios following the schema in
  `data/scenarios/SCHEMA_AND_EXAMPLES.md`. Each scenario should be declarative and map
  to a taxonomy sub-technique.
- **Framework adapters** — as the harness matures, adapters for additional agent
  frameworks (LangGraph, AutoGen, CrewAI, MCP servers, etc.) are welcome.
- **Corrections & clarifications** — documentation improvements, references to prior
  work, and clarifications are all helpful.

## How to submit

1. Open an issue to discuss substantial changes before submitting a PR.
2. Fork, create a topic branch, and submit a pull request.
3. Reference the relevant taxonomy class/sub-technique in your PR description.

## Scope and responsible-use expectations

AgentEsc describes attack *classes* against agent *frameworks* to help defenders
measure and improve their systems. Contributions must:

- Target sandboxed/test configurations, not deployed third-party systems.
- Avoid including live credentials, real exploit payloads against production services,
  or personally identifying information.
- Frame attacks in service of *defensive measurement*.

Contributions that appear intended primarily to weaponize against real systems will be
declined.

## Attribution

Contributors will be acknowledged. Significant sustained contributors may be invited as
co-maintainers.
