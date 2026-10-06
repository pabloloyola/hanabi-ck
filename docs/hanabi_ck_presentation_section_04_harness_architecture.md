---
marp: true
theme: default
size: 16:9
title: Section 4 — Harness architecture
paginate: true
style: |
  section {
    font-size: 28px;
    padding: 44px 60px;
  }
  h1 {
    font-size: 42px;
    margin-bottom: 0.55em;
  }
  h2 {
    font-size: 32px;
  }
  table {
    font-size: 21px;
  }
  pre, code {
    font-size: 20px;
  }
  blockquote {
    font-size: 27px;
  }
---

# 4. Harness architecture

## What the harness has to do

The harness is not just a Hanabi player.

It must let us run the same situation under different epistemic treatments and ask:

```text
same state + same legal actions + different CK treatment
                         ↓
                does the action change?
```

So the architecture needs control, repeatability, and detailed logs.

---

# High-level flow

```text
config YAML
   ↓
scenario builder
   ↓
condition prompt
   ↓
agent call
   ↓
action parser
   ↓
state transition / micro-outcome
   ↓
JSONL logs + summary metrics
```

Each piece is deliberately small so we can inspect failures.

---

# Config: the experiment recipe

A config file says:

```text
which scenario to run
which CK conditions to compare
which model/provider to call
how many repetitions
which seeds to use
where to write outputs
```

This lets us rerun the same experiment with a different model while keeping everything else fixed.

---

# Why configs matter for model comparison

Example comparison:

```text
GPT-5.4 vs DeepSeek vs Sonnet
same scenario
same CK2/CK3 wording
same action shuffles
same metric definitions
```

Only the model changes.

That is what makes the cross-model comparison interpretable.

---

# Scenario layer: controlled Hanabi microstates

A scenario specifies the local Hanabi situation:

```text
hands
stacks
known card possibilities
legal hints
diagnostic target
```

For the reliance experiment, the scenario creates two meaningful sender options:

```text
rank 1 → robust route
rank 2 → convention-dependent route
```

The goal is a controlled choice, not a full unconstrained game.

---

# Condition layer: epistemic treatment

The condition layer adds private instructions.

```text
CK2:
you have the convention,
but your instructions do not establish
whether the receiver has it

CK3:
you have the convention,
and your instructions explicitly establish
that the receiver has it
```

This is where the epistemic manipulation enters.

The underlying Hanabi state does not change.

---

# Agent interface

Every agent receives a prompt containing:

```text
private CK instruction
current observation
legal actions
mechanical annotations
required response format
```

The model must choose from the same legal-action list as every other model.

This keeps the comparison focused on action selection, not parsing differences.

---

# Why action indices?

The harness gives the model a numbered legal-action list.

Example:

```text
0: hint color Y
1: hint rank 2
2: hint rank 1
...
```

Then the model returns the selected index.

This avoids fragile natural-language action parsing and makes failures easier to diagnose.

---

# Pairing and seeds

For CK2 vs CK3, we want paired comparisons.

```text
repetition 0:
  same scenario
  same legal-action order
  CK2 prompt
  CK3 prompt

repetition 1:
  same idea, new shuffle
```

Pairing lets us ask whether the model switched action when only the epistemic treatment changed.

---

# Logs: every sample is inspectable

For each sample, the harness records:

```text
condition
repetition
private instruction
observation
legal actions
chosen action
raw model response
parsed result
diagnostic labels
errors, if any
```

This is why we can inspect both aggregate results and individual failure modes.

---

# Summary metrics

The summary aggregates behavior by condition:

```text
convention-hint rate
robust-hint rate
epistemic-choice accuracy
valid / error samples
```

And for paired runs:

```text
both convention
both robust
CK2 convention → CK3 robust
CK2 robust → CK3 convention
```

The last row is the key predicted switch in our reliance experiment.

---

# Failure handling

Invalid model behavior is not silently cleaned up.

Examples:

```text
timeout
no JSON object
invalid action index
provider error
truncated response
```

The harness logs the raw API response and marks the sample invalid or aborts, depending on the experiment policy.

---

# Why not just use full-game score?

Full-game score is useful, but too coarse for this question.

A score cannot tell us whether the model:

```text
recognized the convention
modeled the partner's knowledge
chose a robust signal under uncertainty
relied on the convention only when justified
```

So we use micro-diagnostics where one action exposes the relevant epistemic policy.

---

# Relation to Hanabi Learning Environment

DeepMind's Hanabi Learning Environment is useful as a reference for standard Hanabi mechanics.

But our harness needs extra experimental control:

```text
construct specific epistemic microstates
inject CK-specific private prompts
annotate provably playable actions
log raw LLM/provider behavior
run paired condition comparisons
```

Best long-term story: hanabi-ck for epistemic experiments, HLE-style tests for rule validation.

---

# Section 4 takeaway

> The harness is designed to isolate one question: when the physical Hanabi state is fixed, does changing the agent's epistemic treatment change the selected action?

It gives us:

```text
control
repeatability
inspectable traces
paired metrics
```

That is what makes the later model comparison meaningful.

---
