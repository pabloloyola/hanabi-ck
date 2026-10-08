---
marp: true
theme: default
size: 16:9
title: Section 11 — Shadow probes and the capability-policy gap
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 11. Shadow probes and the capability-policy gap

## Probe after action, never before

The sender action is sampled first.

Then two fresh stateless calls ask separate questions:

~~~text
mechanical probe:
  what does each candidate hint mechanically imply?

epistemic probe:
  which hint invokes the convention?
  is receiver convention knowledge established?
~~~

Probe answers never feed back into the baseline action.

---

# Mechanical shadow probe

For each candidate hint, reconstruct:

~~~text
touched_indices
receiver_provably_playable_indices_after_hint
~~~

The probe receives no CK treatment and no sender goal.

Its request payload is therefore expected to be identical across CK2 and CK3.

---

# Epistemic shadow probe

The epistemic probe asks for:

~~~text
convention_hint_index
receiver_convention_knowledge:
  no_convention | unknown | known
~~~

Expected in the main contrast:

~~~text
CK2 -> unknown
CK3 -> known
~~~

---

# Combined-probe result

Matched 20-pair raw minimal experiment:

| Condition | Mechanical exact | Epistemic exact | Direct policy correct |
|---|---:|---:|---:|
| CK2 | 20/20 | 20/20 | 3/20 |
| CK3 | 20/20 | 20/20 | 20/20 |

CK2 contains the critical category:

~~~text
both probes correct + action wrong = 17/20
~~~

---

# Mechanical negative control

The mechanical-probe CK2 and CK3 requests were byte-identical:

~~~text
paired request hashes matched:
20 / 20
~~~

So the mechanical probe had no access to the epistemic manipulation.

Yet it solved the relevant mechanics perfectly.

---

# What this establishes

The model has elicitable capability for both constituent subproblems:

~~~text
derive hint consequences       ✓
classify partner knowledge     ✓

raw CK2 action policy          usually ✗
~~~

This is a capability-policy gap.

---

# What it does not establish

The probes are separate stateless calls.

So we should **not** claim that the original action call definitely computed
both facts internally and then ignored them.

The supported claim is narrower:

> The same model can produce the relevant facts under targeted elicitation, while
> its raw action policy usually does not express the appropriate CK2 behavior.

---

# Section 11 takeaway

> **The raw CK2 failure is not explained by absence of mechanical or epistemic
> capability under targeted elicitation.**

The next experiment turns the probes from measurements into interventions.

---
