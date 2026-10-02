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
repetition, and deterministically shuffles the legal action order. A given
repetition uses the same action seed and same action order in every condition,
reducing position bias in paired comparisons.

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
seeds use a separate offset from action seeds. The report includes
`probe_newest_rate`, its Wilson interval, action/probe agreement, and a
recognition-vs-behavior table.

CK1 and CK2 intentionally have identical local wording for the informed
receiver: the difference between those treatments is whether the partner
actually received the convention, which is not directly observable in this
one-step receiver-only scenario.

Micro logs are written to:

```text
runs/<experiment>/micro/<scenario>/<condition>.jsonl
```

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
