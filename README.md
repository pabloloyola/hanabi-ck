# hanabi-ck

A reproducible Hanabi testbed for studying **partner knowledge, conventions, and
coordination in LLM agents**.

The core question is:

> Does an LLM change its cooperative action when only what it knows about its
> partner's knowledge changes?

The project uses controlled Hanabi microstates so that physical state,
communication goal, and legal actions can be held fixed while the epistemic
treatment changes.

## Quick start

```bash
uv sync --extra dev
uv run pytest
uv run hanabi-ck run configs/smoke.yaml
```

Receiver-only micro diagnostic:

```bash
uv run hanabi-ck micro configs/micro_newest.yaml
```

Sender/receiver or sender-reliance diagnostics:

```bash
uv run hanabi-ck micro-pair <config.yaml>
```

Results are written under `runs/`.

## Start with the docs

- [Documentation index](docs/README.md)
- [Experiment/config guide](docs/experiments.md)
- [Current GPT-5.4 result](docs/gpt54_scaffold_factorial_results.md)
- [Backend and mechanical-scaffold architecture](docs/hanabi_source_integration.md)
- [Illustrated harness guide](docs/hanabi_ck_harness_guide.tex)
- [Presentation](docs/hanabi_ck_presentation.md)

## Experimental CK ladder

The treatment names are:

| Condition | Meaning for the convention |
|---|---|
| `ck0` | no convention |
| `ck1_private` | one designated player receives it |
| `ck2_shared` | both receive it privately; no assurance about partner knowledge |
| `ck3_mutual` | both receive it and are explicitly told the other did |
| `ck_inf_common` | public/common-knowledge framing |

These labels are experimental approximations. In particular, CK3 is a finite
partner-knowledge-assurance manipulation, not proof of formal common knowledge.

The starter convention is:

> If a player gives a rank hint that touches the receiver's newest card, the
> receiver should interpret that newest card as intended to be played as soon as
> it is safe to do so.

## Main sender-reliance diagnostic

The central controlled scenario is `sender_reliance_ck2_ck3`.

The sender chooses between:

```text
robust hint
  works without relying on the convention

convention hint
  is reliable only when receiver convention knowledge is established
```

Expected policy:

```text
CK2 -> robust
CK3 -> convention
```

The diagnostic is deliberately artificial: its purpose is to isolate a single
epistemic-policy decision.

## Mechanical scaffold is a separate axis

Mechanical support is controlled independently of the CK treatment.

```yaml
mechanical_scaffold: derived
```

`derived` includes deterministic safety summaries and, in the sender-reliance
scenario, precomputed hint consequences.

```yaml
mechanical_scaffold: raw
```

`raw` keeps the legal/public Hanabi state and hint-derived card constraints but
removes hanabi-ck's synthetic safety summaries and precomputed sender hint
effects.

Conceptually:

```text
game/backend state
      ↓
mechanical scaffold: raw | derived
      ↓
CK treatment
      ↓
LLM policy
```

## Current GPT-5.4 finding

The historical derived-scaffold result showed a large CK2 → CK3 switch. Under
the raw scaffold, that behavioral distinction mostly collapses because CK2
becomes convention-heavy.

Independent post-action probes show that GPT-5.4 can nevertheless recover both
the relevant Hanabi mechanics and the partner-knowledge state.

A four-arm intervention then feeds the model's own probe outputs back into a
fresh decision:

| CK2 intervention | Correct policy |
|---|---:|
| fresh retry | 6/20 |
| mechanical feedback only | 20/20 |
| epistemic feedback only | 2/20 |
| both | 20/20 |

All four CK3 arms remain 20/20 correct.

The current interpretation is an **elicitable-capability / action-policy gap**:
in this scenario, making mechanically derived consequences decision-salient is
sufficient to restore the appropriate CK2 policy.

For the full sequence, counts, caveats, and claim language, use
[docs/gpt54_scaffold_factorial_results.md](docs/gpt54_scaffold_factorial_results.md).

