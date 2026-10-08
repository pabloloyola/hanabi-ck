---
marp: true
theme: default
size: 16:9
title: Section 10 — Mechanical scaffold ablation
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 10. Mechanical scaffold ablation

## Derived versus raw

We separate mechanical support from the CK treatment.

~~~text
derived:
  provide deterministic safety summaries
  and sender hint consequences

raw:
  provide the visible Hanabi state
  but withhold synthetic safety summaries
  and precomputed sender hint effects
~~~

The CK2/CK3 manipulation stays the same.

---

# The critical 2 × 2 result

| Wording | Scaffold | CK2 convention | CK3 convention | Desired switches |
|---|---|---:|---:|---:|
| canonical | derived | 20% | 100% | 16/20 |
| canonical | raw | 90% | 100% | 2/20 |
| minimal pair | derived | 5% | 100% | 19/20 |
| minimal pair | raw | 85% | 100% | 3/20 |

The effect is not scaffold-invariant.

---

# Where the change happens

CK3 is almost unchanged:

~~~text
derived CK3: 100% convention
raw CK3:     100% convention
~~~

The large movement is CK2:

~~~text
derived CK2: 5-20% convention
raw CK2:    85-90% convention
~~~

So raw mechanics mostly destroys the CK2 caution.

---

# This survives the wording control

Minimal-pair wording gives:

~~~text
derived:
CK2  1/20 convention
CK3 20/20 convention

raw:
CK2 17/20 convention
CK3 20/20 convention
~~~

The scaffold effect is therefore not explained by canonical CK wording.

---

# What raw does not mean

Raw does **not** remove legal Hanabi information.

The model still receives:

- visible partner cards
- stacks and public state
- hint-derived card constraints
- indexed legal actions

Raw removes hanabi-ck's **derived safety computations**.

---

# Two competing explanations

The raw CK2 failure could mean:

~~~text
A. mechanics bottleneck
   model cannot derive what the robust hint guarantees

B. policy integration bottleneck
   model can derive the mechanics
   but does not make them control the action
~~~

Behavior alone cannot distinguish these.

---

# Section 10 takeaway

> **GPT-5.4's apparent CK sensitivity depends strongly on mechanical
> scaffolding, primarily through CK2 behavior.**

The next step is to probe mechanical and epistemic capabilities independently,
after the action has already been sampled.

---
