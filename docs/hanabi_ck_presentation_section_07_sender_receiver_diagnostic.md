---
marp: true
theme: default
size: 16:9
title: Section 7 — Sender → receiver diagnostic
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

# 7. Sender → receiver diagnostic

## Moving from recognition to coordination

The receiver micro-diagnostic asked:

> If the receiver sees a convention-relevant hint, does it interpret the hint as intended?

The sender → receiver diagnostic asks a stronger question:

> Does the sender choose a hint that will make the receiver coordinate safely?

This is closer to the real common-knowledge problem.

---

# Why sender behavior is harder

A receiver only has to interpret an observed signal.

A sender has to choose a signal while reasoning about the receiver.

```text
What do I want the receiver to do?
              ↓
What will the receiver infer from each legal hint?
              ↓
Does the receiver know the convention?
              ↓
Which hint is reliable?
```

That last step is where partner-knowledge assurance matters.

---

# The diagnostic structure

We construct a controlled one-turn situation:

```text
Player 0 = sender
Player 1 = receiver

Player 0 sees Player 1's hand
Player 0 must choose one legal hint
Player 1 will later choose a play
```

The hidden card situation is fixed.

The CK treatment changes what Player 0 can assume about Player 1.

---

# Two possible sender strategies

The scenario is designed to contain two meaningful routes.

```text
robust route
  works from ordinary Hanabi knowledge alone

convention route
  works cleanly only if the receiver knows the convention
```

So the sender's choice reveals whether it is relying on the convention being shared.

---

# Robust route

The robust hint is chosen so that, after the hint, the receiver can infer the intended play without needing the special convention.

Example pattern:

```text
rank-1 hint
        ↓
receiver uses negative information
        ↓
newest card becomes uniquely provably playable
```

This is safe even if the receiver does not know the convention.

---

# Convention route

The convention hint is chosen so that it touches the receiver's newest card.

Under the convention:

```text
rank hint touches newest card
        ↓
newest touched card is intended
        ↓
play it once safe
```

But without the convention, the same hint may leave multiple plausible playable cards.

So this route depends on the receiver understanding the convention.

---

# The key comparison

The same sender faces the same physical situation under two treatments:

```text
CK2
Sender has the convention,
but is not assured receiver has it.

CK3
Sender has the convention,
and is explicitly assured receiver has it.
```

The diagnostic prediction is:

```text
CK2 → choose robust hint
CK3 → choose convention hint
```

---

# What a successful switch means

A CK2 → CK3 switch means:

```text
same legal actions
same card state
same convention text
same sender goal

but

partner knowledge uncertain  → robust hint
partner knowledge assured    → convention hint
```

That is direct behavioral evidence that the model's policy is sensitive to partner-knowledge assurance.

---

# What a flat pattern means

If a model chooses the convention hint in both CK2 and CK3:

```text
CK2: convention hint
CK3: convention hint
```

then it may understand the convention, but it is not suppressing convention reliance when the partner's knowledge is uncertain.

This is the pattern we later see for DeepSeek and Sonnet.

---

# Sender-only vs full chain

There are two useful variants.

### Sender-only diagnostic

Only ask Player 0 which hint to send.

This isolates sender policy.

### Full sender → receiver chain

Ask Player 0 for a hint, then ask Player 1 for a play.

This measures end-to-end coordination.

The sender-only version is cheaper and cleaner for cross-model comparisons.

---

# Metrics for the sender diagnostic

For each condition, we count:

```text
sender_convention_hint_rate
sender_robust_hint_rate
sender_epistemic_choice_accuracy
valid / error samples
```

For paired CK2 / CK3 runs, we count:

```text
both convention
both robust
CK2 convention → CK3 robust
CK2 robust → CK3 convention
```

The last line is the predicted switch.

---

# Why pairing matters here

We compare CK2 and CK3 within the same repetition.

```text
repetition k
  same scenario
  same action order
  same model
  CK2 prompt
  CK3 prompt
```

Pairing reduces noise from action-order effects and prompt stochasticity.

It lets us ask:

> Did this same model instance switch when only the epistemic treatment changed?

---

# What this diagnostic adds beyond Section 6

Receiver micro-diagnostic:

```text
Can the receiver map a hint to the intended card?
```

Sender → receiver diagnostic:

```text
Does the sender know when it is safe to use that mapping?
```

The second question is closer to common-knowledge-sensitive coordination.

A model can pass the first and fail the second.

---

# Section 7 takeaway

> **The sender diagnostic tests whether the model uses partner-knowledge assurance to decide whether a convention-dependent signal is safe.**

This sets up the key CK2 → CK3 reliance scenario and the cross-model result.

---
