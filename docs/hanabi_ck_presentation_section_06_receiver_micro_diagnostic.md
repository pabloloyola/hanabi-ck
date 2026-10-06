---
marp: true
theme: default
size: 16:9
title: Section 6 — Receiver micro-diagnostic
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

# 6. Receiver micro-diagnostic

## First isolate the receiver side

Before testing full sender → receiver coordination, we ask a simpler question:

> If the receiver is given a hint and a convention treatment, does it choose the intended card?

This is a one-agent diagnostic.

It tests whether the model can map a convention to a play decision.

---

# Why start with the receiver?

The full problem has two parts:

```text
sender chooses a signal
        ↓
receiver interprets the signal
```

If the receiver cannot interpret the signal, then a sender failure is hard to interpret.

So we first ask:

```text
given the hint and the treatment,
which card does the receiver play?
```

This helps separate convention interpretation from signal choice.

---

# The receiver task

The receiver sees its own hint-derived knowledge and the legal play options.

It has to choose a card.

A simplified version:

```text
A hint touched multiple cards.
A convention says the newest touched card is intended.
Several cards may be mechanically playable.
Which one should the receiver play?
```

The diagnostic target is whether the receiver selects the newest convention-targeted card.

---

# What the metric measures

The main metric is:

```text
newest_selection_rate
```

Meaning:

> Among valid receiver decisions, how often did the model select the newest convention-relevant card?

We also track:

```text
play_rate
safe_candidate_play_rate
epistemically_safe_play_rate
action_type_counts
play_card_index_counts
```

These tell us whether the model played, whether the play was safe, and which card it chose.

---

# Why this is not the final result

A high receiver convention rate does **not** prove common-knowledge-sensitive coordination.

It only shows:

```text
receiver can use the convention when acting locally
```

The harder question is sender-side:

```text
Should I rely on this convention,
given what I know about whether my partner knows it?
```

That requires the sender reliance diagnostic later.

---

# The CK ladder in the receiver diagnostic

We ran the receiver diagnostic across treatments such as:

```text
CK0
CK1 private
CK2 shared
CK3 mutual
CK∞ common
```

The goal was not only to see whether the model plays safely.

It was to see whether the convention treatment changes which safe card it chooses.

---

# Example aggregate pattern

In one 100-sample receiver diagnostic, the action behavior looked like:

| Condition | Newest selection rate | Probe newest rate |
|---|---:|---:|
| CK0 | 0.09 | 0.00 |
| CK1 private | 0.25 | 0.41 |
| CK2 shared | 0.20 | 0.43 |
| CK3 mutual | 0.15 | 0.33 |
| CK∞ common | 0.11 | 0.29 |

The convention increased recognition in probes more than it changed actual action selection.

---

# Recognition vs behavior gap

The receiver sometimes appears to recognize the convention in a probe, but still does not act on it.

This creates a useful distinction:

```text
can state the convention target
        ≠
chooses that target in action
```

This became one of the recurring themes of the project.

For LLM agents, verbal recognition and policy control can dissociate.

---

# Why paired comparisons help

For each non-baseline condition, we can compare against CK0 using matched samples.

Example:

```text
same underlying microstate
same candidate action structure
CK0 prompt vs CK1 / CK2 / CK3 prompt
```

The question becomes:

> Did the convention treatment increase newest-card selection relative to baseline?

This is more informative than only comparing raw rates.

---

# What the receiver diagnostic taught us

The receiver diagnostic told us three things:

1. The harness can produce valid, safe receiver decisions.
2. The convention treatment is visible to the model in probes.
3. Recognition does not automatically imply action selection.

That third point is crucial for interpreting later results.

---

# A useful methodological lesson

If a model says:

> “The convention points to the newest card.”

but then plays a different card, we should not summarize it as simply understanding the convention.

For this project, understanding must be tied to behavior:

```text
recognition → policy → action
```

The receiver diagnostic gave us an early way to measure that gap.

---

# Limitations of this diagnostic

The receiver task is intentionally simplified.

It does not fully test:

- whether the sender should rely on the convention
- whether the sender knows the receiver knows it
- whether a convention-dependent hint is justified
- whether the team coordinates over multiple turns

So it is a component test, not the full common-knowledge experiment.

---

# Section 6 takeaway

> **The receiver diagnostic checks whether a model can map a convention treatment to a card choice, but it does not yet test whether a sender should rely on that convention.**

It gave us a key warning:

```text
verbal recognition can exceed behavioral use
```

That warning motivates the next section: the sender → receiver diagnostic.

---
