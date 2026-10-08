# Hanabi-CK handoff

**Repository:** `pabloloyola/hanabi-ck`  
**Branch:** `main`  
**HEAD at handoff:** `4a07af3aa2d750e2cfe005cfc062cc8eed19998b`  
**Date:** 2026-10-08

This file is the starting point for a new ChatGPT session. Read it before
changing experiments, documentation, or the pair runner.

## 1. Immediate goal

We deliberately paused new experiments to do a cleanup pass.

The current priority is:

1. validate the recent refactor;
2. simplify code where it reduces duplication without changing experiment
   semantics;
3. keep the documentation concise and non-redundant;
4. only after that implement the next positive-information replication
   scenario.

Do **not** start another expensive model run until the cleanup/refactor passes
the local test suite.

## 2. Research question

Hanabi-CK asks:

> Does an LLM change its cooperative action when only what it knows about its
> partner's knowledge changes?

The main controlled contrast is CK2 versus CK3:

```text
CK2:
receiver actually has the convention,
but the sender is not assured that the receiver has it

CK3:
sender is explicitly assured that the receiver has the convention
```

These are experimental treatment labels. CK3 is a finite
partner-knowledge-assurance manipulation, not proof of formal common knowledge.

## 3. Main sender-reliance scenario

Scenario name:

```text
sender_reliance_ck2_ck3
```

The sender chooses between:

```text
robust hint:
  rank 1
  does not rely on the convention
  negative information makes the newest card uniquely provably playable

convention hint:
  rank 2
  invokes the newest-card convention
  leaves multiple cards mechanically playable
  is only unambiguous when the receiver can be relied on to know the convention
```

Expected condition-specific policy:

```text
CK2 -> robust
CK3 -> convention
```

The current robust route depends on a **negative-information deduction**. This
matters for the interpretation and for the next replication.

## 4. Current central result

The full canonical result record is:

```text
docs/gpt54_scaffold_factorial_results.md
```

Treat that file as the authoritative result memo.

### Derived versus raw scaffold

GPT-5.4, 20 paired repetitions:

| Wording | Scaffold | CK2 convention | CK3 convention | Desired switches |
|---|---|---:|---:|---:|
| canonical | derived | 4/20 = 20% | 20/20 = 100% | 16/20 |
| canonical | raw | 18/20 = 90% | 20/20 = 100% | 2/20 |
| minimal pair | derived | 1/20 = 5% | 20/20 = 100% | 19/20 |
| minimal pair | raw | 17/20 = 85% | 20/20 = 100% | 3/20 |

The strong CK2 -> CK3 switch is therefore **not scaffold-invariant**. The change
is concentrated in CK2.

### Combined shadow-probe result

Raw minimal-pair, matched 20-pair run:

| Condition | Mechanical exact | Epistemic exact | Direct policy correct |
|---|---:|---:|---:|
| CK2 | 20/20 | 20/20 | 3/20 |
| CK3 | 20/20 | 20/20 | 20/20 |

Critical CK2 classification:

```text
both probes correct + action wrong = 17/20
```

The mechanical-probe request payload was byte-identical across CK2 and CK3 in
all 20 paired repetitions:

```text
hash_match_rate = 1.0
```

So the mechanical probe did not receive the CK manipulation.

### Self-derived intervention

In the first combined intervention run, CK2 changed from:

```text
baseline correct:      3/19 = 15.8%
both-facts correct:   17/18 = 94.4%
```

Among baseline failures where both probes were correct:

```text
14/14 rescued
```

### Factorial intervention: strongest current result

The four arms are:

```text
fresh       original raw prompt again
mechanical  raw prompt + own mechanical-probe output
epistemic   raw prompt + own epistemic-probe output
both        raw prompt + both probe outputs
```

CK2 factorial result:

| Arm | Convention hint | Correct policy | Baseline-failure rescue |
|---|---:|---:|---:|
| fresh | 14/20 = 70% | 6/20 = 30% | 30% |
| mechanical | 0/20 | 20/20 = 100% | 100% |
| epistemic | 18/20 = 90% | 2/20 = 10% | 10% |
| both | 0/20 | 20/20 = 100% | 100% |

The fresh request payload matched baseline in 20/20 CK2 samples. Therefore the
fresh arm is a clean second-sample control.

Paired CK2 comparisons:

```text
fresh vs mechanical:
  14 discordant pairs favor mechanical
  0 favor fresh
  exact two-sided sign/McNemar p ~= 1.22e-4

mechanical vs epistemic:
  18 favor mechanical
  0 favor epistemic
  p ~= 7.63e-6

mechanical vs both:
  0 discordant pairs
```

