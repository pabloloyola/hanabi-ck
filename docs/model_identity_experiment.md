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
matches the recorded request except for `provider`, comparing embedded user JSON
by content because logs sort nested keys. It then sends the original recorded
prompt text verbatim with only provider routing replaced. Any other change is refused.
No game action is executed, no existing log is modified, and no retries are used.
The diagnostic output reports elapsed time, action/error, actual returned provider,
usage, and attempt telemetry. It is not an experimental game or a resumed turn.
Without `--log`, `action-check CONFIG --seed 0` checks one initial-state decision.

If the check passes and the returned provider is DeepInfra, run one new v3
BB_hidden full game and audit it before continuing. A successful single request
only establishes that this request worked; provider causation requires replicated
matched route checks. If it fails, inspect the error or HTTP body before changing
model, token budget, timeout, or schema settings.

## Replacement B candidate: Gemini 3.6 Flash

The user's third DeepSeek route check (GMICloud) returned404 at Filter by Parameters.
The response does not identify the incompatible parameter. Do not remove strict
structured output simply to make a route pass. This differs from the DeepInfra
429/shared-pool overload and Venice429/timeout observations.

New `identity_disclosure_openrouter_gemini36_smoke.yaml` and `_pilot.yaml` sources
keep A as GPT-5.4 and set B to `google/gemini-3.6-flash`, pinned to Google AI Studio.
Both use low reasoning effort, though that does not imply equal reasoning compute.
Other game settings and full logging remain fixed. This is a new model-pair study;
its data must not be pooled with the DeepSeek setup as if B were unchanged.
Gemini's structured-output capability and listed provider are documented, but its
availability on the user's account and actual Hanabi performance still need testing.
Roughly similar ability is desirable for interpretation, not an assumption or a
logical requirement of identity disclosure. Assess AA/BB hidden baseline scores
across multiple seeds before describing the models as comparable.

```bash
uv run hanabi-ck identity-prepare \
  configs/identity_disclosure_openrouter_gemini36_smoke.yaml \
  --output configs/generated_identity_smoke_gemini36
uv run hanabi-ck action-check configs/generated_identity_smoke_gemini36/BB_hidden.yaml
```

This is a single initial-state decision for the new model. Do not supply the
DeepSeek `--log`: route diagnostics intentionally reject a model change. If the
check passes, audit one full BB_hidden game before continuing the eight-cell grid.
The `api-check` command is available if diagnosing simple schema/auth failures.

### Gemini empty-object schema diagnostic

Two Gemini action checks returned HTTP200 but failed action validation; the
second exposed an empty object `{}`. This is not a valid decision. The cause is
not established. Google documents numeric minimum/maximum constraints, so test
an equivalent action-index schema without an integer enum:

```bash
uv run hanabi-ck action-check \
  configs/generated_identity_smoke_gemini36/BB_hidden.yaml --action-schema bounds
```

For N legal actions, `enum: [0, ..., N-1]` and integer bounds0..N-1 permit the
same values. `action_index` remains required, extra fields remain forbidden, and
the existing local validator still rejects empty/invalid/out-of-range responses.
The default remains enum for all existing configs. The diagnostic override does
not modify generated configs or manifests. It cannot be used to change the
schema while claiming exact recorded-request identity via `--log`.
If bounds works, prepare a new study version with the selected schema setting;
do not edit already-generated experiment cells midway through a batch.

### Bounds-based Gemini study (v2)

The user's bounds diagnostic succeeded in2.409s and selected a valid rank1 hint.
This establishes that this request worked; it is not yet proof of full-game
reliability or that enum handling caused every earlier failure.

New `identity_disclosure_openrouter_gemini36_bounds_smoke.yaml` / `_pilot.yaml`
sources set `action_index_schema: bounds` for both A and B, so the output encoding
is held fixed across models and identity conditions. New experiment names end
`gpt54_gemini36_v2_bounds`. Preserve the previous enum-based configs/recordings.

```bash
uv run hanabi-ck identity-prepare \
  configs/identity_disclosure_openrouter_gemini36_bounds_smoke.yaml \
  --output configs/generated_identity_smoke_gemini36_bounds
uv run hanabi-ck run configs/generated_identity_smoke_gemini36_bounds/BB_hidden.yaml
uv run hanabi-ck replay-audit \
  runs/identity_disclosure_smoke_gpt54_gemini36_v2_bounds_BB_hidden/ck0/seed_000000.jsonl
```

