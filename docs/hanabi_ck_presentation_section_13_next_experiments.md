---
marp: true
theme: default
size: 16:9
title: Section 13 — Next experiments
paginate: true
style: |
  section {
    font-size: 28px;
    padding: 44px 60px;
  }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 13. Next experiments

## What we need next

We have a strong single-scenario dissociation.

The next goal is to test whether the same pattern survives:

- different Hanabi states
- different hint attributes
- different convention phrasings
- larger sample sizes
- stronger statistical modeling
- rule validation against a reference environment

---

# Priority 1 — scenario replication

Create a second and third reliance scenario with the same abstract structure:

```text
robust hint works without convention
convention hint is better only when receiver knowledge is assured
```

But vary the surface details:

```text
rank values
colors
which cards are touched
which card is newest
stack states
```

This checks that the result is not tied to one rank-1 / rank-2 construction.

---

# Scenario replication design

For each new scenario, preserve the logic:

```text
CK2 expected action: robust route
CK3 expected action: convention route
```

Then run the same minimal-pair matrix:

```text
GPT-5.4
DeepSeek V4 Flash
Claude Sonnet 5.5
```

The key outcome is whether the cross-model pattern repeats.

---

# Priority 2 — larger-N replication

The current 20-pair runs are enough to see the effect.

For publication-quality analysis, increase to something like:

```text
50 or 100 paired repetitions
per model
per scenario
```

This gives more stable estimates of:

- convention hint rate
- predicted switch rate
- invalid-call rate
- scenario-by-model variability

---

# Priority 3 — model × condition analysis

Move from descriptive tables to an explicit model.

Example outcome:

```text
sender chose convention hint: yes/no
```

Predictors:

```text
model
condition: CK2 vs CK3
scenario
model × condition interaction
```

The important term is the interaction:

```text
does CK3 increase convention reliance differently by model?
```

---

# Priority 4 — HLE parity tests

Keep the custom harness for epistemic microstates.

But validate standard Hanabi mechanics against the DeepMind Hanabi Learning Environment where possible.

Check things like:

```text
legal moves
hint effects
stack updates
discard effects
token updates
terminal scoring
```

This makes the custom engine easier to defend.

---

# Priority 5 — convention wording ablations

Test whether the pattern depends on the exact convention phrase.

Variants:

```text
"newest touched card"
"rightmost touched card"
"most recently drawn card"
"the newest matching card is intended"
```

The goal is not to find the best prompt.

The goal is to see whether partner-knowledge sensitivity generalizes across equivalent conventions.

---

# Priority 6 — remove helpful annotations

Currently we often provide mechanical annotations such as:

```text
rank-1 → provably playable: [4]
rank-2 → provably playable: [1,2,4]
```

This isolates epistemic policy from deduction skill.

A later harder condition should remove or reduce these annotations.

Then we can ask whether the model can compute both mechanics and epistemic policy itself.

---

# Priority 7 — full chain runs

Sender-only runs isolate sender policy.

Full sender → receiver runs test end-to-end coordination:

```text
P0 chooses hint
        ↓
P1 receives updated observation
        ↓
P1 chooses play
        ↓
coordination success or failure
```

This is noisier but closer to actual gameplay.

---

# Priority 8 — trace coding

Manually or automatically label traces for reasoning features:

```text
mentions receiver uncertainty
mentions robust route
mentions convention route
states whether receiver has convention
matches final action
```

Then compare:

```text
trace recognition vs behavior
```

This separates verbal recognition from policy control.

---

# Priority 9 — additional models

Add models only after the design is stable.

Useful model categories:

- strong OpenAI model
- strong Anthropic model through a reliable route
- DeepSeek reasoning/non-reasoning variants
- local Qwen variants
- smaller open models

The goal is a taxonomy of epistemic-policy behavior, not a leaderboard.

---

# Near-term execution plan

A practical order:

```text
1. implement scenario replication A
2. run GPT / DeepSeek / Sonnet minimal-pair matrix
3. add HLE parity tests
4. scale to larger N on the best scenarios
5. run model × condition analysis
6. write the method/results draft
```

This turns the current pilot into a defensible study.

---

# Section 13 takeaway

> **The next step is not more random model testing; it is scenario replication plus formal analysis.**

We already have a strong seed result.

Now we need to show it is stable, not an artifact of one scenario or one prompt surface.

---
