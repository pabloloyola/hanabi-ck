# hanabi-ck

A small, reproducible Hanabi testbed for studying **common knowledge,
conventions, partner modelling, and coordination in LLM agents**.

The first version intentionally separates:

1. **Game engine** — deterministic Hanabi rules and observations.
2. **Agent interface** — random, simple heuristic, or OpenAI-compatible LLM agents.
3. **Experimental condition** — common-knowledge / convention manipulation.
4. **Instrumentation** — JSONL turn logs with both agent-visible observations and
   researcher-only ground truth.
5. **Metrics** — score, misplays, epistemically unsafe plays, hints, discards,
   hint efficiency proxies, and cross-condition aggregation.

The default experiment is 2-player Hanabi, but the engine supports 2–5 players.

## Quick start

```bash
uv sync --extra dev
uv run pytest
uv run hanabi-ck run configs/smoke.yaml
```

Results are written under `runs/`.

The smoke config uses a deterministic baseline that deliberately ignores the
common-knowledge prompt manipulation. Its purpose is to validate game dynamics,
observations, logging, and metrics. The CK rows should therefore match each
other, while the baseline should still produce successful plays and a non-zero
score. The baseline only plays cards that are provably playable under its
hint-derived public knowledge.

## Run a local LLM (LM Studio / OpenAI-compatible API)

Start an OpenAI-compatible server, then:

```bash
export OPENAI_BASE_URL=http://localhost:1234/v1
export OPENAI_API_KEY=lm-studio
uv run hanabi-ck run configs/lmstudio.yaml
```

The same adapter can point at a stronger remote model as long as the endpoint is
OpenAI-compatible. Omit `base_url` and `api_key` from YAML and set
`OPENAI_BASE_URL` / `OPENAI_API_KEY`, or provide them in the agent spec.

Before spending calls on an experiment, validate the endpoint in three stages:
auth/model discovery, a minimal chat completion, and the strict JSON-schema
format used by the harness:

```bash
uv run hanabi-ck api-check configs/micro_pair_probe_deepseek_v4_flash.yaml
```

The command never prints the API key. Remote endpoints now fail immediately with
a clear configuration error if no API key is resolved, instead of silently using
the local LM Studio placeholder key.
For providers that do not accept a request `seed`, set
`vary_api_seed: false`. Provider-specific LM Studio/Qwen fields in
`extra_body` should be removed when switching providers. A clean template is
available at `configs/micro_pair_probe_api.example.yaml`.

The LLM chooses from an indexed list of legal actions and returns only
`{"action_index": N}`. This avoids ambiguous action-shaped JSON and lets the
structured-output schema constrain the choice to an action that is actually
legal in the current state. For research runs, the default
`agent_error_policy: abort` means API failures or malformed responses are
logged and the game is marked invalid **without executing a Hanabi action**. A
`safe_baseline` policy is also available for debugging.

Observations explicitly state `hand_order: oldest_to_newest` and provide
`newest_card_index` for each player, so conventions involving card age do not
depend on an undocumented implementation detail. They also expose
`provably_playable_indices`, `provably_obsolete_indices`, and per-card
`play_safety`. These are deterministic consequences of the acting player's
hint-derived knowledge and the public stacks; they do not use hidden cards.

The logs distinguish **physical success** from **epistemic justification**.
A play can happen to succeed while still being epistemically unsafe. Summaries
therefore include `epistemically_unsafe_plays`, `successful_unsafe_plays`,
and `unsafe_play_rate`.


## Illustrated LaTeX guide

A self-contained illustrated overview of the research question, harness design,
failure modes, micro-scenarios, current results, and next experiments lives at:

`docs/hanabi_ck_harness_guide.tex`

Build it with:

```bash
latexmk -pdf docs/hanabi_ck_harness_guide.tex
```

The figures and result chart are drawn directly in LaTeX with TikZ/PGFPlots, so
the guide does not depend on external image assets.

## Micro-Hanabi diagnostic

Before interpreting full-game score differences, use the one-step diagnostic:

```bash
uv run hanabi-ck micro configs/micro_newest.yaml
```

The starter scenario, `newest_rank1_three_safe`, fixes the game state immediately
after a rank-1 hint touches cards 1, 2, and newest card 4. All three touched cards
are provably playable. The convention therefore changes only which safe card is
intended, not whether the target card is physically or epistemically safe.

