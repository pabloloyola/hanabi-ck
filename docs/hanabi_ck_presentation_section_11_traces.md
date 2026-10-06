---
marp: true
theme: default
size: 16:9
title: Section 11 — What the traces show
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

# 11. What the traces show

## Why look beyond aggregate rates?

The tables tell us **what** each model chose.

The traces help us understand **how** the model framed the choice.

They let us ask:

```text
Did the model mention partner uncertainty?
Did it notice the robust route?
Did it treat the convention as safe to rely on?
Did its reasoning match its final action?
```

---

# Trace evidence is diagnostic, not the main metric

We should be careful.

Trace text is not a perfect window into cognition.

But it is still useful when paired with behavior:

```text
behavior = primary evidence
trace    = diagnostic evidence
```

A trace can reveal whether a wrong action came from:

- missing the mechanics
- missing the partner-knowledge issue
- noticing the issue but not letting it control policy

---

# GPT-5.4 CK2 traces

In CK2, GPT-5.4 often says something like:

```text
I have the convention,
but I cannot assume Player 1 has it.
```

Then it chooses the robust rank-1 hint.

This is the desired chain:

```text
partner knowledge uncertain
        ↓
convention route unreliable
        ↓
choose robust route
```

---

# GPT-5.4 CK3 traces

In CK3, GPT-5.4 often reasons differently:

```text
Player 1 has the same convention.
A rank-2 hint touches the newest card.
The convention identifies that newest card as intended.
```

Then it chooses the convention hint.

This matches the treatment:

```text
partner knowledge assured
        ↓
convention route reliable
        ↓
choose rank-2 hint
```

---

# The important GPT pattern

GPT-5.4 does not just know the convention.

It changes when it is willing to rely on it.

```text
CK2: knowledge of convention is not enough
CK3: assurance of receiver knowledge makes it usable
```

That is exactly the distinction the experiment targets.

---

# Sonnet traces: capability without stable policy

Sonnet has at least one CK2 trace that gets the intended reasoning right:

```text
rank-2 works only if Player 1 has the convention
I cannot confirm that
rank-1 works regardless
choose rank-1
```

So Sonnet is not incapable of representing the issue.

But this reasoning appears only rarely in behavior.

---

# What Sonnet usually does

Most Sonnet CK2 samples still choose the convention hint.

That suggests a different failure mode:

```text
can sometimes articulate partner uncertainty
        ↓
but usually does not let that uncertainty govern the action
```

The issue is not simple ignorance of the rule.

It is weak or unstable integration of the epistemic fact into policy.

---

# DeepSeek traces: mechanics without the CK switch

DeepSeek also shows evidence of mechanical reasoning.

It can reason about which hint makes which cards playable.

But in the reliance task, it usually chooses:

```text
CK2: rank-2 convention hint
CK3: rank-2 convention hint
```

So the missing piece is again the policy adjustment under partner uncertainty.

---

# A useful DeepSeek counterexample

One DeepSeek sample chose the robust hint in CK3.

Mechanically, the reasoning made sense:

```text
rank-1 uniquely identifies the newest playable card
rank-2 leaves several playable options
```

But in CK3, the convention route should be acceptable because receiver knowledge is assured.

This shows the model can reason about ambiguity, but not consistently about when convention reliance is licensed.

---

# Three trace-level patterns

We can summarize the trace evidence like this:

| Pattern | Model behavior |
|---|---|
| Epistemic fact controls action | common for GPT-5.4 |
| Epistemic fact sometimes noticed but weakly controls action | Sonnet |
| Mechanics handled, CK treatment mostly ignored | DeepSeek |

This is a qualitative description, not a replacement for the metrics.

---

# The trace story in one diagram

```text
GPT-5.4
partner uncertainty → reliability judgment → action switch

Sonnet
partner uncertainty → sometimes recognized → usually no switch

DeepSeek
mechanical hint analysis → convention route preferred → usually no switch
```

The key difference is where the epistemic treatment enters the decision.

---

# Why this matters for interpretation

The traces argue against a shallow interpretation such as:

```text
GPT knows the convention; the others do not.
```

That is not right.

The stronger interpretation is:

```text
All models can use the convention.
GPT is much better at deciding when reliance on that convention is justified.
```

---

# Section 11 takeaway

> **The traces suggest the core difference is not convention recognition, but whether partner-knowledge uncertainty actually controls action selection.**

This prepares the careful interpretation in the next section.

---
