---
marp: true
theme: default
size: 16:9
title: Section 8 — The key CK2 → CK3 reliance scenario
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

# 8. The key CK2 → CK3 reliance scenario

## The controlled decision

We now build one specific Hanabi situation where the sender must choose between:

```text
robust hint
  reliable without the convention

convention hint
  better only if the receiver knows the convention
```

The physical state stays fixed.

Only the sender's assurance about the receiver changes.

---

# Sender goal

Player 0 must get Player 1 to play their newest card on the immediately following turn.

The harness states the goal as:

```text
Get Player 1 to play their newest card
using exactly one legal Hanabi hint.

Reliability is primary.
If multiple hints are equally reliable,
prefer the one that makes more cards useful later.
```

So the sender is not merely maximizing information.

It must communicate the intended next action reliably.

---

# Receiver hand

The receiver's true hand is:

```text
index:      0   1   2   3   4
truth:      W1  R2  G2  B1  Y2
order:      oldest              newest
```

The target is:

```text
card 4 = Y2
```

The stacks are already at rank 1 for every color.

So a rank-2 card is playable.

---

# Receiver's prior knowledge

Before the sender acts, Player 1 already knows something about the newest card:

```text
card 4:
  color = Y
  rank ∈ {1, 2}
```

But Player 1 does **not** yet know whether it is:

```text
Y1  or  Y2
```

Since the Y stack is already at 1:

```text
Y1 = obsolete / unsafe to play
Y2 = playable
```

So the newest card is not yet provably playable.

---

# Sender's two important choices

The scenario creates two meaningful rank hints.

```text
rank-1 hint
  robust route

rank-2 hint
  convention-dependent route
```

Both are legal Hanabi hints.

Both use the same receiver hand and same stacks.

The difference is how much the receiver can infer from the hint without relying on the convention.

---

# Robust route: rank-1 hint

A rank-1 hint touches cards 0 and 3.

```text
index:      0   1   2   3   4
truth:      W1  R2  G2  B1  Y2
rank-1:     ✓   .   .   ✓   .
```

The newest card is **not** touched.

That negative information matters.

---

# Why rank-1 is robust

Player 1 already knows:

```text
card 4: Y{1,2}
```

After rank-1 does not touch card 4:

```text
card 4 is not rank 1
        ↓
card 4 = Y2
```

Now card 4 is uniquely provably playable.

So rank-1 communicates the target even if Player 1 does not know the special convention.

---

# Convention route: rank-2 hint

A rank-2 hint touches cards 1, 2, and 4.

```text
index:      0   1   2   3   4
truth:      W1  R2  G2  B1  Y2
rank-2:     .   ✓   ✓   .   ✓
```

After this hint, all three touched cards are provably playable.

```text
playable candidates: [1, 2, 4]
```

Without the convention, the intended one is ambiguous.

---

# Why rank-2 needs the convention

The convention says:

> If a rank hint touches the receiver's newest card, interpret the newest card as intended to be played once safe.

So under the convention:

```text
rank-2 touches newest card 4
        ↓
card 4 is intended
```

But without the convention, Player 1 sees three playable cards.

The hint is informative, but not self-disambiguating.

---

# The designed tension

| Hint | Immediate reliability | Extra value |
|---|---|---|
| rank-1 | Works without convention | only card 4 becomes playable |
| rank-2 | Requires receiver to know convention | cards 1, 2, 4 become playable |

So the ranking depends on partner knowledge:

```text
receiver knowledge uncertain → rank-1
receiver known to have convention → rank-2
```

This is exactly the epistemic reliance test.

---

# CK2 version

In CK2, both players actually receive the convention.

But the sender is not assured that the receiver has it.

From the sender's justified perspective:

```text
I have C.
The receiver may or may not have C.
```

Because reliability is primary, the predicted action is:

```text
choose rank-1
```

---

# CK3 version

In CK3, both players receive the convention.

And the sender is explicitly told the receiver has it.

From the sender's justified perspective:

```text
I have C.
I know the receiver has C.
```

Now the convention-dependent hint is safe to exploit.

The predicted action is:

```text
choose rank-2
```

---

# The predicted switch

The key behavioral event is:

```text
CK2: rank-1 robust hint
CK3: rank-2 convention hint
```

This is not just choosing the convention sometimes.

It is choosing the convention **only when the sender is justified in relying on receiver knowledge**.

That is the signature we want to detect.

---

# What different patterns mean

```text
rank-1 → rank-2
```

Strong evidence of partner-knowledge-sensitive policy.

```text
rank-2 → rank-2
```

The model uses the convention even when receiver knowledge is uncertain.

```text
rank-1 → rank-1
```

The model avoids convention reliance even when it is justified.

---

# Why this scenario is clean

Between CK2 and CK3, the following are held constant:

```text
receiver hand
sender hand
stacks
legal hints
sender goal
convention text
receiver actually having the convention
```

The main changed variable is:

```text
Is the sender assured that receiver has the convention?
```

This makes the result interpretable.

---

# Section 8 takeaway

> **The reliance scenario turns common-knowledge reasoning into a concrete choice between rank-1 and rank-2.**

If a model changes from rank-1 in CK2 to rank-2 in CK3, it is using partner-knowledge assurance to control communication policy.

That sets up the main cross-model result.

---
