---
marp: true
theme: default
size: 16:9
title: Section 9 — Cross-model result under derived mechanics
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 9. Cross-model result under derived mechanics

## The first dissociation

The original sender-reliance experiments used the **derived** mechanical
scaffold: deterministic hint consequences were supplied to the model.

Under that setup, GPT-5.4 showed a large CK2 → CK3 policy switch.

DeepSeek V4 Flash and Claude Sonnet 5.5 mostly did not.

---

# What we measured

The sender chooses between:

~~~text
rank-1 = robust route
rank-2 = convention-dependent route
~~~

The intended policy is:

~~~text
CK2 -> robust rank-1
CK3 -> convention rank-2
~~~

---

# Canonical derived-scaffold result

20 paired repetitions per model.

| Model | CK2 convention | CK3 convention | Desired switches |
|---|---:|---:|---:|
| GPT-5.4 | 4/20 = 20% | 20/20 = 100% | 16/20 |
| DeepSeek V4 Flash | 20/20 = 100% | 20/20 = 100% | 0/20 |
| Claude Sonnet 5.5 | 19/20 = 95% | 20/20 = 100% | 1/20 |

Under derived mechanics, GPT-5.4 was qualitatively different.

---

# Minimal-pair wording control

| Model | CK2 convention | CK3 convention | Desired switches |
|---|---:|---:|---:|
| GPT-5.4 | 1/20 = 5% | 20/20 = 100% | 19/20 |
| DeepSeek V4 Flash | 18/18 = 100% | 18/19 = 94.7% | 0/17 |
| Claude Sonnet 5.5 | 19/20 = 95% | 20/20 = 100% | 1/20 |

The GPT-5.4 derived-scaffold effect survives the wording control.

---

# But this is not the final story

The original interpretation was:

> GPT-5.4 conditions its signaling policy on partner-knowledge assurance.

That statement is incomplete.

It describes behavior **given derived mechanical support**.

The next experiment removes that support.

---

# Why mechanical scaffolding matters

The robust rank-1 route depends on a negative-information deduction:

~~~text
rank-1 hint does not touch newest
        ↓
newest is not rank 1
        ↓
Y{1,2} becomes exactly Y2
        ↓
newest is uniquely provably playable
~~~

So a raw action requires both mechanical consequence reasoning and
epistemic/reliability reasoning.

---

# Revised Section 9 claim

> **Under a derived mechanical scaffold, GPT-5.4 shows a strong CK2 → CK3
> sender-policy switch that DeepSeek and Sonnet largely do not.**

The phrase **under a derived mechanical scaffold** is now essential.

Section 10 asks whether the GPT result survives when the model must derive the
Hanabi consequences itself.

---