The micro runner evaluates all five CK conditions over repeated paired samples.
The default config uses 100 repetitions. It counterbalances CK1 so the acting
receiver (P1) privately receives the convention, varies the model seed by
repetition, and deterministically shuffles the legal action order. A given repetition uses the same action seed and same action order in every
condition. Conditions themselves are executed in a deterministic randomized
order inside each repetition, reducing position bias as well as wall-clock /
server-state confounding.

The main statistic is `newest_selection_rate`:

```text
P(play the newest touched safe card | condition)
```

It also reports a Wilson 95% interval for the newest-selection rate,
`newest_given_safe_candidate_play_rate`, `safe_candidate_play_rate`,
`play_rate`, and action/card-index counts. The summary includes paired
condition comparisons keyed by repetition, with both-positive, neither-positive,
left-only, right-only, and the paired rate difference.

The default config also enables a **shadow intention probe**. The action call is
made first; afterward, a separate stateless request asks only which touched safe
card the partner intended, constrained to the candidate card indices. Probe
output is never inserted into the action prompt or any future context. Probe
seeds use a separate offset from action seeds. The report includes `probe_newest_rate`, its Wilson interval, action/probe
agreement, `recognition_behavior_gap`, and a recognition-vs-behavior table.
Because action and probe are separate stochastic calls, the co-indexed
action/probe statistic is descriptive rather than a causal mediation estimate.

For reproducibility diagnostics, the runner hashes the exact action and probe
request payloads. Pairwise hash-match rates are reported; CK1 and CK2 are
especially useful here because the informed receiver is intentionally given
identical local wording in the one-step scenario.

CK1 and CK2 intentionally have identical local wording for the informed
receiver: the difference between those treatments is whether the partner
actually received the convention, which is not directly observable in this
one-step receiver-only scenario.

Micro logs are written to:

```text
runs/<experiment>/micro/<scenario>/<condition>.jsonl
```


### Two-agent sender → receiver diagnostic

The next step tests both convention **encoding** and **decoding**. Start with
the low-cost smoke run, then scale to the full 100-repetition experiment:

```bash
uv run hanabi-ck micro-pair configs/micro_pair_smoke.yaml
uv run hanabi-ck micro-pair configs/micro_pair_pilot.yaml
uv run hanabi-ck micro-pair configs/micro_pair_probe_pilot.yaml
uv run hanabi-ck micro-pair configs/micro_pair_newest.yaml
```

P0 is given a fixed communication goal: use exactly one legal Hanabi hint to
communicate that P1 should play their newest card. The goal deliberately avoids
naming the numeric slot index, so it cannot be confused with a rank value. The
revised receiver hand also removes rank 4 as a legal sender hint while preserving
the convention-triggering rank-1 touch set [1, 2, 4]. P1 then receives the
observation produced by the actual hint and chooses an action. The pair runner reports the
sender's convention-triggering rank-hint rate, the receiver's newest-card rate,
and receiver success conditional on the sender using the convention-triggering
hint.

For CK1 in this pair experiment, only the sender is informed
(`ck1_informed_players: [0]`). This creates the useful asymmetric case where
the sender may encode with a convention that the receiver cannot assume.

The sender prompt also receives a deterministic annotation of each legal hint's
`touched_indices`. These are mechanically derivable from the visible receiver
hand and are exposed so the diagnostic measures convention use rather than the
model's ability to mentally simulate hint effects.

After the revised 20-repetition pilot showed that the sender still rarely chose
the convention-triggering hint, the harness gained a separate **sender shadow
probe**. The action is sampled first; then a fresh stateless call asks:

- which indexed hint invokes the supplied convention for the communication goal;
- whether the sender's instruction implies that the receiver's convention
  knowledge is `no_convention`, `unknown`, or `known`.

This produces `sender_probe_mapping_accuracy`,
`sender_probe_partner_knowledge_accuracy`, and
`sender_probe_knowledge_to_action_gap`. CK1 and CK2 should both yield
`unknown` for the sender's belief about the receiver because their sender-local
wording is intentionally identical. Run this diagnostic with:

```bash
uv run hanabi-ck micro-pair configs/micro_pair_probe_pilot.yaml
```

That pilot uses 20 repetitions and makes 300 calls: sender action, sender shadow
probe, and receiver action for each condition/repetition.


### Cross-model screen on the Rakuten OpenAI-compatible endpoint

Three matched 5-repetition configs are provided for the currently available
remote models:

