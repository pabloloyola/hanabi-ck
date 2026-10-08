# GPT-5.4 mechanical-scaffold and intervention results

This note records the current sender-reliance result sequence for the
`sender_reliance_ck2_ck3` diagnostic. It is intended to be the canonical
reference for the presentation and paper draft.

## Diagnostic

The sender chooses between:

- **robust hint**: rank 1, which does not invoke the convention and makes the
  newest card the uniquely provably playable receiver card;
- **convention hint**: rank 2, which invokes the convention but leaves multiple
  receiver cards provably playable.

The intended condition-specific policy is:

```text
CK2: receiver convention knowledge is not established -> robust hint
CK3: receiver convention knowledge is established     -> convention hint
```

The physical state, goal, legal actions, and convention are held fixed.

## 1. Derived versus raw mechanical scaffold

The historical `derived` scaffold supplies deterministic hint consequences.
The `raw` scaffold withholds hanabi-ck's synthetic safety summaries and
precomputed sender hint effects.

| Wording | Scaffold | CK2 convention | CK3 convention | Desired CK2 robust -> CK3 convention switches |
|---|---|---:|---:|---:|
| canonical | derived | 4/20 = 20% | 20/20 = 100% | 16/20 |
| canonical | raw | 18/20 = 90% | 20/20 = 100% | 2/20 |
| minimal pair | derived | 1/20 = 5% | 20/20 = 100% | 19/20 |
| minimal pair | raw | 17/20 = 85% | 20/20 = 100% | 3/20 |

The scaffold effect is concentrated in CK2. CK3 remains at ceiling.

Interpretation: GPT-5.4's CK-sensitive sender policy is not scaffold-invariant.
When deterministic Hanabi consequences are supplied, the model strongly
distinguishes CK2 from CK3. Under the raw scaffold it usually chooses the
convention-dependent hint already in CK2.

## 2. Independent shadow probes

A post-action mechanical shadow probe receives no CK treatment or sender goal.
It reconstructs, for the robust and convention candidate hints:

```text
touched_indices
receiver_provably_playable_indices_after_hint
```

A separate epistemic shadow probe identifies the convention hint and classifies
receiver convention knowledge as `no_convention`, `unknown`, or `known`.

In the matched 20-pair combined-probe run:

| Condition | Mechanical exact | Epistemic exact | Direct policy correct |
|---|---:|---:|---:|
| CK2 | 20/20 = 100% | 20/20 = 100% | 3/20 = 15% |
| CK3 | 20/20 = 100% | 20/20 = 100% | 20/20 = 100% |

CK2 therefore contained:

```text
both probes correct + action wrong = 17/20
```

The mechanical-probe request payload was identical across CK2 and CK3 in all
20 paired repetitions, confirming that the mechanical probe itself had no access
to the epistemic manipulation.

This supports a capability-policy gap: the relevant mechanical and epistemic
capabilities are independently elicitable from the same model, but are not
reliably expressed in the raw CK2 action policy.

## 3. Self-derived facts intervention

After the baseline action and both shadow probes, a fresh action call receives
the original raw prompt plus the model's own structured probe outputs. Researcher
ground truth is not substituted for a probe answer.

In the first matched intervention run:

| CK2 stage | Convention hint | Correct condition-specific policy |
|---|---:|---:|
| raw baseline | 16/19 = 84.2% | 3/19 = 15.8% |
| self-derived both-facts intervention | 1/18 = 5.6% | 17/18 = 94.4% |

Among baseline CK2 failures, 14/15 were rescued. Among baseline failures for
which both probes were correct, 14/14 were rescued.

CK3 stayed at ceiling before and after intervention.

## 4. Factorial intervention ablation

The follow-up decomposes the intervention into four arms:

```text
fresh       = original raw prompt again; no probe facts
mechanical  = feed back only the mechanical-probe output
epistemic   = feed back only the epistemic-probe output
both        = feed back both outputs
```

In the matched 20-pair factorial run, the CK2 baseline chose the convention hint
20/20 times while both probes were exact 20/20.

| CK2 arm | Convention hint | Correct policy | Baseline-failure rescue |
|---|---:|---:|---:|
| fresh | 14/20 = 70% | 6/20 = 30% | 30% |
| mechanical | 0/20 = 0% | 20/20 = 100% | 100% |
| epistemic | 18/20 = 90% | 2/20 = 10% | 10% |
| both | 0/20 = 0% | 20/20 = 100% | 100% |

The fresh request hash matched the baseline request in 20/20 CK2 samples. Thus
fresh is a genuine repeated sample from the same request payload, and its 30%
accuracy establishes that simple retry/nondeterminism can help somewhat.

The decisive comparisons are:

- mechanical versus fresh: 14 discordant pairs favor mechanical, 0 favor fresh;
- mechanical versus epistemic: 18 discordant pairs favor mechanical, 0 favor
  epistemic;
- mechanical versus both: 0 discordant pairs; both are 20/20 correct.

Two-sided exact paired sign/McNemar probabilities are approximately
`1.22e-4` for mechanical versus fresh and `7.63e-6` for mechanical versus
epistemic. These are descriptive diagnostics over repeated model calls, not
population-level human-subject inference.

All four CK3 arms remained 20/20 convention and 20/20 policy-correct.

## 5. Current interpretation

The factorial result localizes the dominant bottleneck more sharply than
"epistemic recognition."

GPT-5.4 can independently:

1. derive the relevant Hanabi consequences;
2. classify CK2 receiver convention knowledge as unestablished/unknown;
3. classify CK3 receiver convention knowledge as established/known.

Yet its raw CK2 action policy usually fails. Re-inserting only the model's own
mechanical derivation is sufficient to restore the intended CK2/CK3 distinction;
re-inserting only the epistemic fact is not.

A careful claim is:

> In this controlled Hanabi diagnostic, GPT-5.4's partner-knowledge-sensitive
> signaling policy is strongly dependent on whether mechanically derived hint
> consequences are made decision-salient. The model can recover those
> consequences when separately elicited, and feeding back only that
> self-derived mechanical information restores the appropriate CK2 policy.

This does **not** prove that the original action call internally failed to
compute the mechanics. Shadow probes are separate stateless elicitation calls.
The result establishes an elicitable-capability versus action-policy gap and a
causal rescue by mechanical feedback.

## 6. Next replication target

The next high-value replication should change the *mechanical route*, not merely
the wording or model.

Design a second CK2 -> CK3 sender-reliance microstate where the robust route is
made safe by **direct positive information**, rather than the current rank-1
negative-information chain. Keep the same abstract choice:

```text
CK2 -> robust signal
CK3 -> convention-dependent signal
```

but vary rank/color values, touched-card pattern, stack state, and which hint
supplies the robust guarantee.

This tests whether the current scaffold/intervention effect is specific to
negative-information reasoning or generalizes to a mechanically distinct
reliance problem.

## 7. Reproducibility notes

Key configs:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_minimal_pair.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw_minimal_pair.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_combined_probe.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_self_derived_intervention.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_factorial_intervention.yaml
```

For the factorial experiment, intervention-arm execution order is
deterministically shuffled and logged. The fresh arm uses the exact baseline
prompt and, with API seed variation disabled, should match the baseline request
payload hash.