All four CK3 arms remained 20/20 correct.

## 5. Current interpretation

Use this language:

> GPT-5.4 shows an elicitable-capability / action-policy gap in this controlled
> Hanabi diagnostic. It can independently recover the relevant mechanical
> consequences and partner-knowledge state, but under the raw CK2 action policy
> it usually relies on the convention. Making only its own mechanical
> derivation decision-salient is sufficient to restore the appropriate CK2
> policy in the factorial intervention.

A useful sharper summary is:

```text
mechanical capability      yes
epistemic capability       yes
raw CK2 policy             usually wrong
mechanical self-feedback   rescues CK2
epistemic self-feedback    does not
```

Do **not** claim that the baseline action call internally computed both facts and
then consciously ignored them. The probes are separate stateless elicitation
calls.

Do **not** claim formal common knowledge.

## 6. Historical cross-model result

Under the **derived** scaffold, the minimal-pair comparison was:

| Model | CK2 convention | CK3 convention | Desired switches |
|---|---:|---:|---:|
| GPT-5.4 | 1/20 = 5% | 20/20 = 100% | 19/20 |
| DeepSeek V4 Flash | 18/18 = 100% | 18/19 = 94.7% | 0/17 |
| Claude Sonnet 5.5 | 19/20 = 95% | 20/20 = 100% | 1/20 |

This is still useful, but every claim about GPT's strong CK sensitivity should
now be qualified as **under derived mechanical support**.

## 7. Current code architecture

Important modules:

```text
src/hanabi_ck/
  engine.py
      native Hanabi mechanics

  backends.py
      native/HLE backend boundary

  agents.py
      model adapters
      sender epistemic probe
      sender mechanical probe

  scaffolds.py
      raw/derived mechanical rendering

  micro_scenarios.py
      controlled injected microstates

  micro_runner.py
      receiver-only micro experiments

  pair_micro_runner.py
      orchestration of sender/receiver runs, probes, interventions

  pair_analysis.py
      pair-experiment aggregation and pairwise summaries

  pair_interventions.py
      intervention-arm definitions and prompt rendering

  runner.py
      full-game runner
```

The cleanup pass already moved substantial analysis/intervention logic out of
`pair_micro_runner.py`.

Current approximate sizes at handoff:

```text
pair_micro_runner.py   ~1380 lines
pair_analysis.py        ~857 lines
pair_interventions.py    ~53 lines
README.md               ~317 lines
```

Recent refactor commits include:

```text
262803ee27  Extract pair-micro aggregation into analysis module
269dd78356  Extract pair intervention prompt helpers
e0d61d5bc0  Use extracted pair analysis and intervention modules
75472b84ed  Move pairwise result construction into analysis module
83f945a114  Delegate pairwise summaries to analysis module
20bb3dfd93  Test extracted pair analysis and intervention modules
```

The intent is architectural separation, not behavior change.

## 8. Cleanup status and next code work

The code is much better than before, but the cleanup is **not finished**.

Highest-value next steps:

### A. Run tests locally first

From a fresh pull:

```bash
git pull
uv run pytest
```

Also useful:

```bash
uv run pytest tests/test_pair_micro_runner.py -v
uv run pytest tests/test_agents.py -v
uv run pytest tests/test_backends.py -v
```

Do not assume the refactor is safe until this passes locally. There is no useful
CI status recorded at this handoff.

Historical validated milestone before the latest cleanup:

```text
HLE/backend suite: 14 passed
full repository:   81 passed
```

The latest extraction/refactor needs a fresh local full-suite confirmation.

### B. Continue simplifying pair_micro_runner.py

Good extraction candidates, in order:

1. **probe execution**
   - mechanical shadow-probe execution
   - epistemic shadow-probe execution
   - conversion of decisions into normalized result dictionaries

2. **intervention execution**
   - run one intervention arm
   - run/shuffle all arms
   - build legacy compatibility aliases only if still needed

3. **record construction**
   - sender-only record builder
   - full sender/receiver record builder
   - shared probe/intervention fields

Avoid a giant class hierarchy. Small pure helpers/dataclasses are preferable.

### C. Simplify pair_analysis.py

It is now isolated, but still large.

Good targets:

- shared rate/count helper;
- shared transition-count helper;
- intervention-arm aggregation helper;
- probe aggregation helper;
- explicit typed result structures only where they improve readability.

Do not rename public summary fields during this pass unless tests and docs are
updated together. Existing run-analysis scripts depend on those names.

### D. Preserve semantics

Refactor only. Do not change:

