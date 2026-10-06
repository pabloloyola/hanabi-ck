---
marp: true
theme: default
size: 16:9
title: Hanabi-CK: Testing Common-Knowledge-Sensitive Coordination in LLM Agents
description: Working presentation outline for explaining the Hanabi common-knowledge testbed and current results.
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

# Hanabi-CK

Testing common-knowledge-sensitive coordination in LLM agents

_Working presentation outline_

---

# Table of contents — foundations

1. **The core question**
2. **Hanabi basics for this project**
3. **The experimental CK ladder**
4. **Harness architecture**
5. **Early failures and harness fixes**
6. **Receiver micro-diagnostic**
7. **Sender → receiver diagnostic**

---

# Table of contents — evidence

8. **The key CK2 → CK3 reliance scenario**
9. **Main cross-model result**
10. **Minimal-pair wording control**
11. **What the traces show**
12. **Careful interpretation**
13. **Next experiments**
14. **Takeaways**

---

# 1. The core question

## The question is not simply:

> Can an LLM play Hanabi well?

## The question is:

> **Does the model change its cooperative action when only the team's epistemic state changes?**

---

# Same game, different knowledge

The **physical state can be identical**:

- same cards
- same stacks
- same legal hints
- same objective

What changes is what the sender can assume about the receiver.

That alone can change which communication strategy is rational.

---

# Three different epistemic situations

Consider a convention shared by a team:

1. **I know the convention.**
2. **My partner may or may not know it.**
3. **I know that my partner knows it.**

The experiment asks whether the model treats these as meaningfully different states.

Most importantly: **does its action change?**

---

# Behavior is the target

A verbal statement such as

> “I know that my partner knows the convention.”

is useful diagnostic evidence, but it is **not the result**.

Our main chain is:

```text
epistemic treatment → partner model → strategy → action
```

We care most about the final behavioral consequence.

---

# Why ordinary task success is not enough

| Partner knowledge | Reliable sender policy |
|---|---|
| Uncertain | Use a robust signal that works without the convention |
| Known to share convention | Exploit the convention when useful |

Both policies can occur in the **same board state**.

So score alone cannot tell us whether the model used the right epistemic reasoning.

---

# Why Hanabi?

Hanabi gives us four useful ingredients:

- **Cooperation:** both players have the same objective.
- **Partial observability:** you cannot see your own cards.
- **Restricted communication:** only legal game actions and hints.
- **Pragmatics:** the same hint can carry extra meaning through a convention.

This makes it a compact laboratory for coordination under hidden information.

---

# Shared information ≠ mutual knowledge

Suppose both players privately receive the same convention.

Then:

```text
P0 knows C
P1 knows C
```

But P0 may still be unable to conclude:

```text
P1 knows C
```

That missing assurance can matter when choosing a signal.

---

# Mutual knowledge ≠ common knowledge

Even if:

```text
P0 knows that P1 knows C
P1 knows that P0 knows C
```

there are still deeper levels:

```text
P0 knows that P1 knows that P0 knows C
...
```

This is why we use an **epistemic ladder** rather than treating “both were told” as common knowledge.

---

# The transition we currently care about most

```text
CK2
Both players receive the convention.
Sender is NOT assured that receiver has it.

            ↓

CK3
Both players receive the convention.
Sender IS explicitly assured that receiver has it.
```

**Question:** does that assurance change the sender's policy?

---

# Terminology caution

`CK2`, `CK3`, and `CK∞` are names for our **experimental treatments**.

They do not prove that an LLM internally represents formal arbitrary-depth common knowledge.

Our current strongest claim is narrower:

> We test whether **partner-knowledge assurance** changes cooperative action selection.

---

# Section 1 takeaway

> **Keep the game fixed. Change only what the sender can assume about the partner. Then observe whether the sender changes its action.**

That is the central experimental idea.

---
# Working plan

We will build this presentation one section at a time.

For each section:

1. Draft the explanatory slides.
2. Add diagrams, tables, or trace snippets where useful.
3. Review and simplify the story.
4. Commit the updated Markdown file.

Next section to write: **2. Hanabi basics for this project**.
