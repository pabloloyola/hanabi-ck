---
marp: true
theme: default
size: 16:9
title: Section 14 — Takeaways
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

# 14. Takeaways

## The project in one sentence

> Hanabi-CK tests whether LLM agents change cooperative actions when only the team's epistemic state changes.

The physical game can stay fixed.

The key manipulation is what the sender can assume about the receiver's knowledge.

---

# Takeaway 1 — Hanabi is useful here

Hanabi gives us:

```text
partial observability
restricted communication
cooperative goals
conventions with pragmatic meaning
```

That makes it a compact testbed for studying coordination under nested knowledge.

We are not just asking whether models can play Hanabi.

We are asking whether they choose signals appropriately under partner uncertainty.

---

# Takeaway 2 — the CK ladder separates concepts

The ladder separates:

```text
having the convention
        from
knowing the partner has the convention
        from
public/common declaration of the convention
```

This distinction is the core experimental lever.

It lets us keep the game fixed while changing the epistemic treatment.

---

# Takeaway 3 — the key diagnostic is sender reliance

The central question is not simply:

```text
Does the model know the convention?
```

It is:

```text
Does the model know when it is justified
in relying on the receiver knowing the convention?
```

That is why CK2 → CK3 is so informative.

---

# Takeaway 4 — GPT-5.4 shows the predicted switch

Under minimal-pair wording:

```text
GPT-5.4
CK2:  1/20 convention hints
CK3: 20/20 convention hints
```

That means GPT-5.4 usually chooses the robust route when partner knowledge is uncertain, and the convention route when it is assured.

---

# Takeaway 5 — DeepSeek and Sonnet are mostly flat

Under the same minimal-pair setup:

```text
DeepSeek
CK2: 18/18 convention
CK3: 18/19 convention

Sonnet
CK2: 19/20 convention
CK3: 20/20 convention
```

They mostly rely on the convention even when receiver convention knowledge is not assured.

---

# Takeaway 6 — the difference is not convention recognition

All three models can use the convention when it is safe to use.

The difference is CK2:

```text
Can the sender suppress convention reliance
when receiver knowledge is uncertain?
```

GPT-5.4 mostly does.

DeepSeek and Sonnet mostly do not.

---

# Takeaway 7 — traces support the behavioral story

The traces suggest:

```text
GPT-5.4:
  partner uncertainty controls policy

Sonnet:
  uncertainty sometimes recognized,
  but weakly controls policy

DeepSeek:
  mechanics often handled,
  CK treatment mostly fails to change policy
```

The traces are diagnostic support, not the main metric.

---

# Takeaway 8 — interpret carefully

Do say:

> partner-knowledge-sensitive policy selection

Do not overclaim:

> formal common knowledge has been proven inside the model

The result is strongest as a controlled behavioral dissociation.

That is already scientifically interesting.

---

# What to tell another person

A compact explanation:

> We built a Hanabi micro-scenario where the same hint is reliable only if the receiver is known to share a convention. GPT-5.4 changes its hint depending on whether that partner knowledge is assured. DeepSeek and Sonnet mostly keep using the convention hint even when the sender is not entitled to assume the receiver knows it.

---

# What remains to do

Before turning this into a polished paper-quality result:

```text
replicate across more scenarios
increase repetitions
add HLE-style rule validation
formalize model × condition analysis
systematically code traces
```

The current result is a strong pilot.

The next step is robustness.

---

# Final takeaway

> **The interesting capability is not knowing a convention. It is knowing when a convention is safe to rely on.**

Hanabi-CK gives us a controlled way to measure that distinction in LLM agents.

---
