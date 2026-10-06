---
marp: true
theme: default
size: 16:9
title: Section 9 — Main cross-model result
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

# 9. Main cross-model result

## The first headline

In the CK2 → CK3 sender-reliance scenario, models did **not** behave the same way.

GPT-5.4 showed a large CK-sensitive policy switch.

DeepSeek V4 Flash and Claude Sonnet 5.5 mostly did not.

```text
GPT-5.4:   uncertainty about receiver knowledge changes the hint
Others:    usually use the convention hint even under uncertainty
```

---

# What we measured

For each model and condition, we measured whether the sender chose the convention-dependent hint.

```text
rank-1 hint = robust route
rank-2 hint = convention-dependent route
```

So the key rate is:

```text
sender_convention_hint_rate
```

Higher means the sender relied on the convention.

---

# Canonical wording result

20 paired repetitions per model.

| Model | CK2 convention hint | CK3 convention hint | Predicted switches |
|---|---:|---:|---:|
| GPT-5.4 | 4/20 = 20% | 20/20 = 100% | 16/20 |
| DeepSeek V4 Flash | 20/20 = 100% | 20/20 = 100% | 0/20 |
| Claude Sonnet 5.5 | 19/20 = 95% | 20/20 = 100% | 1/20 |

The GPT-5.4 pattern is qualitatively different.

---

# Reading the table

The desired CK-sensitive behavior is:

```text
CK2: receiver knowledge uncertain
     → robust rank-1 hint

CK3: receiver knowledge assured
     → convention rank-2 hint
```

So the important event is a paired switch:

```text
CK2 robust  →  CK3 convention
```

GPT-5.4 switched this way in 16 of 20 canonical pairs.

---

# What GPT-5.4 did

GPT-5.4 mostly treated CK2 and CK3 differently.

```text
CK2:
  often chooses rank-1
  avoids relying on unassured convention knowledge

CK3:
  consistently chooses rank-2
  exploits the convention when receiver knowledge is assured
```

This is the behavior the scenario was designed to detect.

---

# What DeepSeek did

DeepSeek chose the convention-dependent hint in both conditions.

```text
CK2: rank-2 convention hint
CK3: rank-2 convention hint
```

This means it used the convention even when the sender was not assured that the receiver had the convention.

So DeepSeek did not show the intended CK2 → CK3 policy adjustment.

---

# What Sonnet did

Sonnet looked very similar to DeepSeek in the canonical run.

```text
CK2: 19/20 convention hint
CK3: 20/20 convention hint
```

It did produce one CK2 robust choice.

But the dominant pattern was still flat convention reliance across both conditions.

---

# Main visual intuition

```text
Convention-hint rate

CK2       CK3

GPT-5.4       20%  ─────────────▶ 100%
DeepSeek     100%  ─────────────▶ 100%
Sonnet        95%  ─────────────▶ 100%
```

Only GPT-5.4 shows the large jump we predicted.

---

# Why this is not just convention knowledge

All three models can use the convention under CK3.

That is not the differentiator.

The differentiator is CK2:

```text
When receiver convention knowledge is not assured,
does the sender suppress convention-dependent behavior?
```

GPT-5.4 mostly does.

DeepSeek and Sonnet mostly do not.

---

# The result in one sentence

> GPT-5.4 conditions its signaling policy on partner-knowledge assurance; DeepSeek V4 Flash and Claude Sonnet 5.5 mostly choose the convention-dependent signal regardless of that assurance.

That is the central empirical result so far.

---

# Statistical status

The raw separation is large.

For the canonical run, the predicted switch counts were:

```text
GPT-5.4:   16 / 20
DeepSeek:   0 / 20
Sonnet:     1 / 20
```

This is much larger than ordinary sampling noise in this small controlled setting.

But we should still be careful: these are repeated model calls, not independent human subjects.

---

# What claim this supports

A careful claim:

> In this controlled Hanabi signaling scenario, GPT-5.4 shows strong behavioral sensitivity to whether convention knowledge is merely available to the sender or explicitly known to be shared with the receiver.

And the contrast:

> DeepSeek V4 Flash and Claude Sonnet 5.5 largely fail to make that policy adjustment in the same scenario.

---

# What claim this does not yet prove

We should **not** say:

```text
GPT-5.4 has formal common knowledge.
```

We should also not say:

```text
DeepSeek and Sonnet cannot reason about partner knowledge at all.
```

The more precise statement is about **behavioral policy sensitivity** in a controlled CK2 → CK3 manipulation.

---

# Why we needed the next control

A possible objection:

> Maybe the CK2 and CK3 prompts were worded differently enough that GPT-5.4 reacted to wording rather than epistemic structure.

So the next step was a minimal-pair wording control.

That control keeps the contrast very tight:

```text
CK2: instructions do not establish whether receiver has C
CK3: instructions explicitly establish receiver has C
```

Section 10 covers that result.

---

# Section 9 takeaway

> **The main result is a cross-model dissociation: GPT-5.4 changes policy across CK2 and CK3, while DeepSeek and Sonnet mostly do not.**

This makes the question concrete enough to test with wording controls, trace analysis, and scenario replications.

---