```bash
export OPENAI_API_KEY=...

uv run hanabi-ck micro-pair configs/micro_pair_probe_deepseek_v4_flash.yaml
uv run hanabi-ck micro-pair configs/micro_pair_probe_rakutenai_3.yaml
uv run hanabi-ck micro-pair configs/micro_pair_probe_glm_5_3.yaml
```

All three use the same scenario, condition order seed, action-order seeds, and
probe design. Each screen makes 75 API calls. Compare
`sender_probe_mapping_accuracy`, `sender_probe_partner_knowledge_accuracy`,
`sender_convention_hint_rate`, and `sender_probe_knowledge_to_action_gap`
before scaling the strongest candidate to 20 repetitions.

The configs set
`base_url: https://api-opensource-ai.mde.rakuten-it.com/v1`,
`vary_api_seed: false`, and omit LM Studio/Qwen-specific `extra_body`
arguments. If the endpoint rejects strict `json_schema` response formatting,
set `structured_output: false` and rerun; parsing still requires valid JSON.

## Common-knowledge ladder

The initial conditions are:

- `ck0`: no convention supplied.
- `ck1_private`: convention supplied only to designated informed player(s);
  the informed player is not told whether the partner received it. Full-game
  configs default to player 0; micro configs can counterbalance this.
- `ck2_shared`: convention supplied to all agents, but no statement about the
  partner's information.
- `ck3_mutual`: each agent is explicitly told the partner received the same
  convention.
- `ck_inf_common`: the convention is explicitly declared public/common knowledge.

This is an **experimental prompt manipulation**, not a claim that arbitrary-depth
epistemic common knowledge has been formally established inside the model.

## Convention used in the starter experiment

> If a player gives a rank hint that touches the receiver's newest card, the
> receiver should interpret that newest card as intended to be played as soon as
> it is safe to do so.

You can replace the convention in YAML.

## Output

Each game writes one JSONL file. A turn record contains:

- seed / game / condition
- public game state
- the acting player's exact observation
- legal actions
- indexed legal-action list, selected action index, and executed action
- raw agent/API response and response channel (when applicable)
- researcher-only true state
- immediate physical outcome
- epistemic play-safety status for play actions
- optional probe payloads

A `summary.json` is also produced for each experiment.

## Inspect a game

Use the compact inspector to review exactly what each agent could see and what
it did:

```bash
uv run hanabi-ck inspect runs/llm_debug/ck0/seed_000000.jsonl
uv run hanabi-ck inspect runs/llm_debug/ck_inf_common/seed_000000.jsonl
```

Add `--true-state` to show researcher-only hidden cards, or `--raw` to print
the raw model response.

## First LLM debug run

`configs/llm_debug.yaml` is currently configured for
`qwen/qwen3.8-27b`. Change the model identifier if your LM Studio server
exposes a different model, then run:

```bash
uv run hanabi-ck run configs/llm_debug.yaml
```

This deliberately runs just one identical deck seed under `ck0` and
`ck_inf_common` so the two traces can be inspected before scaling up.

## Suggested first experiment

Use the *same deck seeds* in every condition:

```yaml
seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
conditions:
  - ck0
  - ck1_private
  - ck2_shared
  - ck3_mutual
  - ck_inf_common
```

Then compare:

- final score
- failed / perfect games
- life losses
- unsafe-play rate
- successful-but-unsafe plays
- hints used
- successful plays per hint
- invalid-action rate
- cross-play compatibility

The important methodological point is that **score is downstream**. The log is
designed so later versions can add explicit first-, second-, and higher-order
belief probes without changing the engine.

## Repository layout

```text
src/hanabi_ck/
  actions.py       structured actions
  engine.py        Hanabi rules/state
  observations.py  no-hidden-information player views
  conditions.py    CK prompt manipulations
  agents.py        random / heuristic / LLM adapters
  logging.py       JSONL instrumentation
  metrics.py       aggregation
  runner.py        experiment orchestration
  cli.py           command-line entry point

configs/
  smoke.yaml
  llm_debug.yaml
  lmstudio.yaml
  micro_newest.yaml
  micro_pair_smoke.yaml
  micro_pair_pilot.yaml
  micro_pair_newest.yaml

tests/
  test_engine.py
  test_conditions.py
```

## Next milestones

1. Extend shadow belief/intention probes to selected full-game turns.
2. Add paired convention-conflict experiments.
3. Add model × model cross-play matrices.
4. Add controlled ablations of memory/history.
5. Add exact epistemic-state annotations for carefully designed micro-Hanabi
   scenarios.
