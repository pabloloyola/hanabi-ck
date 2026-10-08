---
marp: true
theme: default
size: 16:9
title: Section 14 — Takeaways
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 14. Takeaways

## The project in one sentence

> Hanabi-CK tests whether LLM cooperative actions change when only the team's
> epistemic state changes, while separately controlling the mechanical support
> available to the policy.

---

# Takeaway 1 — CK2 → CK3 is still the key contrast

~~~text
CK2:
receiver actually has the convention,
but sender is not assured of that fact

CK3:
sender is explicitly assured
receiver has the convention
~~~

The physical Hanabi state stays fixed.

---

# Takeaway 2 — the original GPT result was scaffold-dependent

Under minimal-pair wording:

~~~text
derived:
CK2 convention  1/20
CK3 convention 20/20

raw:
CK2 convention 17/20
CK3 convention 20/20
~~~

The strong behavioral CK switch was not invariant to mechanical presentation.

---

# Takeaway 3 — the capabilities are elicitable

In the raw combined-probe run:

~~~text
CK2 mechanical exact 20/20
CK2 epistemic exact  20/20
CK2 direct action      3/20 correct
~~~

Seventeen CK2 trials had both probes correct while the action was wrong.

---

# Takeaway 4 — mechanical feedback causally rescues behavior

Factorial CK2 intervention:

~~~text
fresh        6/20 correct
mechanical  20/20 correct
epistemic    2/20 correct
both        20/20 correct
~~~

Mechanical-only and both-facts interventions are behaviorally identical here.

---

# Takeaway 5 — the bottleneck is more specific than "epistemics"

GPT-5.4 correctly reports:

~~~text
CK2 receiver knowledge = unknown
CK3 receiver knowledge = known
~~~

But explicitly feeding back that epistemic fact alone does not repair CK2.

Making the **mechanical consequences decision-salient** does.

---

# Takeaway 6 — CK3 is a specificity control

Across the factorial intervention:

~~~text
CK3 fresh       20/20 correct
CK3 mechanical  20/20 correct
CK3 epistemic   20/20 correct
CK3 both        20/20 correct
~~~

The intervention is not simply biasing toward the robust hint.

---

# Takeaway 7 — interpret carefully

Do say:

> elicitable capability versus action-policy gap

Do say:

> mechanical consequence salience strongly controls CK-sensitive signaling

Do not say:

> formal common knowledge has been demonstrated inside the model

---

# The current causal story

~~~text
derived mechanics
    -> strong CK2/CK3 policy distinction

raw mechanics
    -> distinction mostly collapses

raw + probes
    -> model can recover both constituent facts

raw + self-derived mechanical feedback
    -> appropriate distinction returns
~~~

This is now the central result.

---

# What remains

The next target is a mechanically distinct positive-information scenario.

If that replicates the same pattern, then expand across models and longer
coordination chains.

---

# Final takeaway

> **The interesting failure is not that GPT-5.4 lacks the relevant facts. It is
> that its raw cooperative policy often fails to make mechanically derivable
> consequences govern when a convention is safe to rely on.**

Hanabi-CK gives us a controlled way to measure—and intervene on—that gap.

---
