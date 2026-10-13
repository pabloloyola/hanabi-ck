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
  --output configs/generated_identity_smoke
uv run hanabi-ck api-check configs/generated_identity_smoke/AA_hidden.yaml
uv run hanabi-ck api-check configs/generated_identity_smoke/BB_hidden.yaml
```

Preparation makes eight YAML files and a manifest; it makes **no model requests**.
API checks make small remote requests. Generated directories must be empty.
The manifest pins config hashes and paths; keep the project at the same location
through a batch, and do not edit generated configs midway. Edit the source and
prepare a new experiment instead. Inline credentials are rejected.

## First game, then its disclosure comparison

```bash
uv run hanabi-ck run configs/generated_identity_smoke/AA_hidden.yaml
uv run hanabi-ck replay-audit runs/identity_disclosure_smoke_v1_AA_hidden/ck0/seed_000000.jsonl
```

Check complete/eligible before proceeding. Then:

```bash
uv run hanabi-ck run configs/generated_identity_smoke/AA_named.yaml
uv run hanabi-ck identity-analyze configs/generated_identity_smoke/manifest.json
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
  --output configs/generated_identity_pilot
```

The pilot contains ten matched deck seeds per cell: **80 full games total**.
Run the eight generated configs. Randomize/interleave cell execution order across
independent batches rather than always putting named conditions later. Record that
order; API drift and sampling randomness can affect results. Matching seed controls
the initial deal, not identical trajectories after different actions.

```bash
uv run hanabi-ck identity-analyze configs/generated_identity_pilot/manifest.json
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
