---
marp: true
theme: default
size: 16:9
title: Section 10 — Minimal-pair wording control
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

# 10. Minimal-pair wording control

## Why we needed this control

After the canonical result, one obvious concern remained:

> Maybe GPT-5.4 reacted to superficial wording differences between CK2 and CK3.

So we made the CK2 and CK3 prompts as parallel as possible.

The goal was to preserve the epistemic contrast while reducing prompt-style confounds.

---

# What stayed fixed

The minimal-pair control keeps fixed:

```text
same Hanabi state
same sender goal
same legal actions
same convention
same action-order shuffling
same number of repetitions
same model/provider setup
```

Only the sentence establishing partner-knowledge assurance changes.

---

# Minimal-pair CK2 wording

The CK2 treatment says, in effect:

```text
You have this convention.
Your instructions do not establish
whether the other player has it.
```

So the sender has the convention.

But the sender is **not justified** in assuming the receiver has it.

---

# Minimal-pair CK3 wording

The CK3 treatment says, in effect:

```text
You have this convention.
Your instructions explicitly establish
that every other player has the same convention.
```

So the sender has the convention.

And the sender **is justified** in assuming the receiver has it.

---

# The contrast is now very tight

```text
CK2:
instructions do not establish whether receiver has C

CK3:
instructions explicitly establish receiver has C
```

The intended interpretation is unchanged:

```text
CK2 → prefer robust rank-1 hint
CK3 → convention rank-2 hint becomes reliable
```

---

# GPT-5.4 replicated strongly

GPT-5.4 became even more separated under the minimal-pair wording.

| GPT-5.4 run | CK2 convention | CK3 convention | Predicted switches |
|---|---:|---:|---:|
| Canonical | 4/20 = 20% | 20/20 = 100% | 16/20 |
| Minimal pair | 1/20 = 5% | 20/20 = 100% | 19/20 |

The effect did not disappear.

It got cleaner.

---

# What that means for GPT-5.4

Under the tight wording control, GPT-5.4 usually did exactly the predicted thing:

```text
CK2:
  "I have the convention,
   but I cannot rely on the receiver having it."
       → robust rank-1 hint

CK3:
  "I know the receiver has the convention."
       → convention rank-2 hint
```

This makes the wording-confound explanation much weaker.

---

# DeepSeek under the same control

DeepSeek did not show the GPT-like switch.

| DeepSeek minimal pair | Convention hint rate |
|---|---:|
| CK2 | 18/18 = 100% |
| CK3 | 18/19 = 94.7% |

Paired-valid repetitions:

```text
predicted CK2 robust → CK3 convention switches: 0/17
```

DeepSeek remained essentially flat.

---

# Note on DeepSeek valid counts

DeepSeek had a few invalid calls because the response hit the token limit before emitting the final answer.

So the valid counts are:

```text
CK2: 18 valid out of 20
CK3: 19 valid out of 20
paired-valid: 17
```

Those failures are generation failures, not behavioral observations.

They do not explain the flat pattern among valid samples.

---

# Sonnet under the same control

Sonnet also stayed essentially flat.

| Sonnet minimal pair | Convention hint rate |
|---|---:|
| CK2 | 19/20 = 95% |
| CK3 | 20/20 = 100% |

Paired result:

```text
19 pairs: convention in both CK2 and CK3
1 pair:   predicted CK2 robust → CK3 convention switch
```

Again, this is not GPT-like behavior.

---

# Fully matched minimal-pair matrix

| Model | CK2 convention | CK3 convention | Predicted switches |
|---|---:|---:|---:|
| GPT-5.4 | 1/20 = 5% | 20/20 = 100% | 19/20 |
| DeepSeek V4 Flash | 18/18 = 100% | 18/19 = 94.7% | 0/17 |
| Claude Sonnet 5.5 | 19/20 = 95% | 20/20 = 100% | 1/20 |

This is the cleanest version of the cross-model dissociation.

---

# Where the models differ

The models are mostly aligned in CK3:

```text
when receiver knowledge is assured,
all models usually use the convention hint
```

They differ sharply in CK2:

```text
when receiver knowledge is not assured,
GPT mostly avoids convention reliance
DeepSeek and Sonnet mostly keep relying on it
```

That CK2 behavior is the diagnostic difference.

---

# Why this matters

The minimal-pair control addresses a key alternative explanation.

The result is not simply:

```text
GPT responded to verbose CK wording
```

A better interpretation is:

```text
GPT responded to the epistemic difference
between unassured and assured partner knowledge
```

At least in this controlled scenario.

---

# The strongest current claim

> Under matched minimal-pair wording, GPT-5.4 robustly changes its sender policy across CK2 and CK3.

And:

> DeepSeek V4 Flash and Claude Sonnet 5.5 largely do not make that policy adjustment.

This is currently the central empirical evidence for the project.

---

# What remains to check

The minimal-pair result is strong, but still single-scenario.

Next concerns:

- Does the pattern hold in another concrete Hanabi state?
- Does it hold with different hint ranks/colors?
- Does it hold with different convention wording?
- Do model traces reveal the same reasoning gap?

The next sections address traces and interpretation.

---

# Section 10 takeaway

> **The GPT-5.4 CK2 → CK3 effect survives a tight wording control; DeepSeek and Sonnet remain mostly flat under the same control.**

This makes the cross-model dissociation much harder to explain as prompt phrasing alone.

---
