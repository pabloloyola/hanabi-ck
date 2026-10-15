"""Usage evidence from retained JSONL logs; never contact a model API."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _calls(record):
    """Recognize action responses and flat/nested micro-experiment probes."""
    nodes = [("", record)]
    nodes.extend((key, value) for key, value in record.items()
                 if isinstance(value, dict) and key.endswith("agent"))
    for node_name, node in nodes:
        for key, api in node.items():
            if key != "api_response" and not key.endswith("_api_response"):
                continue
            prefix = key[:-len("api_response")]
            payload = node.get(prefix + "request_payload") or {}
            request_hash = node.get(prefix + "request_payload_hash")
            agent = node.get("agent") or {}
            associated_agent = record.get(prefix.split("_")[0] + "_agent") or {}
            model = (payload.get("model") or (api or {}).get("model")
                     or node.get("model") or agent.get("model")
                     or associated_agent.get("model"))
            # Rule-based decisions also contain null api_response fields.
            if not (api or payload or request_hash or
                    (not prefix and agent.get("type") == "openai_compatible") or
                    (not prefix and node_name and node.get("model"))):
                continue
            error = node.get(prefix + "error")
            if not prefix:
                error = error or agent.get("error") or node.get("agent_error")
            yield {"model": model or "unknown", "api": api or {},
                   "error": bool(error or (api or {}).get("error")),
                   "attempts": node.get(prefix + "http_attempts"),
                   "role": node_name + ("." if node_name else "") + key}


def _aggregate(calls):
    result = {
        "logged_model_calls": len(calls),
        "calls_with_usage": 0, "calls_with_errors": 0,
        "observed_http_attempts": 0, "calls_without_attempt_telemetry": 0,
        "observed_http_statuses": {},
    }
    values = defaultdict(list)
    statuses = Counter()
    for call in calls:
        api = call["api"]
        usage = api.get("usage") or {}
        result["calls_with_usage"] += bool(usage)
        result["calls_with_errors"] += call["error"]
        attempts = call["attempts"]
        if attempts:
            result["observed_http_attempts"] += len(attempts)
            statuses.update(str(a.get("status_code", "unknown")) for a in attempts)
        else:
            result["calls_without_attempt_telemetry"] += 1
        prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
        completion = usage.get("completion_tokens", usage.get("output_tokens"))
        total = usage.get("total_tokens")
        if total is None and _number(prompt) and _number(completion):
            total = prompt + completion
        details = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
        metrics = {
            "input_tokens": prompt, "output_tokens": completion, "total_tokens": total,
            "reasoning_tokens": details.get("reasoning_tokens"),
            "cached_input_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            "recorded_cost_usd": usage.get("cost"),
        }
        for name, value in metrics.items():
            if _number(value):
                values[name].append(value)
    result["observed_http_statuses"] = dict(statuses)
    for name in ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens",
                 "cached_input_tokens", "recorded_cost_usd"):
        numbers = values[name]
        result[name] = {"calls_reporting": len(numbers),
                        "sum": sum(numbers) if numbers else None,
                        "mean_per_reporting_call": sum(numbers) / len(numbers) if numbers else None}
    return result


def build_usage_report(paths):
    files = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(path)
        files.update(p.resolve() for p in (path.rglob("*.jsonl") if path.is_dir() else [path]))
    all_calls, inventory, duplicates, seen_ids = [], [], [], set()
    experiments, models = defaultdict(list), defaultdict(list)
    game_counts = Counter()
    for path in sorted(files):
        data = path.read_bytes()
        file_calls, game_records, malformed = [], [], []
        experiment = None
        for line_number, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("not an object")
            except (ValueError, TypeError):
                malformed.append(line_number)
                continue
            experiment = record.get("experiment") or experiment
            if record.get("event_kind") in {"turn", "agent_error"}:
                game_records.append(record)
            for call in _calls(record):
                response_id = call["api"].get("id")
                identity = (call["model"], response_id) if response_id else None
                if identity and identity in seen_ids:
                    duplicates.append({"file": str(path), "line": line_number,
                                       "response_id": response_id})
                    continue
                if identity:
                    seen_ids.add(identity)
                file_calls.append(call)
        group = experiment or path.stem
        state = None
        if game_records and file_calls:
            last = game_records[-1]
            state = ("aborted" if last.get("event_kind") == "agent_error" else
                     "terminal" if last.get("game_done") else "incomplete")
            game_counts[state] += 1
        all_calls.extend(file_calls)
        experiments[group].extend(file_calls)
        for call in file_calls:
            models[call["model"]].append(call)
        inventory.append({"file": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                          "experiment": group, "game_state": state,
                          "malformed_lines": malformed, "usage": _aggregate(file_calls)})
    terminal_files = [f for f in inventory if f["game_state"] == "terminal"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Retained JSONL files only; all discovered attempts, including aborted and recovery runs.",
        "notes": [
            "A logged model call is a decision/probe invocation, not an exact HTTP request count.",
            "HTTP retries are counted only where attempt telemetry is retained; missing telemetry is unknown.",
            "Averages use only calls reporting that field; missing usage or cost is not treated as zero.",
            "Reasoning tokens are a subset of output tokens; do not add them again to total tokens.",
            "Recorded cost is usage.cost in USD, not a reconciled invoice. Missing cost is not free usage.",
            "Terminal game counts are log-based, not replay-audit eligibility checks; copies can inflate game counts.",
            "Repeated API response IDs are counted once; calls without response IDs cannot be deduplicated reliably.",
            "Overwritten/deleted logs, unsaved console checks, and unlogged server-side processing are not recoverable.",
        ],
        "overall": _aggregate(all_calls), "game_log_counts": dict(game_counts),
        "mean_logged_model_calls_per_terminal_game_log": (
            sum(f["usage"]["logged_model_calls"] for f in terminal_files) / len(terminal_files)
            if terminal_files else None
        ),
        "by_model": {k: _aggregate(v) for k, v in sorted(models.items())},
        "by_experiment": {k: _aggregate(v) for k, v in sorted(experiments.items()) if v},
        "duplicate_response_references": duplicates, "files": inventory,
    }


def render_usage_markdown(report):
    def fmt(number):
        return "—" if number is None else f"{number:,.2f}"

    lines = ["# Model access usage evidence", "", report["scope"], "",
             f"Generated: {report['generated_at_utc']}", "",
             "| Model | Logged calls | Calls with usage | Total tokens | Mean input/call | Mean output/call | Recorded USD | Cost-reporting calls |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, stats in {**report["by_model"], "ALL": report["overall"]}.items():
        lines.append(f"| {name.replace('|', '/')} | {stats['logged_model_calls']} | "
                     f"{stats['calls_with_usage']} | {fmt(stats['total_tokens']['sum'])} | "
                     f"{fmt(stats['input_tokens']['mean_per_reporting_call'])} | "
                     f"{fmt(stats['output_tokens']['mean_per_reporting_call'])} | "
                     f"{stats['recorded_cost_usd']['sum'] if stats['recorded_cost_usd']['sum'] is not None else '—'} | "
                     f"{stats['recorded_cost_usd']['calls_reporting']} |")
    overall = report["overall"]
    lines.extend(["", f"Game log states: {json.dumps(report['game_log_counts'], sort_keys=True)}.",
                  "Mean logged model calls per terminal game log: "
                  f"{fmt(report['mean_logged_model_calls_per_terminal_game_log'])}.",
                  f"Observed HTTP attempts: {overall['observed_http_attempts']}; "
                  f"calls without attempt telemetry: {overall['calls_without_attempt_telemetry']}.",
                  f"Calls with recorded errors: {overall['calls_with_errors']}.", "",
                  "Reasoning tokens (already included in output): "
                  f"{fmt(overall['reasoning_tokens']['sum'])}; mean per reporting call: "
                  f"{fmt(overall['reasoning_tokens']['mean_per_reporting_call'])}; "
                  f"reporting calls: {overall['reasoning_tokens']['calls_reporting']}.", "",
                  "## Experiment breakdown", "",
                  "| Experiment | Logged calls | Recorded total tokens | Recorded USD |",
                  "|---|---:|---:|---:|"])
    for name, stats in report["by_experiment"].items():
        lines.append(f"| {name.replace('|', '/')} | {stats['logged_model_calls']} | "
                     f"{fmt(stats['total_tokens']['sum'])} | {fmt(stats['recorded_cost_usd']['sum'])} |")
    malformed_count = sum(len(f["malformed_lines"]) for f in report["files"])
    lines.extend(["", f"Malformed lines skipped: {malformed_count}; duplicate response references excluded: "
                  f"{len(report['duplicate_response_references'])}.", "", "## Reading the evidence", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def export_usage_report(paths, output):
    report = build_usage_report(paths)
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    # The report contains aggregates and file hashes, never prompts or credentials.
    (directory / "usage.json").write_text(json.dumps(report, indent=2) + "\n")
    markdown = render_usage_markdown(report)
    (directory / "usage.md").write_text(markdown)
    return markdown
