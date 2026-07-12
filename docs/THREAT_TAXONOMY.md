# A Threat Taxonomy for Privilege Escalation in Tool-Calling Agent Systems

**Working title of paper:** *AGENTESC: A Benchmark and Evaluation Harness for
Privilege-Escalation Attacks in Tool-Calling and MCP-Based Agent Systems*

**Status:** Draft v0.1 — taxonomy design. This is the conceptual contribution the
benchmark operationalizes. Everything empirical hangs off these categories.

---

## 1. Scope and definitions

**Privilege escalation (PE), in an agentic context:** any sequence of interactions
by which an agent (or an adversary acting through an agent's inputs) causes the
system to invoke a tool, access a resource, or perform an action that exceeds the
privilege the agent was intended to hold for the current task, principal, or
session.

This is distinct from — but often chains with — prompt injection. Prompt injection
is a *delivery mechanism*; privilege escalation is the *effect on the authorization
boundary*. Our benchmark measures the effect, not just the injection.

**Why tool-calling / MCP specifically:** The Model Context Protocol standardizes how
agents discover and invoke external tools. That standardization creates a uniform,
cross-vendor attack surface: tool schemas, tool descriptions, resource URIs, and the
orchestration layer that maps model intent to tool execution. PE in this setting is
under-benchmarked relative to its real-world exposure.

---

## 2. The taxonomy (5 classes, testable sub-techniques)

Each sub-technique is written to be *operationalizable* — i.e., we can author a
concrete scenario that attempts it and observe a binary/graded outcome.

### PE-1: Authorization-boundary confusion
The agent conflates the privilege of one principal/context with another.

- **PE-1.1 Cross-principal tool reuse** — an agent servicing user A reuses a
  credential/handle scoped to user B (e.g., cached session, shared connection pool).
- **PE-1.2 Task-scope creep** — the agent invokes a tool outside the declared task
  scope because the orchestration layer does not re-check scope per call.
- **PE-1.3 Delegated-authority overreach** — a sub-agent inherits the full authority
  of the orchestrator rather than a narrowed, task-specific grant.

### PE-2: Tool-schema / description manipulation
The attack lives in the *metadata* the model reads, not the user prompt.

- **PE-2.1 Malicious tool description** — a tool's natural-language description
  contains instructions that steer the model to call it with elevated parameters.
- **PE-2.2 Schema-coercion** — crafted parameter schemas (defaults, enums,
  "required" fields) push the model toward privileged argument values.
- **PE-2.3 Shadow/duplicate tool** — a lower-trust tool masquerades under the name or
  namespace of a higher-trust tool ("tool squatting").

### PE-3: Multi-agent orchestration exploits
The escalation emerges from *composition*, not any single agent.

- **PE-3.1 Confused-deputy relay** — agent X, lacking privilege P, induces
  privileged agent Y to perform P on its behalf.
- **PE-3.2 Message-passing injection** — adversarial content in inter-agent messages
  is treated as trusted control by the receiving agent.
- **PE-3.3 Planner hijack** — the planning/decomposition step is steered to emit a
  sub-task that requires elevated tools.

### PE-4: Persistent-state / memory poisoning
The escalation is *latent*, planted now and triggered later.

- **PE-4.1 Memory-write escalation** — the agent stores attacker-controlled content
  that, on later retrieval, is treated as a privileged instruction.
- **PE-4.2 Retrieval-time trigger** — RAG/memory retrieval surfaces a poisoned record
  at a moment when it can authorize a privileged call.
- **PE-4.3 Cross-session carryover** — poisoned state survives session boundaries and
  escalates in a later, higher-trust session.

### PE-5: Tool-chaining / capability composition
Individually benign tool calls compose into a privileged effect.

- **PE-5.1 Read-then-write chaining** — a read tool exfiltrates a token/path that a
  write tool then consumes to act with elevated effect.
- **PE-5.2 Capability laundering** — a sequence routes a privileged action through a
  tool the policy engine treats as low-risk.
- **PE-5.3 Side-effect amplification** — a nominally low-privilege tool has an
  out-of-band side effect (e.g., triggers a webhook) that escalates.

---

## 3. Metrics (what the harness measures per scenario)

For each (framework, defense-config, scenario) triple:

- **ESR — Escalation Success Rate:** did the privileged action actually execute?
  (binary per trial; rate over N trials to capture non-determinism)
- **DR — Detection Rate:** did any guardrail/monitor flag the attempt, regardless of
  whether it succeeded?
- **CR — Containment Rate:** if the attempt was flagged, was the privileged action
  actually blocked (not merely logged)?
- **Optional: TTC — Turns-to-Compromise:** interaction turns needed, as a difficulty
  proxy.

Reporting ESR *and* (DR, CR) separately is the key analytical move: it separates
"the system never noticed" from "the system noticed but didn't stop it" — a
distinction current agent-security discussion collapses.

---

## 4. Defense configurations to compare

To make results actionable, run each framework under a small ladder of defenses:

- **D0 Baseline** — framework defaults, no added guardrail.
- **D1 Prompt-hardening** — system-prompt-level scope constraints only.
- **D2 Policy engine** — an external allow/deny check on each tool call (deterministic).
- **D3 Least-privilege broker** — per-call, per-principal capability scoping.

The interesting empirical claim will be *where on this ladder each attack class stops
working* — e.g., "PE-2 defeats D0–D1 but D2 contains it; PE-3/PE-4 survive to D2 and
need D3."

---

## 5. Framework matrix (kept deliberately small for a 6-week solo build)

- **MCP-based agent (primary)** — canonical tool-calling target.
- **LangGraph** — graph/stateful orchestration.
- **AutoGen** — multi-agent conversation orchestration.

(CrewAI and others deferred — three frameworks give cross-system generalization
without overrunning the timeline.)

---

## 6. Relationship to prior work (for the Related Work section)

- CoSAI MCP security taxonomy (2026) — threat *enumeration*; we add *executable
  measurement* and cross-framework comparison.
- OWASP Agentic Top-10 / ASI (2026) — risk *catalog*; we operationalize a slice
  (privilege/identity abuse) into a benchmark.
- Prompt-injection benchmarks — adjacent; we measure the *authorization effect*, not
  injection success per se.
- Confused-deputy literature (classic security) — we port it into the agent setting
  and quantify it.

The gap we fill: **no reproducible, cross-framework benchmark that isolates
privilege escalation as a measurable outcome with a defense ladder.**
