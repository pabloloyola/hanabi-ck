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

The **Average per completed full game** table reports mean model calls, input
tokens, output tokens, total tokens and recorded USD per game, for both players
combined. Separate rows identify each model pairing and protocol hash; different
token budgets, reasoning settings and schema modes are not pooled in those rows.
Changing legal-action counts does not create a new protocol group.

Only contiguous terminal turn logs without recorded agent errors, fallbacks,
malformed lines or duplicate API response references enter this table. A game
that ends through lost lives still counts as a completed game. This is a usage
filter, not an integrity audit: use `replay-audit` for scientific eligibility.
Each token/cost average includes only games where every model call reports that
field. The table shows the token- and cost-complete game counts; missing values
are not zero. Aborted/incomplete runs remain in the historical totals above it.

For the eight completed GPT/Gemini identity games reported on October 15, the
reference figures were 592 calls and 3,134,939 tokens: **74 calls and 391,867.375
tokens per completed game**. These are observed historical figures, not a claim
that a local reasoning run will have the same token usage.

Including the two earlier completed AA games and the completed local Qwen game,
the same report contains eleven completed games: 834 calls and 4,409,495 tokens,
averaging **75.82 calls and 400,863.18 tokens per game**. This broader descriptive
average mixes protocols; use the separate protocol rows for a future-run budget.

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
