# LM Studio local identity smoke test

## October 21 update: thinking without schema enforcement

The fixed turn-2 test returned only action JSON in `reasoning_content` when a
schema was enforced. Removing `response_format` produced a reasoning trace and
final JSON in `content`. This supports testing schema interference; it does not
prove the API thinking toggle is honored in both directions or improve game play.

Repeat the original fixed-board four-arm diagnostic without schema enforcement:

```bash
uv run hanabi-ck turn-diagnostic \
  configs/identity_lmstudio_qwen38_hidden.yaml \
  --log runs/identity_lmstudio_qwen38_no_thinking_hidden_v1/ck0/seed_000000.jsonl \
  --turn 2 --output-mode prompt-json \
  --output runs/qwen38_turn2_prompt_json_v1.jsonl
```

The original config remains the reference for validating recorded settings.
`--output-mode prompt-json` removes only schema enforcement from each probe;
the existing four arms still request thinking off/on and original/shuffled order.
Console summaries now include usage and response channel; complete API responses
remain in the output JSONL. These are **requested** thinking settings, not a
verified server-side manipulation.

New candidate full-game configs are available:

- `configs/identity_lmstudio_qwen38_thinking_hidden.yaml`
- `configs/identity_lmstudio_qwen38_thinking_named.yaml`

They request thinking, disable schema enforcement, retain the strict JSON action
parser and abort on invalid output, and use new experiment directories. Existing
configs and recordings are preserved. Validate one action before a full game:

```bash
uv run hanabi-ck action-check configs/identity_lmstudio_qwen38_thinking_hidden.yaml
```

The runner already prefers final `content` over separate reasoning when present.
No JSON repair, prompt change, silent retry or automatic token increase is added.
Full-game validation against the user's LM Studio is still pending.

## Original no-thinking smoke configuration

User's loaded model ID: `qwen/qwen3.8-27b`; server: `http://localhost:1234/v1`.
Observed UI settings: Reasoning Effort Low; Enable Thinking off; Preserve Thinking off.
Local MLX/GGUF quantization, context length, LM Studio version, engine version, and
custom prompt template should be recorded from LM Studio before scientific runs;
`/v1/models` alone does not provide all those details or prove every listed model is loaded.

The two direct full-game configs are `identity_lmstudio_qwen38_hidden.yaml` and
`identity_lmstudio_qwen38_named.yaml`. Both agents use the single loaded model,
with separate private observations and stateless chat requests. They do not require
two copies of the model in memory. CK0, derived mechanical support, matched seed0,
strict bounded-integer action selection, and full logs stay fixed. Identity mode
changes only the disclosure of teammate model ID, as in the cloud experiment.

The configs explicitly request `chat_template_kwargs.enable_thinking: false` and
`preserve_thinking: false`, reusing the project’s existing local template controls.
Do not assume an endpoint honors every custom field: inspect LM Studio server logs
and returned reasoning channels during preflight. The screenshot's Low effort is
recorded here as a UI setting; no unverified OpenRouter reasoning parameter is sent.
With thinking disabled, effort selection does not establish that hidden reasoning
was computed. No prior private agent responses are inserted into the next request.

A local dummy API key prevents accidentally sending the ambient Rakuten/OpenRouter
key to this local endpoint. If local token authentication is enabled, use the actual
LM Studio token through an appropriate local configuration instead. Never put real
credentials in git. These configs are run directly; identity-prepare's remote-suite
credential guard intentionally does not accept inline API keys.

## First check

From the repository root, with LM Studio running and the specified model loaded:

```bash
uv run hanabi-ck action-check configs/identity_lmstudio_qwen38_hidden.yaml
```

This sends one real initial-state action request. Confirm `ok: true`, a valid
`raw_response`, and acceptable elapsed time. It does not execute a game action.
The config uses a4096-token output cap and300-second read timeout as local smoke
settings; these differ from the cloud experiment and must remain separately labelled.
The action schema remains strict; there is no response repair or policy fallback.
Do not infer lack of internal thinking solely from terse schema-constrained output.

## Full-game smoke, then disclosure comparison

```bash
uv run hanabi-ck run configs/identity_lmstudio_qwen38_hidden.yaml
uv run hanabi-ck replay-audit \
  runs/identity_lmstudio_qwen38_no_thinking_hidden_v1/ck0/seed_000000.jsonl
```

After a complete/eligible game:

```bash
uv run hanabi-ck run configs/identity_lmstudio_qwen38_named.yaml
uv run hanabi-ck replay-audit \
  runs/identity_lmstudio_qwen38_no_thinking_named_v1/ck0/seed_000000.jsonl
```

Keep these local results separate from GPT/Gemini cloud results. An initial test of
the same model under two disclosure conditions is sufficient for integration; a
later expanded suite can use another local model or a local/cloud pairing. Preserve
failed attempts with fresh experiment IDs rather than overwriting logs. If context
fills or inference slows as public history grows, capture the error and measured
prompt-token usage before altering model/context settings. The server's loaded
context must accommodate both the prompt and requested output allowance.
# Diagnose thinking and action ordering on a fixed turn

Use the recorded turn 2 rather than starting a new game. This makes four
independent requests: thinking off/on, each with original/shuffled legal actions.
The board, instructions, token budget and output schema stay fixed. The API
request explicitly sets `enable_thinking`; the UI toggle alone does not verify
that the template honors it. Preserve thinking is disabled for every call.

```bash
uv run hanabi-ck turn-diagnostic \
  configs/identity_lmstudio_qwen38_hidden.yaml \
  --log runs/identity_lmstudio_qwen38_no_thinking_hidden_v1/ck0/seed_000000.jsonl \
  --turn 2 \
  --output runs/qwen38_turn2_diagnostic_v1.jsonl
```

The output includes full requests and API responses, reasoning fields if returned,
timings, errors and the mapping from presented indices to original indices.
Every shuffled index moves. The four arms run in a reproducible randomized order;
no game action is executed, no retry or fallback occurs, and existing output files
are protected. Use a fresh output path and `--repetitions 3` for twelve calls.
One call per arm is a diagnostic, not evidence of a stable performance difference.
