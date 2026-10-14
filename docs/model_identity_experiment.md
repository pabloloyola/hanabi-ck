# Model identity disclosure experiment

Question: does knowing the teammate's actual model ID change Hanabi coordination?
This is an identity-information study, before introducing convention knowledge treatments.

## Design

| Actual pairing (Player 1, Player 2) | Teammate identity hidden | Teammate identity named |
|---|---|---|
| A, A | AA_hidden | AA_named |
| B, B | BB_hidden | BB_named |
| A, B | AB_hidden | AB_named |
| B, A | BA_hidden | BA_named |

The smoke setup reuses model IDs from existing configs: A is `openai/gpt-5.4`,
B is `deepseek/deepseek-v4-flash`. Edit `models.A` / `models.B` before preparing
if a different pair is wanted. Endpoint availability must pass preflight.
A uses low reasoning effort; both have a 16,384-token output limit. These are
new study settings, not continuations of the earlier medium-effort replay.
Each model's settings are identical across its hidden/named conditions.

All cells use two players, native rules, CK0 (no supplied convention), derived
mechanical support, matched deck seeds, abort-on-error, and full request logging.
Player names are neutral (`player_0`, `player_1`), not model labels in prompts.

**Own model identity is disclosed in both conditions.** Only the teammate line changes:

- Hidden: `Your teammate's underlying model identity is not disclosed.`
- Named: `Your teammate's underlying model is <actual configured model ID>.`

Both end with: `No statement is made about what identity information your teammate received.`
Both agents receive the assigned treatment, but we make no explicit mutual-awareness
claim. Hidden means no explicit disclosure, not that identity cannot be inferred
from behavior. No prompt says same-model partners are better or different-model
partners are weaker. A model ID is the configured API identity, not a guarantee
of identical internal weights or deterministic behavior across requests.

## Prepare and preflight

From the repository root, with `OPENROUTER_API_KEY` set:

```bash
uv run hanabi-ck identity-prepare configs/identity_disclosure_openrouter_smoke.yaml \
  --output configs/generated_identity_smoke_v2
uv run hanabi-ck api-check configs/generated_identity_smoke_v2/AA_hidden.yaml
uv run hanabi-ck api-check configs/generated_identity_smoke_v2/BB_hidden.yaml
```

Preparation makes eight YAML files and a manifest; it makes **no model requests**.
API checks make small remote requests. Generated directories must be empty.
The manifest pins config hashes and paths; keep the project at the same location
through a batch, and do not edit generated configs midway. Edit the source and
prepare a new experiment instead. Inline credentials are rejected.

## First game, then its disclosure comparison

```bash
uv run hanabi-ck run configs/generated_identity_smoke_v2/AA_hidden.yaml
uv run hanabi-ck replay-audit runs/identity_disclosure_smoke_v2_AA_hidden/ck0/seed_000000.jsonl
```

Check complete/eligible before proceeding. Then:

```bash
uv run hanabi-ck run configs/generated_identity_smoke_v2/AA_named.yaml
uv run hanabi-ck identity-analyze configs/generated_identity_smoke_v2/manifest.json
```

Partial analysis reports missing cells explicitly. Run the six remaining configs
for a complete smoke grid. Each game is a sequence of model calls and can take
substantial time. Existing identity-study logs are never overwritten. If a game
aborts, preserve it and use a new experiment version for changed settings.
An aborted game is not a low-score completed game.

## Pilot and analysis

After the smoke grid is stable:

```bash
uv run hanabi-ck identity-prepare configs/identity_disclosure_openrouter_pilot.yaml \
  --output configs/generated_identity_pilot_v2
```

The pilot contains ten matched deck seeds per cell: **80 full games total**.
Run the eight generated configs. Randomize/interleave cell execution order across
independent batches rather than always putting named conditions later. Record that
order; API drift and sampling randomness can affect results. Matching seed controls
the initial deal, not identical trajectories after different actions.

```bash
uv run hanabi-ck identity-analyze configs/generated_identity_pilot_v2/manifest.json
```