- request prompts;
- request ordering;
- seeds;
- action order;
- condition order;
- probe timing;
- intervention timing;
- logged field names;
- aggregate metric definitions.

A cleanup commit should ideally make old configs produce structurally identical
summaries apart from intentionally added metadata.

## 9. Documentation cleanup status

The documentation was also simplified before this handoff.

Start here:

```text
docs/README.md
```

Operational guide:

```text
docs/experiments.md
```

Canonical result memo:

```text
docs/gpt54_scaffold_factorial_results.md
```

Architecture/HLE decision:

```text
docs/hanabi_source_integration.md
```

Long guide:

```text
docs/hanabi_ck_harness_guide.tex
```

Presentation entry:

```text
docs/hanabi_ck_presentation.md
```

Current presentation evidence modules:

```text
docs/hanabi_ck_presentation_section_09_main_cross_model_result.md
docs/hanabi_ck_presentation_section_10_mechanical_scaffold_ablation.md
docs/hanabi_ck_presentation_section_11_shadow_probes.md
docs/hanabi_ck_presentation_section_12_causal_intervention.md
docs/hanabi_ck_presentation_section_13_interpretation_next_replication.md
docs/hanabi_ck_presentation_section_14_takeaways.md
```

The old misleading filenames for Sections 10–13 were renamed/removed.

Documentation rule going forward:

```text
README
  -> short project entry point

docs/experiments.md
  -> how to run experiments

docs/gpt54_scaffold_factorial_results.md
  -> canonical current numbers/claims

docs/hanabi_source_integration.md
  -> architecture and validation

presentation files
  -> explanatory narrative, not canonical storage of results
```

Avoid growing README back into an experiment diary.

## 10. Key configs

Derived:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_minimal_pair.yaml
```

Raw:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw_minimal_pair.yaml
```

Probes:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_mechanical_probe.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_combined_probe.yaml
```

Interventions:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_self_derived_intervention.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_factorial_intervention.yaml
```

Smoke versions exist for the newer remote experiments. Use them before any new
large paid run.

## 11. Reproducibility invariants

For the main reliance experiments:

```yaml
vary_api_seed: false
shuffle_legal_actions: true
sender_action_order_seed: 20262001
condition_order_seed: 20262003
```

Probe/intervention seed namespaces:

```yaml
sender_probe_seed_offset: 2000000
sender_mechanical_probe_seed_offset: 3000000
sender_intervention_seed_offset: 4000000
sender_intervention_order_seed: 4500000
```

Factorial intervention arm execution order is deterministically shuffled and
logged.

The `fresh` intervention should use exactly the original baseline prompt; its
request hash should match baseline when API seed variation is off.

## 12. Backends / HLE state

DeepMind HLE pinned reference commit:

```text
54e79594f4b6fb40ebb3004289c6db0e34a8b5fb
```

Apple Silicon install:

```bash
CMAKE_ARGS="-DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5" \
uv pip install \
  --python ../../.venv/bin/python \
  --no-build-isolation \
  .
```

Expanded parity validation was completed locally before this cleanup:

```text
tests/test_backends.py: 14 passed
full repository suite: 81 passed
```

Coverage includes rank-5 information-token recovery and 3–5 player parity.

## 13. Next science task — after cleanup

Do **not** add another shadow probe to the current scenario.

The next replication target is a second CK2 -> CK3 sender-reliance microstate
where the robust route is established through **direct positive information**
rather than the current negative-information chain.

Preserve the abstract structure:

```text
CK2 -> robust signal
CK3 -> convention-dependent signal
```

Change:

```text
rank/color values
touch pattern
stack state
mechanism establishing robust playability
```

Desired replication sequence:

```text
1. derived minimal-pair
2. raw minimal-pair
3. combined probes if raw collapses
4. factorial self-feedback if needed
5. only then expand to other models
```

The scientific question is whether the current pattern generalizes:

```text
derived mechanics
    -> strong CK policy distinction

raw mechanics
    -> distinction collapses

mechanical self-feedback
    -> distinction returns
```

If that holds under a positive-information construction, the result is much
harder to explain as an artifact of one negative-information deduction.

## 14. How to start the next chat

Suggested first message to the new assistant:

> Read `HANDOFF.md`, `docs/README.md`, and
> `docs/gpt54_scaffold_factorial_results.md`. We are in a cleanup/refactor
> phase. First verify the current refactor with the local tests, then simplify
> `pair_micro_runner.py` and `pair_analysis.py` without changing experiment
> semantics. Do not start the positive-information replication until cleanup is
> validated.

When the cleanup is complete, update this handoff or replace it with a shorter
current-status note.
