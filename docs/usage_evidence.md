# Model usage evidence for funding

Generate a read-only summary of retained experiment logs:

```bash
uv run hanabi-ck usage-report runs --output runs/usage_evidence
```

This prints tables and writes `runs/usage_evidence/usage.md` and `usage.json`.
The Markdown report is intended for review; the JSON includes the denominators
for each average, experiment/model breakdowns, and source file SHA-256 hashes.
Prompts, response text and API credentials are excluded from the report.
Regeneration replaces these two report files; source logs are never modified.

For a restricted experiment family, pass its directories or JSONL files:

```bash
uv run hanabi-ck usage-report \
  runs/identity_disclosure_smoke_gpt54_gemini36_v2_bounds_* \
  --output runs/identity_usage_evidence
```

The tool recognizes full-game action logs, turn diagnostics, micro experiments,
and nested sender/receiver/probe responses. It includes failed/recovery attempts
found within the selected files. One logged decision/probe is one model invocation;
HTTP retries are shown separately where attempt telemetry exists. API response IDs
are deduplicated across files; calls lacking IDs cannot be reliably deduplicated.
Retain only one copy of each source game when interpreting per-game averages.

Token and cost averages use the calls reporting each field. Missing usage is
unknown, and missing cost does not mean free usage. Reasoning tokens are included
within output tokens, not added a second time. `usage.cost` is a recorded USD cost,
not an invoice reconciliation. Token totals are reported usage only; discarded,
overwritten and unsaved console calls cannot be recovered. Malformed lines are
listed in the JSON and counted in the Markdown report.

For a funding estimate, first select a representative, fixed-protocol pilot and
measure cost per completed game with complete cost reporting. Keep the historical
debugging/recovery costs separate from the expected cost of future valid games.
Multiply the per-game estimate by planned pairings, disclosure conditions and
seeds; state the retry allowance explicitly. Historical model prices and token
budgets should not silently become assumptions for a different model or protocol.
