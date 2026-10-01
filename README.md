# hanabi-ck

A small, reproducible Hanabi testbed for studying **common knowledge,
conventions, partner modelling, and coordination in LLM agents**.

The first version intentionally separates:

1. **Game engine** — deterministic Hanabi rules and observations.
2. **Agent interface** — random, simple heuristic, or OpenAI-compatible LLM agents.
3. **Experimental condition** — common-knowledge / convention manipulation.
4. **Instrumentation** — JSONL turn logs with both agent-visible observations and
   researcher-only ground truth.
5. **Metrics** — score, misplays, hints, discards, hint efficiency proxies, and
   cross-condition aggregation.

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

The LLM is asked to return one legal Hanabi action as JSON. Invalid responses are
logged and replaced by a deterministic fallback legal action so experiments do
not silently terminate.

## Common-knowledge ladder

The initial conditions are:

- `ck0`: no convention supplied.
- `ck1_private`: convention supplied only to player 0; player 0 is not told
  whether the partner received it.
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
- selected action and raw agent response (when applicable)
- researcher-only true state
- immediate outcome
- optional probe payloads

A `summary.json` is also produced for each experiment.

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
  lmstudio.yaml

tests/
  test_engine.py
  test_conditions.py
```

## Next milestones

1. Add explicit belief probes after selected turns.
2. Add paired convention-conflict experiments.
3. Add model × model cross-play matrices.
4. Add controlled ablations of memory/history.
5. Add exact epistemic-state annotations for carefully designed micro-Hanabi
   scenarios.
