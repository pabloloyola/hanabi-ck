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

## Start with the vocabulary

Assume the audience knows the basic rules of Hanabi.

For this project, four extra ideas matter:

- **Convention** — an agreed interpretation of an action.
- **Knowledge** — what a player can infer from its information.
- **Epistemic state** — who knows what, including knowledge about other players' knowledge.
- **Policy** — how an agent maps what it knows to an action.

The experiment asks how these four pieces interact.

---

# What is a convention?

A **convention** is a shared rule for interpreting an otherwise ambiguous action.

Example:

> “If a rank hint touches my newest card, interpret the newest card as the intended play once it is safe.”

The hint still has its normal Hanabi meaning.

But the convention adds an extra **pragmatic meaning**:

```text
literal meaning: these cards have rank r
extra meaning: play the newest touched card
```

---

# What is knowledge?

By **knowledge**, we mean information that is justified by what the player can observe.

Example:

```text
After a hint, Player 1 can infer:
“my newest card must be rank 2”
```

That is different from:

```text
“my newest card happens to be rank 2”
```

The first is epistemic; the second is only a fact about the hidden state.

---

# Knowledge about knowledge

Hanabi coordination often depends on more than:

> “What do I know?”

It can depend on:

> “What do I know about what my partner knows?”

For a convention `C`, compare:

```text
I know C

vs.

I know that my partner knows C
```

Those are different informational situations.

---

# What is an epistemic state?

The **physical state** describes the game:

```text
cards, stacks, tokens, legal actions, history
```

The **epistemic state** describes the information structure:

```text
who knows what
who knows what about the other player
which assumptions about the partner are justified
```

Our key experiments keep the physical state fixed and change the epistemic state.

---

# What is a policy?

A **policy** is simply the rule used to choose an action.

```text
observation + beliefs about partner
                ↓
             action
```

For us, the important question is not only whether a model can *describe* the partner's knowledge.

It is whether that knowledge changes the model's **policy**.

---

# Robust vs convention-dependent communication

We need one more distinction.

### Robust signal

Works even if the receiver does **not** know the special convention.

### Convention-dependent signal

Is unambiguous only if the receiver **does** know how to interpret the convention.

This creates a controlled choice:

```text
uncertain partner knowledge  → prefer robust signal
known shared convention      → convention signal becomes safe to exploit
```

---

# Levels of knowledge

Let `C` mean: “the team uses this convention.”

```text
Level 1
P0 knows C
P1 knows C

Level 2
P0 knows that P1 knows C
P1 knows that P0 knows C

Level 3
they know that the other knows that they know C

...
```

Each level adds knowledge about the other player's knowledge.

---

# What is common knowledge?

Informally, `C` is **common knowledge** when the nesting continues without a finite stopping point:

```text
everyone knows C
everyone knows that everyone knows C
everyone knows that everyone knows that everyone knows C
...
```

This matters because some coordination strategies are rational only when players can rely on sufficiently deep shared expectations.

Important: our prompt conditions are **experimental approximations to these epistemic levels**, not proof of a model's internal formal representation.

---

# Same game, different rational action

Now the central idea becomes simple.

| Physical game | Sender's knowledge about receiver | Best communication strategy |
|---|---|---|
| Same cards, same stacks, same legal hints | Receiver may not know the convention | Prefer a robust signal |
| Same cards, same stacks, same legal hints | Sender knows receiver has the convention | Convention-dependent signal can be reliable |

Only the **epistemic state** changes.

Therefore the rational **policy** can change.

---

# The core research question

> **Does an LLM change its cooperative action when only what it knows about its partner's knowledge changes?**

Equivalently:

```text
same physical state
same objective
same legal actions

but

“my partner may know the convention”
                 vs.
“I know my partner knows the convention”
```

Does the model choose differently?

---

# Behavior is the evidence

A model saying

> “I know that my partner knows the convention”

is useful diagnostic evidence.

But our primary evidence is behavioral:

```text
epistemic treatment
        ↓
model of partner
        ↓
communication strategy
        ↓
chosen action
```

If the action does not change when reliability should change, verbal recognition alone is not enough.

---

# Section 1 takeaway

> **Keep the Hanabi situation fixed. Change only what the sender is justified in assuming about the receiver. Then ask whether the sender changes its action.**

That is the central idea behind Hanabi-CK.

---
# Working plan

We will build this presentation one section at a time.

For each section:

1. Draft the explanatory slides.
2. Add diagrams, tables, or trace snippets where useful.
3. Review and simplify the story.
4. Commit the updated Markdown file.

Next section to write: **2. Hanabi basics for this project**.
