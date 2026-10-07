# Hanabi engine/source integration decision

This note records the architectural decision after reviewing three public Hanabi
implementations relevant to this project.

## Sources reviewed

1. **DeepMind Hanabi Learning Environment (HLE)**  
   https://github.com/google-deepmind/hanabi-learning-environment  
   Reference commit used for the adapter:
   `54e79594f4b6fb40ebb3004289c6db0e34a8b5fb`.

2. **Prime Intellect community Hanabi environment**  
   https://app.primeintellect.ai/dashboard/environments/mahesh-ramesh/hanabi  
   Public source currently lives under
   `PrimeIntellect-ai/community-environments/environments/hanabi`.

3. **Mahesh Ramesh Hanabi scaffold-transfer reproduction bundle**  
   https://github.com/Maheshram1/hanabi-eval-bundle  
   This is useful additional context because it implements the
   Watson/Sherlock/Mycroft evaluation stack from the LLM Hanabi work.

The Prime community environment and the Mahesh scaffold-transfer bundle should
not be conflated: the current Prime community environment contains its own
Python Hanabi state/rule implementation, while the scaffold-transfer bundle
wraps `hanabi_learning_environment.pyhanabi`.

## What HLE contributes

HLE is a canonical mechanics/reference implementation. Its low-level
`pyhanabi` API exposes:

- standard 2-5 player game construction;
- seeded initial states;
- legal moves;
- play/discard/reveal transitions;
- information/life tokens;
- fireworks, discards, hands, move history;
- per-player observations;
- accumulated card knowledge including negative information from hints.

Its main mismatch with hanabi-ck is state construction. The public API naturally
creates a standard initial state and advances it through legal moves. It does not
expose a convenient high-level constructor for arbitrary mid-game microstates
with researcher-specified hands, stacks, hint-derived knowledge, and history.

Therefore HLE is a strong backend for standard games and an independent oracle
for mechanics, but not a replacement for the native microstate machinery.

## What the Prime community environment contributes

The Prime environment is primarily an LLM/agent execution environment built on
`verifiers.StatefulToolEnv`.

It provides:

- seeded training/evaluation examples;
- multi-turn model interaction;
- an `action` tool for play/discard/hint;
- automatic turns for multiple model players;
- score-based reward;
- trajectory recording;
- a detailed Hanabi system prompt.

Its game state is implemented directly in Python. It stores positive revealed
color/rank information and instructs the model to reason about negative
information in the prompt.

This is valuable as an example of packaging Hanabi as a train/eval environment,
but it is not a better mechanical oracle than HLE and does not provide the
epistemic treatment machinery needed by hanabi-ck.

We therefore do **not** make `verifiers` or the Prime environment a core
dependency.

## What the Mahesh scaffold-transfer bundle contributes

The scaffold-transfer bundle uses HLE underneath and adds LLM-specific
experimental scaffolding:

- **Watson**: relatively direct game observation;
- **Sherlock**: programmatic deductions / richer mechanical support;
- **Mycroft**: multi-turn state/belief tracking;
- indexed legal moves and parsers;
- detailed per-turn logs;
- replay/resume;
- optional move judging and offline datasets.

For hanabi-ck, the most important idea is to make *mechanical reasoning support*
an experimental axis that is separate from *social epistemic treatment*.

That motivates a later scaffold layer such as:

```text
raw observation        ~ Watson-like
derived knowledge      ~ Sherlock-like
self-tracked belief    ~ Mycroft-like
```

crossed independently with:

```text
CK0 / CK1 / CK2 / CK3 / CK∞
```

## hanabi-ck's distinct role

hanabi-ck is designed around controlled causal manipulations of social
epistemic state.

Its distinctive requirements are:

- private convention delivery;
- partner-knowledge assurance manipulations;
- CK2 -> CK3 minimal pairs;
- arbitrary injected microstates;
- paired action-order controls;
- sender/receiver shadow probes;
- explicit separation of physical success from epistemic justification;
- cross-provider LLM instrumentation.