Audit one completed game before starting the other cells. Then analyze the
manifest in the new generated directory. AA games should also use the new
study settings; do not substitute earlier AA results into this manifest.

## Recover an aborted smoke cell without replacing completed results

The user's AB_named game aborted at turn4 with HTTP402 carrying
`limit_source: openrouter_in_flight_budget` and Retry-After120. This is a transient
reservation limit, distinct from ordinary credit/key-budget failures. Action calls
now retry this exact subtype only when a Retry-After delay is provided. Other402s
still abort. The original request and provider route remain unchanged; retries
and waits are logged, and a short retry notice is printed to stderr. Long waits
are split into60-second sleeps while respecting the full requested delay.

The original smoke configs cap each retry wait at60seconds, so prepare recovery
configs with a180-second cap. Do not edit existing generated configs or logs:

```bash
uv run hanabi-ck identity-recover \
  configs/generated_identity_smoke_gemini36_bounds/manifest.json \
  --output configs/generated_identity_smoke_gemini36_recovery1
uv run hanabi-ck run configs/generated_identity_smoke_gemini36_recovery1/AB_named.yaml
```

For the current user's state this creates AB_named, BA_hidden, and BA_named
configs with experiment suffix `_retry01`, preserving the five valid cells in
the replacement manifest. No requests are made during preparation. Recovery
supports single-seed smoke manifests; mixed multi-seed cells are refused.
It reruns the whole aborted game as a new attempt, rather than resuming its
partial trajectory. Source config and summary hashes are checked, and prior
attempt paths/status remain visible in `identity-analyze` output.

If AB_named completes, run the remaining two new configs:

```bash
for cell in BA_hidden BA_named; do
  uv run hanabi-ck run "configs/generated_identity_smoke_gemini36_recovery1/${cell}.yaml" || break
done
uv run hanabi-ck identity-analyze \
  configs/generated_identity_smoke_gemini36_recovery1/manifest.json
```

The comparison combines retained complete cells with separately recorded recovery
attempts. Report the excluded original abort and operational retry-policy change.
A repeated in-flight error remains bounded by the retry count and wait cap; it
does not trigger provider switching, action fallback, or credit-error retries.

## October 21 update: one-sided disclosure

Four private disclosure modes are now supported. Every player still receives its
own model name. Only disclosure of the **partner's** name changes:

| `identity_disclosure` | Player 0 receives partner name | Player 1 receives partner name |
|---|---|---|
| `hidden` | No | No |
| `named` | Yes | Yes |
| `p0_named` | Yes | No |
| `p1_named` | No | Yes |

The same final sentence is retained in every player's prompt: no statement is
made about what identity information the teammate received. The informed player
is therefore not additionally told that the other player is uninformed. These
are private disclosure treatments, not higher-order knowledge assurances.
Player numbers identify seats, not model labels: in BA, player 0 is model B.

Existing suite files still generate eight cells by default. To include both
one-sided modes, set `disclosure_modes: [hidden, named, p0_named, p1_named]`.
The new config below prepares **16 games at seed 0** (four pairings × four modes):

```bash
uv run hanabi-ck identity-prepare \
  configs/identity_disclosure_openrouter_gemini36_asymmetric_smoke.yaml \
  --output configs/generated_identity_asymmetric_smoke_v1
```

Preparation makes no model calls. This uses a fresh experiment name and does
not reclassify old results or reuse earlier games as new baselines. No paid run
has been performed for the new suite. Validate endpoint availability before runs.

`identity-analyze` retains the existing named-minus-hidden `paired` section and
adds `one_sided_vs_hidden`, with matched-seed differences for each seat's
disclosure versus hidden. Missing/aborted cells do not enter a paired contrast.
Recovery supports the new modes through the existing manifest mechanism.

The funding estimate for eight conditions × ten seeds must be doubled in game
count if all four modes are included: four pairings × four modes × ten seeds
is **160 games**, not 80. A seed-0 smoke remains a descriptive technical check.