## Shadow probes and interventions

The pair harness supports post-action diagnostics:

```yaml
sender_shadow_mechanical_probe: true
sender_shadow_probe: true
```

The baseline action is always sampled first. Shadow-probe answers therefore
cannot change the baseline action.

The factorial intervention supports:

```yaml
sender_intervention_arms:
  - fresh
  - mechanical
  - epistemic
  - both
```

`fresh` repeats the original action prompt and acts as the second-sample
control. The other arms append only the indicated self-derived facts.

See [docs/experiments.md](docs/experiments.md) for the exact configs.

## Game backends

The default backend is the native Python engine:

```yaml
backend: native
```

It supports the injected microstates required by the CK experiments.

An optional DeepMind Hanabi Learning Environment backend is available:

```yaml
backend: hle
```

HLE is used for standard full-game trajectories and independent mechanics
validation, not for arbitrary injected microstates.

The adapter is documented against HLE commit
`54e79594f4b6fb40ebb3004289c6db0e34a8b5fb`.

On Apple Silicon:

```bash
bash scripts/install_hle_macos.sh
uv run pytest tests/test_backends.py -v
```

The expanded local parity suite has passed rank-5 token recovery, complete
2-player seeded trajectories, and 3–5 player cases.

More detail:
[docs/hanabi_source_integration.md](docs/hanabi_source_integration.md).

## Agents

The harness supports deterministic baselines and OpenAI-compatible LLM
endpoints.

For a local LM Studio server:

```bash
export OPENAI_BASE_URL=http://localhost:1234/v1
export OPENAI_API_KEY=lm-studio
uv run hanabi-ck run configs/lmstudio.yaml
```

For remote endpoints, provide the endpoint/model in YAML and the API key through
the environment.

Before spending calls on a new endpoint:

```bash
uv run hanabi-ck api-check <config.yaml>
```

The model selects from an indexed list of legal actions and returns:

```json
{"action_index": 3}
```

Research configs normally use:

```yaml
agent_error_policy: abort
```

so malformed/API-failed actions are logged as invalid rather than silently
replaced by gameplay.

## Observations and safety

Hands are ordered:

```text
oldest -> newest
0 1 2 3 4
```

The harness distinguishes physical success from epistemic justification.

A card is **provably playable** only if every identity still compatible with the
acting player's legal information is currently playable.

This prevents lucky plays from being counted as justified reasoning.

## Reproducibility

The micro runners support:

- paired repetitions;
- deterministic legal-action shuffling;
- deterministic condition-order randomization;
- separate action/probe/intervention seed namespaces;
- exact request-payload hashes;
- raw API response logging;
- Wilson intervals and paired transition summaries.

Important controls and seed conventions are listed in
[docs/experiments.md](docs/experiments.md).

## Repository layout

```text
src/hanabi_ck/
  engine.py              native Hanabi mechanics
  backends.py            native/HLE backend boundary
  agents.py              model adapters and shadow probes
  scaffolds.py           raw/derived mechanical rendering
  micro_scenarios.py     controlled diagnostic states
  micro_runner.py        receiver-only micro experiments
  pair_micro_runner.py   sender/receiver experiment orchestration
  pair_analysis.py       pair-experiment aggregation
  pair_interventions.py  intervention arm definitions/rendering
  runner.py              full-game experiments

configs/                 reproducible experiment configs
tests/                   mechanics, adapters, runners, diagnostics
docs/                    result memo, experiment guide, architecture, presentation
```

## Next research target

Before broadening the model matrix, replicate the mechanism in a mechanically
distinct sender-reliance microstate.

The next target should preserve:

```text
CK2 -> robust signal
CK3 -> convention-dependent signal
```

but make the robust route safe through **direct positive information**, rather
than the current negative-information deduction.

That tests whether the scaffold/intervention result generalizes across
mechanical reasoning structures.