Primary outcome: per-pairing score difference, named minus hidden, on matching
completed seeds. Secondary descriptive outcomes: hints, misplays, turns, and the
existing safe/unsafe-play metrics. The report includes per-cell valid/aborted
counts, missing seeds/cells, and per-seed differences. Config hash and actual
identity metadata must match the manifest. Pairs containing an error, abort, or
fallback are excluded from paired comparisons; retain and report exclusion counts.

Interpret AA and BB separately, and AB and BA separately, before pooling anything.
Disclosure improvement within a pairing is evidence about identity information;
AA versus AB alone changes actual partner capability as well. Naming models also
introduces reputation cues. This pilot does not establish a CK effect, statistical
significance, or that identical models necessarily share conventions. Later studies
can compare unnamed same/different disclosure and explicit mutual identity awareness.

## Replay

Existing `replay` works on these logs. The inspector's exact private instructions
show the identity treatment. Researcher-only log metadata records actual models even
in hidden conditions; it is never fed to the agent as part of the board observation.

## HTTP reliability controls (v2)

The original v1 DeepSeek smoke cells aborted with HTTP 429; keep those recordings.
V2 applies the same transport retry policy to both models: at most three retries
for HTTP 429 or 503, with 10/20/40-second backoff unless Retry-After specifies a
delay. Retry-After supports seconds and HTTP dates. If the provider requests more
than the 60-second wait cap, abort instead of retrying too early. Requests retain
the exact same payload and provider routing. No completion, parsing failure,
token truncation, timeout, or other HTTP error is retried.

Every opted-in action logs `http_attempts`, including response statuses, failed
response bodies, Retry-After, and retry waits. Final failed response bodies also
appear in `api_response`. Successful retries are not policy fallbacks; report
retry counts when assessing infrastructure reliability. The historical default
is zero retries, so other experiment configs keep their single-attempt behavior.

`run` now exits with code 1 after printing a summary containing an aborted game;
`run ... || break` therefore stops a sequential batch at the first abort.
Use the new v2 generated directory/experiment names, rather than editing v1
configs or overwriting v1 logs. Recreate all comparison cells under v2 controls.

## One-action route diagnostic (v3 DeepInfra)

The user's v2 BB_hidden game stopped at turn 3 with ReadTimeout after a
180-second read wait. No response status arrived. This does not locate the
failure to one particular service. Transport errors are now recorded as
attempts with `status_code: null`, error text, elapsed time, and `retried: false`;
they remain nonretryable. HTTP 429/503 retries retain the existing policy.

OpenRouter lists DeepInfra as an alternative for the same model ID. Separate
`identity_disclosure_openrouter_deepinfra_smoke.yaml` and `_pilot.yaml` sources
pin B to DeepInfra with `only`, disable fallback, and require parameter support.
Other model/decoding settings and the 180-second timeout are unchanged. Do not
assume that availability guarantees schema support or reliable long-game service;
the action check tests this on the user's account. Keep all v1/v2 files and runs.

```bash
uv run hanabi-ck identity-prepare \
  configs/identity_disclosure_openrouter_deepinfra_smoke.yaml \
  --output configs/generated_identity_smoke_v3_deepinfra

uv run hanabi-ck action-check \
  configs/generated_identity_smoke_v3_deepinfra/BB_hidden.yaml \
  --log runs/identity_disclosure_smoke_v2_BB_hidden/ck0/seed_000000.jsonl
```

This sends exactly one HTTP request for the previously failed decision. It
uses only its recorded observation, legal actions, and private instruction,
never researcher hidden state. Before sending, it verifies the rebuilt payload
matches the recorded request except for `provider`. Any other change is refused.
No game action is executed, no existing log is modified, and no retries are used.
The diagnostic output reports elapsed time, action/error, actual returned provider,
usage, and attempt telemetry. It is not an experimental game or a resumed turn.
Without `--log`, `action-check CONFIG --seed 0` checks one initial-state decision.

If the check passes and the returned provider is DeepInfra, run one new v3
BB_hidden full game and audit it before continuing. A successful single request
only establishes that this request worked; provider causation requires replicated
matched route checks. If it fails, inspect the error or HTTP body before changing
model, token budget, timeout, or schema settings.
