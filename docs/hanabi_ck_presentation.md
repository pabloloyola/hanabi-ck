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

# Working plan

We will build this presentation one section at a time.

For each section:

1. Draft the explanatory slides.
2. Add diagrams, tables, or trace snippets where useful.
3. Review and simplify the story.
4. Commit the updated Markdown file.

Next section to write: **1. The core question**.
