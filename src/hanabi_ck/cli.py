from __future__ import annotations

import argparse
import json

from .runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="hanabi-ck")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run an experiment YAML config")
    run.add_argument("config")

    args = parser.parse_args()

    if args.command == "run":
        summary = run_experiment(args.config)
        print(json.dumps(summary["aggregate_by_condition"], indent=2))


if __name__ == "__main__":
    main()
