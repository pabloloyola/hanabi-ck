---
marp: true
theme: default
size: 16:9
title: Section 12 — Causal intervention and localization
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 20px; }
  pre, code { font-size: 19px; }
  blockquote { font-size: 26px; }
---

# 12. Causal intervention and localization

## Feed the model its own facts

After the baseline action and shadow probes, make a fresh action call.

The intervention receives:

~~~text
original raw prompt
+
the model's own structured probe outputs
~~~

Researcher ground truth is never substituted for a probe answer.

---

# First intervention result

CK2:

| Stage | Convention hint | Correct policy |
|---|---:|---:|
| raw baseline | 16/19 = 84.2% | 3/19 = 15.8% |
| both self-derived facts | 1/18 = 5.6% | 17/18 = 94.4% |

Among baseline failures, 14/15 were rescued.

Among failures where both probes were correct, 14/14 were rescued.

CK3 stayed at ceiling.

---

# But what caused the rescue?

The both-facts intervention confounds:

~~~text
mechanical feedback
+
epistemic feedback
+
a fresh decision call
~~~

So we need a factorial control.

---

# Four intervention arms

~~~text
fresh
  original raw prompt again

mechanical
  raw prompt + mechanical-probe output

epistemic
  raw prompt + epistemic-probe output

both
  raw prompt + both probe outputs
~~~

Arm execution order is deterministically shuffled and logged.

---

# Factorial CK2 result

In this run, the baseline CK2 action was wrong 20/20 times.

| Arm | Convention hint | Correct policy |
|---|---:|---:|
| fresh | 14/20 = 70% | 6/20 = 30% |
| mechanical | 0/20 = 0% | 20/20 = 100% |
| epistemic | 18/20 = 90% | 2/20 = 10% |
| both | 0/20 = 0% | 20/20 = 100% |

This sharply localizes the rescue.

---

# Fresh is a real second-attempt control

For CK2:

~~~text
fresh request hash == baseline request hash
20 / 20
~~~

So fresh is another sample from the exact same request payload.

It improves from 0% to 30%, showing nondeterministic retry can help.

But retry alone is nowhere near the mechanical intervention.

---

# Mechanical feedback is sufficient

~~~text
mechanical-only: 20/20 correct
both-facts:      20/20 correct
epistemic-only:   2/20 correct
~~~

There are zero paired disagreements between mechanical and both.

---

# Paired contrasts

CK2 exact paired discordances:

~~~text
fresh vs mechanical:
  14 favor mechanical, 0 favor fresh

mechanical vs epistemic:
  18 favor mechanical, 0 favor epistemic

mechanical vs both:
  0 discordant pairs
~~~

Two-sided exact paired probabilities are approximately 1.22e-4 and 7.63e-6
for the first two contrasts.

Treat them as descriptive diagnostics over repeated model calls.

---

# CK3 specificity control

Every CK3 intervention arm stayed at ceiling:

~~~text
fresh       20/20 correct
mechanical  20/20 correct
epistemic   20/20 correct
both        20/20 correct
~~~

Mechanical feedback is therefore not merely pushing the model toward rank 1.

---

# Current mechanistic picture

~~~text
mechanical capability      ✓
epistemic capability       ✓

raw CK2 policy             ✗

surface mechanical facts
at decision time
          ↓
CK2 policy                 ✓
~~~

The dominant bottleneck is **decision-salience of mechanical consequences**.

---

# Section 12 takeaway

> **Making GPT-5.4's own mechanical derivation explicit at decision time is
> sufficient to restore the appropriate CK2/CK3 policy distinction.**

Making the epistemic fact explicit by itself is not.

---
