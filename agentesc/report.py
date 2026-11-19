"""Turn run JSONL into Markdown tables (HARNESS_SPEC §6, §8, §9)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .metrics import macro, summarize

VALIDATION_AGENTS = {"scripted", "benign"}
VALIDATION_TITLE = "# Harness construction check — not model results\n"


def read(path: Path) -> tuple[dict, list[dict]]:
    header, rows = {}, []
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") == "header":
                header = obj
            else:
                rows.append(obj)
    return header, rows


def _pct(rate) -> str:
    return "n/a" if rate.value is None else f"{rate.value:.0%}"


def _cell(rate) -> str:
    if rate.value is None:
        return "n/a"
    lo, hi = rate.interval
    return f"{rate.value:.0%} ({lo:.0%}–{hi:.0%})"


def render(path: Path, *, validation: bool = False) -> str:
    header, rows = read(path)
    agents = {r["agent"] for r in rows}
    if agents & VALIDATION_AGENTS and not validation:
        raise SystemExit(
            "This run contains scripted/benign agents. Their numbers are harness construction "
            "checks, not model results. Re-run report with --validation to render them."
        )
    errors = sum(1 for r in rows if r.get("error"))
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("error"):
            continue
        cells[(r["scenario"], r["class"], r["agent"], r.get("model") or "-", r["defense"], r["condition"])].append(r["outcome"])

    lines = [VALIDATION_TITLE if validation else "# AgentEsc results\n"]
    lines.append(f"Run: `{path.name}` · harness {header.get('version', '?')} · "
                 f"prompts {header.get('prompt_hash', '?')} · error trials excluded: {errors}\n")
    cost = sum((r.get("cost_usd") or 0) for r in rows)
    if cost:
        lines.append(f"Estimated API cost: ${cost:.2f}\n")

    lines.append("## Per scenario\n")
    lines.append("| Scenario | Agent / model | Defense | Condition | n | ASR | ESR | DR | CR | Utility |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    summaries = {}
    for key in sorted(cells):
        scen, cls, agent, model, defense, cond = key
        s = summarize(cells[key])
        summaries[key] = s
        lines.append(f"| {scen} | {agent} / {model} | {defense} | {cond} | {s['n']} | {_cell(s['asr'])} | "
                     f"{_cell(s['esr'])} | {_pct(s['dr'])} | {_pct(s['cr'])} | {_pct(s['utility'])} |")

    lines.append("\n## Per class (macro-mean over scenarios, min–max, k scenarios)\n")
    lines.append("| Class | Agent / model | Defense | Condition | ESR | ASR | Utility |")
    lines.append("|---|---|---|---|---|---|---|")
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for (scen, cls, agent, model, defense, cond), s in summaries.items():
        groups[(cls, agent, model, defense, cond)].append(s)

    def fmt(m: dict) -> str:
        if m["mean"] is None:
            return "n/a"
        return f"{m['mean']:.0%} ({m['min']:.0%}–{m['max']:.0%}, k={m['k']})"

    for key in sorted(groups):
        cls, agent, model, defense, cond = key
        ss = groups[key]
        lines.append(f"| {cls} | {agent} / {model} | {defense} | {cond} | "
                     f"{fmt(macro([s['esr'].value for s in ss]))} | {fmt(macro([s['asr'].value for s in ss]))} | "
                     f"{fmt(macro([s['utility'].value for s in ss]))} |")

    deltas = []
    for (scen, cls, agent, model, defense, cond), s in summaries.items():
        if cond != "attack":
            continue
        c = summaries.get((scen, cls, agent, model, defense, "control"))
        if c and s["esr"].value is not None and c["esr"].value is not None:
            deltas.append(f"| {scen} | {agent} / {model} | {defense} | {s['esr'].value - c['esr'].value:+.0%} |")
    if deltas:
        lines.append("\n## ESR net of no-attack control\n")
        lines.append("| Scenario | Agent / model | Defense | ESR − control ESR |")
        lines.append("|---|---|---|---|")
        lines.extend(sorted(deltas))

    lines.append("\nASR = attempted the privileged action; ESR = it executed; DR = attempts flagged; "
                 "CR = flagged attempts that did not execute. With one scenario per sub-technique, "
                 "per-sub-technique numbers are anecdotes, not estimates.")
    return "\n".join(lines) + "\n"
