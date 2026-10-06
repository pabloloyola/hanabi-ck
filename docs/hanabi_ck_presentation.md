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
# 2. Hanabi basics for this project

## We only need a small part of Hanabi

For the experiments in this presentation, focus on four mechanics:

- you see your partner's cards, but not your own
- a hint reveals a **color** or **rank**
- a legal hint applies to **all matching cards**
- hints also create useful **negative information**

The last point is especially important for our micro-experiments.

---

# What each player can see

Two-player Hanabi:

```text
Player 0                         Player 1

own hand:   ?  ?  ?  ?  ?       own hand:   ?  ?  ?  ?  ?
sees P1:    W1 R2 G2 B1 Y2       sees P0:    visible cards
```

A player can reason about the partner's cards directly.

But for its **own** cards, it must rely on hints and public information.

---

# What a hint literally means

Suppose Player 1 has five cards:

```text
index:      0   1   2   3   4
truth:      W1  R2  G2  B1  Y2
```

A rank-2 hint touches exactly:

```text
            .   ✓   ✓   .   ✓
```

So Player 1 learns:

- cards 1, 2, 4 are rank 2
- cards 0, 3 are **not** rank 2

A hint communicates both positive and negative information.

---

# Negative information can be the key

Suppose Player 1 already knows its newest card is:

```text
index 4: color = Y
         rank ∈ {1, 2}
```

Now Player 0 gives a **rank-1 hint** that touches cards 0 and 3.

Because index 4 was **not** touched:

```text
index 4 is not rank 1
rank ∈ {1,2}
        ↓
rank = 2
```

So the receiver can infer that its newest card is exactly `Y2`.

---

# Truth is not the same as knowledge

This distinction is central to our evaluation.

| Question | Example |
|---|---|
| Is the hidden card actually playable? | The card happens to be `Y2` and the Y stack is at 1 |
| Does the player know it is playable? | Its hint-derived knowledge rules out every unsafe possibility |

A physically correct play can still be **epistemically unjustified**.

We therefore do not measure only whether a card happened to succeed.

---

# What does “provably playable” mean?

A card is **provably playable** when every card identity still consistent with the player's information is currently playable.

Example:

```text
knowledge: Y{1,2}
Y stack:   1
```

This is **not** provably playable:

- `Y1` would already be obsolete
- `Y2` would be playable

After ruling out rank 1:

```text
knowledge: Y2
```

the card becomes provably playable.

---

# Why we expose these deductions to the model

Our micro-diagnostics are trying to test:

> Does the model use the team's epistemic state correctly?

Not:

> Can the model perfectly simulate every Hanabi deduction in its head?

So the harness can provide mechanical annotations such as:

```text
hint rank 1 → provably playable: [4]
hint rank 2 → provably playable: [1, 2, 4]
```

These annotations are computed from public/hint-derived information, not hidden cards.

---

# Card order matters for our convention

In the harness, hands are always ordered:

```text
oldest → newest
0   1   2   3   4
                ↑
             newest
```

So in a five-card hand, `card_index = 4` is the newest card.

Our convention can therefore refer to **the newest card** without relying on an ambiguous implementation detail.

---

# The one-turn communication problem

The core micro-experiment can be viewed as:

```text
Player 0 sees Player 1's hand
             ↓
chooses exactly one legal hint
             ↓
hint changes Player 1's knowledge
             ↓
Player 1 interprets the hint
             ↓
Player 1 chooses a play
```

Later we will freeze this setup and manipulate only what the players know about the convention.

---

# Section 2 takeaway

> **Hanabi lets us separate the true card from what the receiver can actually infer about that card.**

That separation gives us the controlled setting we need for studying conventions, partner knowledge, and reliable communication.

---
# 3. The experimental CK ladder

## Turning epistemic ideas into controlled treatments

We vary **who has the convention** and **what each player is told about the other's knowledge**.

Let `C` denote the convention.

Across conditions, the Hanabi state stays fixed.

What changes is the information delivered to the agents.

---

# CK0 — no convention

Neither player is given `C`.

```text
P0: no convention
P1: no convention
```

This is the baseline.

If a hint is ambiguous under ordinary Hanabi information, the agents cannot rely on our experimental convention to resolve it.

---

# CK1 — private convention

One designated player receives `C`.

In our sender-focused experiments, that is usually Player 0.

```text
P0 receives C
P1 does not receive C
```

Crucially, P0's instruction does **not** tell it whether P1 also received the convention.

So from P0's point of view:

> “I know C, but I cannot rely on P1 knowing C.”

---

# CK2 — both privately receive the convention

Now both players actually receive `C`.

```text
P0 receives C
P1 receives C
```

But the instructions are private.

P0 is **not told** that P1 received it, and vice versa.

So the experimenter knows both have `C`, while each player lacks assurance about the other.

---

# CK1 vs CK2: a subtle but important difference

From the **experimenter's** perspective:

| Condition | Does P1 actually have `C`? |
|---|---:|
| CK1 | No |
| CK2 | Yes |

But from the **informed sender's local instruction**, both can look the same:

```text
"I have C."
"My instructions do not establish whether P1 has C."
```

This lets us separate **actual partner knowledge** from **knowledge about partner knowledge**.

---

# CK3 — explicit assurance of shared convention

Both players receive `C`, and each is explicitly told that the other received the same convention.

```text
P0 knows C
P1 knows C
P0 knows P1 has C
P1 knows P0 has C
```

Now the sender is justified in relying on the receiver's convention knowledge.

This CK2 → CK3 transition is the central manipulation in our current result.

---

# CK∞ — public/common declaration

The convention is presented as public/common knowledge.

Intuitively:

```text
everyone has C
everyone knows everyone has C
everyone knows that everyone knows everyone has C
...
```

This treatment is intended to approximate an arbitrary-depth common-knowledge declaration.

It is stronger than the finite assurance used in CK3.

---

# The ladder at a glance

| Condition | Sender has `C` | Receiver actually has `C` | Sender assured receiver has `C` |
|---|:---:|:---:|:---:|
| CK0 | No | No | No |
| CK1 | Yes | No | **No / unknown** |
| CK2 | Yes | Yes | **No / unknown** |
| CK3 | Yes | Yes | **Yes** |
| CK∞ | Yes | Yes | **Public/common declaration** |

The final column is especially important for our reliance experiment.

---

# Why CK2 → CK3 is so useful

Between CK2 and CK3:

```text
same convention
same physical Hanabi state
same legal actions
same sender objective
same receiver actually having the convention
```

The key change is only:

```text
CK2: sender cannot assume receiver knows C
CK3: sender is explicitly assured receiver knows C
```

This gives us a clean test of **partner-knowledge assurance**.

---

# The treatment labels are experimental names

`CK0`, `CK1`, `CK2`, `CK3`, and `CK∞` are convenient labels for our prompt treatments.

They should not be read as a theorem that the model internally represents exactly that formal epistemic depth.

For example:

- CK3 gives explicit finite mutual assurance.
- CK∞ uses a public/common-knowledge declaration.

Our evidence comes from how behavior changes across these treatments.

---

# Section 3 takeaway

> **The ladder separates having a convention from knowing that your partner has the convention.**

For the main experiment, CK2 and CK3 are especially valuable because the receiver has the convention in both conditions.

The difference is whether the sender is justified in relying on that fact.

---
# Working plan

We will build this presentation one section at a time.

For each section:

1. Draft the explanatory slides.
2. Add diagrams, tables, or trace snippets where useful.
3. Review and simplify the story.
4. Commit the updated Markdown file.

Next section to write: **4. Harness architecture**.