None of the reviewed environments directly supplies these.

## Architectural decision

The codebase should use a backend boundary:

```text
agents / CK treatments / logging / metrics
                  |
             HanabiBackend
             /          \
       native            HLE
       ------            ---
       microstates       canonical games
       current CK work   mechanics oracle
```

The native engine remains the default.

The HLE backend is optional and is used for:

1. standard full-game experiments;
2. independent mechanical validation;
3. parity tests against the native engine.

The Prime/Verifiers environment remains external for now. If training or
large-scale Verifiers evaluation becomes a goal, hanabi-ck should add an
adapter/export layer rather than move its core experiments into that stack.

## Refactor phases

### Phase A — backend boundary

- [x] Define `HanabiBackend`.
- [x] Expose the current engine as `NativeHanabiBackend`.
- [x] Add optional `HLEHanabiBackend`.
- [x] Route the full-game runner through a backend factory.
- [x] Add initial native/HLE parity checks.
- [x] Run the HLE parity suite on Apple Silicon macOS with the native HLE library built.
- [x] Validate expanded parity coverage for discard-token recovery, life
      exhaustion, and full seeded trajectories through the final round.
- [ ] Validate the newly added rank-5 token-recovery and 3-5 player parity
      cases on the local HLE build.

### Phase B — mechanical scaffold axis

Add scaffold rendering independently of the backend:

```text
backend observation
       |
mechanical scaffold
       |
CK treatment
       |
agent prompt
```

Implemented modes:

- `raw`: backend-normalized observation and hint-derived card constraints,
  without hanabi-ck's synthetic play-safety summaries or precomputed sender
  hint effects;
- `derived`: the historical hanabi-ck prompt with those deterministic
  annotations included.

Additional Phase-B diagnostics:

- a stateless **sender mechanical shadow probe** can be enabled for the
  epistemic-reliance scenario. The sender action is sampled first; a fresh
  request then receives only the player-visible state and the robust/convention
  candidate hints, with no CK instruction or sender goal. It must reconstruct
  touched cards and post-hint provably-playable indices;
- the existing stateless **sender epistemic shadow probe** can be crossed with
  the mechanical probe to classify failures as mechanical, epistemic, or
  policy-integration failures;
- a **self-derived facts intervention** can then make a fresh action call after
  both probes and feed back the model's own structured mechanical and epistemic
  answers. Researcher truth is never substituted for a probe answer. This tests
  whether jointly surfacing the model's elicitable facts at decision time
  rescues the CK2 robust policy.

Planned:

- `self_tracking`: persistent model-maintained belief/memory state across
  turns. This is a separate implementation step because it changes agent state,
  not only prompt rendering.

### Phase C — full-game / cross-play validation

Use HLE-backed standard games to test whether micro-diagnostic CK sensitivity
predicts longer-horizon coordination and cross-play.

### Phase D — optional Verifiers/Prime export

Only if training becomes a project goal:

- export trajectories to a Verifiers-compatible format;
- optionally expose a `load_environment` adapter;
- keep Prime/Verifiers dependencies outside the core package.


## Validation status

On Apple Silicon macOS with Python 3.12.13, the pinned HLE revision builds and
loads successfully with the modern-CMake compatibility flag
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.

The first integrated validation run produced:

```text
tests/test_backends.py: 6 passed
full repository suite: 68 passed
HLE smoke game: valid, score 15, 68 turns, 0 misplays
```

The parity suite has since been expanded further. During validation we found
that HLE and the native engine keep different post-terminal current-player
cursors. This is not actionable game state, so parity now explicitly ends
current-player/observation comparison once both backends report `done=True`.
The corrected expanded suite was rerun successfully on the local Apple
Silicon HLE build: all 11 then-current backend tests passed, including life
exhaustion and three complete 2-player seeded trajectories. Additional rank-5
and 3-5 player cases were added afterward and still require a local rerun.
