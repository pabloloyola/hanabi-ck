# Experiment guide

This file is the operational map of the experiment configs. It is intentionally
shorter than the historical README.

## 1. Receiver-only micro diagnostic

Purpose: test whether a receiver selects the newest touched safe card under the
convention.

Run:

```bash
uv run hanabi-ck micro configs/micro_newest.yaml
```

Primary metric:

```text
newest_selection_rate
```

The receiver shadow probe measures intended-card recognition without feeding its
answer back into the action.

## 2. Sender → receiver pair diagnostic

Purpose: test end-to-end convention encoding and decoding.

Useful configs:

```text
configs/micro_pair_smoke.yaml
configs/micro_pair_pilot.yaml
configs/micro_pair_probe_pilot.yaml
configs/micro_pair_newest.yaml
```

Run with:

```bash
uv run hanabi-ck micro-pair <config>
```

## 3. CK2 → CK3 sender-reliance diagnostic

Scenario:

```text
sender_reliance_ck2_ck3
```

The sender chooses between a robust hint and a convention-dependent hint.

Expected condition-specific policy:

```text
CK2 -> robust
CK3 -> convention
```

### Derived scaffold

Canonical wording:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3.yaml
```

Minimal-pair wording:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_minimal_pair.yaml
```

### Raw scaffold

Canonical wording:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw.yaml
```

Minimal-pair wording:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_ck2_ck3_raw_minimal_pair.yaml
```

## 4. Shadow probes

Mechanical probe only:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_raw_mechanical_probe.yaml
```

Combined mechanical + epistemic probes:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_raw_combined_probe.yaml
```

Important probe rule: the baseline sender action is sampled **before** the
shadow probes. Probe outputs cannot affect that baseline action.

## 5. Self-derived intervention

Both probe outputs fed back to a fresh action call:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_raw_self_derived_intervention.yaml
```

The intervention uses the model's own structured probe answers. It does not
replace them with researcher ground truth.

## 6. Factorial intervention

Current main causal diagnostic:

```bash
uv run hanabi-ck micro-pair \
  configs/micro_sender_reliance_openrouter_gpt_5_4_raw_factorial_intervention.yaml
```

Arms:

```text
fresh       same baseline prompt again
mechanical  mechanical probe output only
epistemic   epistemic probe output only
both        both probe outputs
```

The `fresh` arm controls for a second model sample without extra information.
Arm execution order is deterministically shuffled and logged.

Canonical results are in
[gpt54_scaffold_factorial_results.md](gpt54_scaffold_factorial_results.md).

## 7. Smoke-test policy

Before scaling a new remote experiment:

1. run the relevant smoke config;
2. inspect valid/error counts;
3. verify request-hash expectations;
4. only then run the full repetition count.

Useful smoke configs include:

```text
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_smoke.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_mechanical_probe_smoke.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_combined_probe_smoke.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_self_derived_intervention_smoke.yaml
configs/micro_sender_reliance_openrouter_gpt_5_4_raw_factorial_intervention_smoke.yaml
```

## 8. Reproducibility controls

For the reliance experiments, preserve unless deliberately ablating:

```yaml
vary_api_seed: false
shuffle_legal_actions: true
sender_action_order_seed: 20262001
condition_order_seed: 20262003
```

Intervention experiments additionally pin:

```yaml
sender_probe_seed_offset: 2000000
sender_mechanical_probe_seed_offset: 3000000
sender_intervention_seed_offset: 4000000
sender_intervention_order_seed: 4500000
```

Request payload hashes are logged to verify identity where identity is expected.

## 9. Backends

`native` remains the default and supports controlled injected microstates.

`hle` is an optional reference backend for standard full-game trajectories and
mechanics parity. See
[hanabi_source_integration.md](hanabi_source_integration.md).

## 10. Next experiment

Do not add another probe to the existing scenario first.

The next replication target is a mechanically distinct CK2 → CK3 reliance
microstate where the robust route is established through **direct positive
information** rather than the current negative-information chain.
