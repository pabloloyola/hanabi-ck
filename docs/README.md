# Documentation

This directory separates **how to run the project**, **what the current result
is**, and **why the architecture looks the way it does**.

## Start here

| Document | Use it for |
|---|---|
| [../README.md](../README.md) | installation, quick start, project overview |
| [gpt54_scaffold_factorial_results.md](gpt54_scaffold_factorial_results.md) | canonical record of the current GPT-5.4 result |
| [experiments.md](experiments.md) | experiment families, configs, and recommended run order |
| [hanabi_source_integration.md](hanabi_source_integration.md) | native/HLE backend decision and mechanical-scaffold architecture |
| [hanabi_ck_harness_guide.tex](hanabi_ck_harness_guide.tex) | long-form illustrated technical guide |
| [hanabi_ck_presentation.md](hanabi_ck_presentation.md) | presentation entry point and Sections 1–3 |

Sections 4–14 of the presentation live in standalone files. The current evidence
sequence uses:

- `hanabi_ck_presentation_section_09_main_cross_model_result.md`
- `hanabi_ck_presentation_section_10_mechanical_scaffold_ablation.md`
- `hanabi_ck_presentation_section_11_shadow_probes.md`
- `hanabi_ck_presentation_section_12_causal_intervention.md`
- `hanabi_ck_presentation_section_13_interpretation_next_replication.md`
- `hanabi_ck_presentation_section_14_takeaways.md`

## Current evidence sequence

The main sender-reliance result should be read in this order:

1. derived-scaffold CK2 → CK3 result;
2. minimal-pair wording control;
3. raw mechanical-scaffold ablation;
4. independent mechanical and epistemic shadow probes;
5. self-derived facts intervention;
6. four-arm factorial intervention.

The canonical numbers and careful claim are maintained in
[gpt54_scaffold_factorial_results.md](gpt54_scaffold_factorial_results.md).
Avoid duplicating result tables in new docs unless they serve a presentation
purpose.

## Documentation conventions

- **README**: short operational entry point, not an experiment log.
- **Result memo**: canonical numerical record for the current headline result.
- **Experiment guide**: commands and configuration families.
- **Architecture note**: implementation decisions and validation status.
- **Presentation files**: explanatory narrative; they may repeat selected
  numbers for communication, but should defer to the result memo for the
  canonical record.
- **Generated run outputs** under `runs/` remain the source data; documentation
  summarizes them rather than replacing them.

## Naming

The CK labels are experimental treatment names:

- `ck0`
- `ck1_private`
- `ck2_shared`
- `ck3_mutual`
- `ck_inf_common`

Do not describe CK3 as proof of formal common knowledge. The main CK2 → CK3
contrast is a finite **partner-knowledge assurance** manipulation.
