import json
import tempfile
import unittest
from pathlib import Path

from hanabi_ck.usage_report import build_usage_report, export_usage_report


class TestUsageReport(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, name, records):
        path = self.root / name
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        return path

    def test_missing_usage_retries_duplicates_and_denominators(self):
        first = {
            "event_kind": "turn",
            "experiment": "smoke",
            "game_done": True,
            "agent": {"type": "openai_compatible", "model": "A"},
            "api_response": {
                "id": "unique",
                "model": "A",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                    "cost": 0.002,
                },
            },
        }
        self.write("completed.jsonl", [first])
        self.write("copy.jsonl", [first])
        self.write(
            "abort.jsonl",
            [
                {
                    "event_kind": "agent_error",
                    "experiment": "recovery",
                    "agent": {"type": "openai_compatible", "model": "A", "error": "HTTP 402"},
                    "api_response": None,
                    "http_attempts": [{"status_code": 402}, {"status_code": 402}],
                }
            ],
        )
        report = build_usage_report([self.root, self.root / "completed.jsonl"])
        overall = report["overall"]
        self.assertEqual(overall["logged_model_calls"], 2)
        self.assertEqual(overall["calls_with_usage"], 1)
        self.assertEqual(overall["calls_with_errors"], 1)
        self.assertEqual(overall["input_tokens"]["mean_per_reporting_call"], 100)
        self.assertEqual(overall["total_tokens"]["sum"], 120)
        self.assertEqual(overall["recorded_cost_usd"]["sum"], 0.002)
        self.assertEqual(overall["observed_http_attempts"], 2)
        self.assertEqual(overall["calls_without_attempt_telemetry"], 1)
        self.assertEqual(len(report["duplicate_response_references"]), 1)
        self.assertEqual(report["game_log_counts"], {"aborted": 1, "terminal": 1})

    def test_micro_nested_probe_and_local_diagnostic(self):
        self.write(
            "micro.jsonl",
            [
                {
                    "event_kind": "micro_pair_sample",
                    "experiment": "micro",
                    "sender_agent": {
                        "model": "A",
                        "api_response": {
                            "model": "A",
                            "usage": {"prompt_tokens": 4, "completion_tokens": 6},
                        },
                    },
                    "receiver_agent": {"model": "B", "error": "timeout", "api_response": None},
                    "sender_probe_request_payload_hash": "hash",
                    "sender_probe_api_response": {"model": "A", "usage": {"total_tokens": 3}},
                    "sender_mechanical_probe_api_response": None,
                }
            ],
        )
        self.write(
            "local.jsonl",
            [
                {
                    "thinking_requested": True,
                    "request_payload": {"model": "local", "messages": ["private prompt"]},
                    "api_response": {"model": "local", "usage": {"total_tokens": 9}},
                    "http_attempts": [{"status_code": 200}],
                }
            ],
        )
        report = build_usage_report([self.root])
        self.assertEqual(report["overall"]["logged_model_calls"], 4)
        self.assertEqual(report["overall"]["total_tokens"]["sum"], 22)
        self.assertIsNone(report["overall"]["recorded_cost_usd"]["sum"])
        self.assertEqual(report["by_model"]["B"]["calls_with_errors"], 1)
        self.assertEqual(report["game_log_counts"], {})
        destination = self.root / "evidence"
        markdown = export_usage_report([self.root], destination)
        self.assertIn("local", markdown)
        self.assertNotIn("private prompt", (destination / "usage.json").read_text())

    def test_rule_agents_and_truncated_line(self):
        path = self.write(
            "rules.jsonl",
            [
                {
                    "event_kind": "turn",
                    "game_done": True,
                    "agent": {"type": "simple", "model": None},
                    "api_response": None,
                }
            ],
        )
        with path.open("a") as f:
            f.write('{"partial":')
        report = build_usage_report([path])
        self.assertEqual(report["overall"]["logged_model_calls"], 0)
        self.assertEqual(report["files"][0]["malformed_lines"], [2])
        self.assertEqual(report["game_log_counts"], {})

    def test_game_averages_exclude_partial_tokens_and_aborts(self):
        def game(name, turns, prompt, missing=False, aborted=False, maximum=8):
            rows = []
            for turn in range(turns):
                row = {
                    "event_kind": "turn",
                    "turn": turn,
                    "player": turn % 2,
                    "game_done": turn == turns - 1 and not aborted,
                    "agent": {"model": "A", "type": "openai_compatible"},
                    "request_payload": {
                        "model": "A",
                        "max_tokens": 1000,
                        "response_format": {
                            "json_schema": {
                                "schema": {"properties": {"action_index": {"maximum": maximum}}}
                            }
                        },
                    },
                    "api_response": {
                        "id": f"{name}-{turn}",
                        "model": "A",
                        "usage": {
                            "prompt_tokens": prompt,
                            "completion_tokens": 10,
                            "total_tokens": prompt + 10,
                        },
                    },
                }
                if missing and turn == 0:
                    row["api_response"].pop("usage")
                if aborted and turn == turns - 1:
                    row.update(event_kind="agent_error")
                    row["agent"]["error"] = "timeout"
                rows.append(row)
            return self.write(name, rows)

        game("complete1.jsonl", 2, 100)
        game("complete2.jsonl", 4, 200, maximum=11)
        game("missing.jsonl", 2, 100, missing=True)
        game("abort.jsonl", 2, 100, aborted=True)
        report = build_usage_report([self.root])
        summary = report["completed_full_games"]["overall"]
        self.assertEqual(summary["n_completed_games"], 3)
        self.assertAlmostEqual(summary["mean_model_calls_per_game"], 8 / 3)
        self.assertEqual(summary["total_tokens"]["games_fully_reporting"], 2)
        self.assertEqual(summary["total_tokens"]["mean_per_fully_reported_game"], 530)
        self.assertEqual(summary["input_tokens"]["mean_per_fully_reported_game"], 500)
        self.assertEqual(summary["output_tokens"]["mean_per_fully_reported_game"], 30)
        self.assertIsNone(summary["recorded_cost_usd"]["mean_per_fully_reported_game"])
        self.assertEqual(len(report["completed_full_games"]["by_protocol"]), 1)


if __name__ == "__main__":
    unittest.main()
