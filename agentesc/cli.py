"""agentesc command-line interface (HARNESS_SPEC §9)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__, loader, prompts
from .agents.base import Usage
from .agents.scripted import ScriptedAgent
from .pricing import estimate
from .runner import Trial
from .validate import check, d3_false_positive_ids

LEVELS = ["D0", "D1", "D2", "D3"]


def _paths(args) -> list[Path]:
    root = Path(args.scenarios) if args.scenarios else loader.SCENARIO_DIR
    paths = loader.select(root, scenario=getattr(args, "scenario", None), cls=getattr(args, "cls", None))
    if not paths:
        raise SystemExit("no scenarios matched")
    return paths


def cmd_list(args) -> int:
    for p in _paths(args):
        raw = loader.load_raw(p)
        exp = raw.get("scripted_expected", {})
        print(f"{raw['id']:<12} {raw['attack']['vector']:<20} D0/D2/D3 {exp.get('D0','?')[:3]}/"
              f"{exp.get('D2','?')[:3]}/{exp.get('D3','?')[:3]}  {raw['title']}")
    return 0


def cmd_validate(args) -> int:
    results = [check(p) for p in _paths(args)]
    bad = [r for r in results if not r.ok]
    for r in results:
        mark = "ok  " if r.ok else "FAIL"
        print(f"{mark} {r.id:<12} scripted {r.scripted}  D3 benign denials {r.benign.get('D3', {}).get('denials', '-')}")
        for e in r.errors:
            print(f"       - {e}")
    fps = d3_false_positive_ids(results)
    print(f"\n{len(results) - len(bad)}/{len(results)} scenarios pass. "
          f"D3 false positives on benign traces: {len(fps)} ({', '.join(fps) or 'none'}).")
    return 1 if bad else 0


def _make_agent(args, scenario):
    if args.agent in ("scripted", "benign"):
        return ScriptedAgent(scenario, "reference" if args.agent == "scripted" else "benign")
    if not args.model:
        raise SystemExit("--model is required for LLM agents")
    from .agents.llm import AnthropicAgent, OpenAICompatAgent
    if args.agent == "anthropic":
        return AnthropicAgent(args.model, temperature=args.temperature)
    if not args.base_url:
        raise SystemExit("--base-url is required for --agent openai")
    return OpenAICompatAgent(args.model, base_url=args.base_url, temperature=args.temperature)


def cmd_run(args) -> int:
    paths = _paths(args)
    levels = [d.strip() for d in args.defense.split(",")]
    if any(lv not in LEVELS for lv in levels):
        raise SystemExit(f"--defense must be a comma list of {LEVELS}")
    conditions = ["attack", "control"] if args.control else ["attack"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = out_dir / f"run-{args.agent}-{(args.model or 'na').replace('/', '_')}-{stamp}.jsonl"
    header = {
        "type": "header", "version": __version__, "prompt_hash": prompts.prompt_hash(),
        "scenario_hashes": {loader.load_raw(p)["id"]: loader.file_hash(p) for p in paths},
        "params": {k: v for k, v in vars(args).items() if k != "func"},
        "started": stamp,
    }
    total, total_usage = 0, Usage()
    with open(out, "w") as f:
        f.write(json.dumps(header) + "\n")
        for p in paths:
            for cond in conditions:
                sc = loader.load(p, control=(cond == "control"))
                trials = args.trials or sc.trials
                agent = _make_agent(args, sc)
                for level in levels:
                    for t in range(trials):
                        res = Trial(sc, agent, level, monitor=args.monitor,
                                    hide_unauthorized=args.hide_unauthorized).run()
                        total += 1
                        total_usage.add(res.usage)
                        row = {
                            "type": "trial", "scenario": sc.id, "class": sc.class_, "subtechnique": sc.subtechnique,
                            "agent": agent.name, "model": agent.model, "defense": level, "condition": cond,
                            "trial": t, "outcome": res.outcome, "error": res.error, "budget_hit": res.budget_hit,
                            "usage": res.usage.__dict__, "cost_usd": estimate(agent.model, res.usage),
                            "records": res.records,
                        }
                        f.write(json.dumps(row) + "\n")
                        f.flush()
                        o = res.outcome
                        print(f"{sc.id} {level} {cond} #{t}: attempted={o['attempted']} escalated={o['escalated']}"
                              f" task={o['task_completed']}{' ERROR ' + res.error if res.error else ''}",
                              file=sys.stderr)
    cost = estimate(args.model, total_usage) if args.model else None
    print(f"\n{total} trials -> {out}")
    print(f"tokens: in={total_usage.input_tokens} out={total_usage.output_tokens} "
          f"cache_read={total_usage.cache_read_tokens} requests={total_usage.requests}"
          + (f"  est. cost ${cost:.2f}" if cost is not None else ""))
    return 0


def cmd_report(args) -> int:
    from .report import render
    text = render(Path(args.path), validation=args.validation)
    if args.output:
        Path(args.output).write_text(text)
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


def cmd_mcp_serve(args) -> int:
    from .mcp_server import serve
    paths = _paths(args)
    if len(paths) != 1:
        raise SystemExit("mcp-serve needs exactly one --scenario")
    return serve(paths[0], args.defense, trace_path=Path(args.trace))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agentesc", description="AgentEsc privilege-escalation benchmark harness")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", required=True)

    def scen_args(p, single=False):
        p.add_argument("--scenarios", help="scenario directory (default: bundled scenarios/)")
        p.add_argument("--scenario", help="run one scenario id")
        if not single:
            p.add_argument("--class", dest="cls", help="run one class, e.g. PE-3")

    p = sub.add_parser("list", help="list scenarios")
    scen_args(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("validate", help="schema, payload placement, scripted expectations, benign traces")
    scen_args(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("run", help="run trials and write JSONL")
    scen_args(p)
    p.add_argument("--agent", choices=["scripted", "benign", "anthropic", "openai"], required=True)
    p.add_argument("--model")
    p.add_argument("--base-url", help="OpenAI-compatible base URL, e.g. http://localhost:11434/v1")
    p.add_argument("--defense", default="D0,D1,D2,D3")
    p.add_argument("--trials", type=int, help="override each scenario's trial count")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--control", action="store_true", help="also run the no-attack control condition")
    p.add_argument("--monitor", action="store_true", help="flag (do not block) D3 violations at any level")
    p.add_argument("--hide-unauthorized", action="store_true", help="hide tools the active level would deny")
    p.add_argument("--out", default="results")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="render a run's JSONL as Markdown")
    p.add_argument("path")
    p.add_argument("--validation", action="store_true", help="allow scripted/benign runs (construction check)")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("mcp-serve", help="serve one single-agent scenario's tools over MCP (stdio)")
    scen_args(p, single=True)
    p.add_argument("--defense", default="D0", choices=LEVELS)
    p.add_argument("--trace", default="mcp-trace.jsonl")
    p.set_defaults(func=cmd_mcp_serve)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
