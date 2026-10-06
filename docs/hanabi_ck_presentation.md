---
marp: true
title: Hanabi-CK: Testing Common-Knowledge-Sensitive Coordination in LLM Agents
description: Working presentation outline for explaining the Hanabi common-knowledge testbed and current results.
paginate: true
---

# Hanabi-CK

Testing common-knowledge-sensitive coordination in LLM agents

_Working presentation outline_

---

# Table of contents

1. **The core question**
   - What are we trying to measure?
   - Why Hanabi is a good testbed for coordination and hidden information.
   - What we mean, and do not mean, by “common knowledge.”

2. **Hanabi basics for this project**
   - What each player can and cannot see.
   - What a hint does.
   - Why a play can be physically correct but epistemically unsafe.

3. **The experimental ladder**
   - CK0: no convention.
   - CK1: private convention.
   - CK2: everyone has the convention, but no assurance about others.
   - CK3: explicit assurance that the partner has the convention.
   - CK∞: convention declared public/common knowledge.

4. **The harness architecture**
   - Deterministic Hanabi engine.
   - Agent interface.
   - Condition prompts.
   - JSONL logs.
   - Metrics and paired comparisons.

5. **Early failures and harness fixes**
   - Agents discard forever when no play policy exists.
   - Reasoning-model output appears in `reasoning_content` instead of `content`.
   - Structured-output support differs across providers.
   - Why we log raw API responses and abort invalid games.

6. **Micro-diagnostic 1: receiver chooses newest safe card**
   - The one-step newest-card scenario.
   - What the model must infer.
   - Action/probe gap: recognizing the convention is not the same as acting on it.

7. **Micro-diagnostic 2: sender → receiver convention use**
   - Sender must choose one hint.
   - Receiver then acts.
   - What sender convention use and receiver follow-through measure.

8. **The key CK2 → CK3 reliance scenario**
   - Robust rank-1 hint: uniquely makes newest card playable.
   - Convention rank-2 hint: makes three cards playable and requires shared convention.
   - Why CK2 and CK3 should lead to different sender policies.

9. **Main result: model differences**
   - GPT-5.4: strong CK2 → CK3 policy switch.
   - DeepSeek V4 Flash: convention use remains high in CK2 and CK3.
   - Claude Sonnet 5.5: mostly DeepSeek-like in this scenario.

10. **Minimal-pair wording control**
    - Why we needed it.
    - What changed in the wording.
    - What stayed fixed.
    - Why the GPT-5.4 effect survived.

11. **What the traces show**
    - GPT-5.4 suppresses convention reliance under partner-knowledge uncertainty.
    - Sonnet and DeepSeek often identify the convention but still rely on it in CK2.
    - Evidence for an epistemic-recognition vs policy-integration gap.

12. **How to interpret the result carefully**
    - This is not a proof that a model “understands common knowledge.”
    - It is evidence about finite partner-knowledge assurance and action selection.
    - The core claim: epistemic state modulates policy in GPT-5.4 much more than in the other tested models.

13. **Next experiments**
    - Replicate the reliance structure with a second Hanabi state.
    - Add model × condition statistical analysis.
    - Add cross-play and convention-conflict experiments.
    - Turn the harness into a reusable evaluation suite.

14. **Takeaways**
    - Hanabi gives us controlled cooperative signaling problems.
    - The harness separates recognition, reasoning, and action.
    - Current evidence points to large model differences in epistemic-policy integration.

---

# 1. The core question

## Can an LLM act differently because of what it knows about its partner's knowledge?

The central question is **not** simply:

> Can the model solve Hanabi?

It is:

> **Can the model condition a cooperative action on the epistemic state of the team?**

In other words, can it distinguish between:

- “I know the convention.”
- “My partner may or may not know the convention.”
- “I know that my partner knows the convention.”

…and then **change its action accordingly**?

---

# The object we want to measure

A useful way to think about the experiment is as a causal chain:

```text
information given to the agent
            ↓
what the agent can infer about the partner
            ↓
which communication strategy is reliable
            ↓
which action the agent chooses
            ↓
coordination outcome
```

The key measurement is therefore **behavioral**.

A model saying

> “I know that my partner knows the convention”

is not enough.

We want to see whether that belief actually changes the selected action.

---

# Why this is a harder question than ordinary task success

Two agents can face the **same physical game state** but rationally choose different actions because their knowledge about each other is different.

| Physical situation | What the sender knows about the receiver | Rational communication policy |
|---|---|---|
| Same cards, same stacks, same legal hints | Receiver's convention knowledge is uncertain | Prefer a robust signal that works without the convention |
| Same cards, same stacks, same legal hints | Sender knows receiver has the convention | It is safe to exploit the convention |

So the experimental variable is not the board.

It is the **epistemic relationship between the players**.

This lets us ask whether the model is sensitive to something that is invisible in the physical state but crucial for coordination.

---

# Why Hanabi is a good testbed

Hanabi has several properties that make this unusually clean:

1. **Cooperative objective**  
   Both players want exactly the same outcome.

2. **Partial observability**  
   A player cannot see its own cards but can see its partner's cards.

3. **Restricted communication**  
   Players cannot freely explain their intentions; they communicate through legal Hanabi hints and actions.

4. **Actions can carry pragmatic meaning**  
   A hint can communicate more than its literal card information if both players share a convention.

5. **We can hold the physical state fixed**  
   Then we manipulate only what each agent is told about the convention and about the partner's knowledge.

That makes Hanabi a controlled laboratory for studying **coordination under nested knowledge**.

---

# The important distinction: shared information is not automatically common knowledge

Suppose both players independently receive the same convention.

That establishes:

```text
P0 knows the convention
P1 knows the convention
```

But it does **not necessarily establish**:

```text
P0 knows that P1 knows it
P1 knows that P0 knows it
```

And that still does not automatically establish deeper levels such as:

```text
P0 knows that P1 knows that P0 knows it
...
```

This hierarchy is exactly why “everyone received the same instruction” and “the instruction is common knowledge” are different experimental treatments.

---

# What we mean by “common knowledge” in this project

We use a ladder of increasingly strong epistemic treatments.

At this stage, the most important transition is:

```text
CK2
Both players receive the convention,
but the sender is not assured that the receiver has it.

                 ↓

CK3
Both players receive the convention,
and the sender is explicitly told that the receiver has it.
```

The crucial question is:

> **Does that extra assurance change the sender's policy?**

Later we also include a public/common declaration, `CK∞`, but we should be careful: these are **controlled prompt treatments**, not proof that an LLM has internally constructed arbitrary-depth formal common knowledge.

---

# Section 1 takeaway

If the audience remembers only one sentence, it should be this:

> **We are testing whether an LLM's cooperative policy changes when only the team's epistemic state changes.**

The cards can stay the same.

The legal actions can stay the same.

What changes is what the sender is entitled to assume about the receiver's knowledge.

That is the phenomenon the rest of the presentation will isolate experimentally.

---

# Working plan

We will build this presentation one section at a time.

For each section:

1. Draft the explanatory slides.
2. Add diagrams, tables, or trace snippets where useful.
3. Review and simplify the story.
4. Commit the updated Markdown file.

Next section to write: **2. Hanabi basics for this project**.
