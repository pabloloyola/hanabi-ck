from __future__ import annotations

import argparse
import json

from .inspection import inspect_log
from .micro_runner import run_micro_experiment
from .runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="hanabi-ck")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a full-game experiment YAML config")
    run.add_argument("config")

    micro = sub.add_parser(
        "micro",
        help="Run a repeated one-step micro-Hanabi diagnostic",
    )
    micro.add_argument("config")

    inspect = sub.add_parser(
        "inspect",
        help="Print a compact turn-by-turn view of a JSONL game log",
    )
    inspect.add_argument("log")
    inspect.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Show at most N log records",
    )
    inspect.add_argument(
        "--true-state",
        action="store_true",
        help="Also show researcher-only hidden cards",
    )
    inspect.add_argument(
        "--raw",
        action="store_true",
        help="Also print raw model responses",
    )

    args = parser.parse_args()

    if args.command == "run":
        summary = run_experiment(args.config)
        print(json.dumps(summary["aggregate_by_condition"], indent=2))
    elif args.command == "micro":
        summary = run_micro_experiment(args.config)
        print(
            json.dumps(
                {
                    "aggregate_by_condition": summary["aggregate_by_condition"],
                    "paired_action_vs_baseline": (
                        summary["paired_action_vs_baseline"]
                    ),
                    "paired_probe_vs_baseline": (
                        summary["paired_probe_vs_baseline"]
                    ),
                },
                indent=2,
            )
        )
    elif args.command == "inspect":
        inspect_log(
            args.log,
            limit=args.limit,
            show_true_state=args.true_state,
            show_raw=args.raw,
        )


if __name__ == "__main__":
    main()
