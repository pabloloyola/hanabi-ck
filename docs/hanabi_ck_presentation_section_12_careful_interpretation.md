---
marp: true
theme: default
size: 16:9
title: Section 12 — Careful interpretation
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

# 12. Careful interpretation

## The result is strong, but narrow

The current evidence is compelling for one controlled diagnostic.

But the claim should stay precise.

We have not proven a general theory of model common knowledge.

We have shown a behavioral dissociation in a deliberately constructed Hanabi signaling task.

---

# What we can say

A careful positive claim:

> In this controlled scenario, GPT-5.4 robustly changes its sender policy when moving from unassured to assured receiver convention knowledge.

And:

> DeepSeek V4 Flash and Claude Sonnet 5.5 mostly do not make that policy adjustment under the same manipulation.

This is the core result.

---

# What we should not say

Avoid these stronger claims:

```text
GPT-5.4 has formal common knowledge.
DeepSeek cannot reason about partner knowledge.
Sonnet does not understand conventions.
```

Those are too broad.

The experiment measures policy sensitivity in a specific epistemic manipulation.

---

# The right conceptual label

The best current phrase is:

```text
partner-knowledge assurance
```

or:

```text
finite higher-order epistemic sensitivity
```

rather than simply:

```text
common knowledge
```

Common knowledge is the motivating concept, but CK2 → CK3 is a finite controlled contrast.

---

# Why CK2 → CK3 is not CK∞

CK3 gives explicit assurance that the partner has the convention.

CK∞ is a stronger public/common declaration.

```text
CK3: I know my partner knows C
CK∞: public/common declaration of C
```

Our strongest result is about the CK2 → CK3 transition.

So the paper language should reflect that.

---

# What the result is not about

This is not primarily a test of:

- full-game Hanabi skill
- long-horizon planning
- memorized Hanabi conventions
- raw card-counting ability
- benchmark score maximization

It is a test of whether an epistemic fact changes an action policy in a controlled communication problem.

---

# Why full-game score would be insufficient

A full-game score can hide the relevant mechanism.

A model could score well while:

```text
using conventions too aggressively
ignoring partner uncertainty
getting lucky because the partner happens to understand
```

Or it could score poorly for unrelated reasons.

The micro-diagnostic isolates the policy decision we care about.

---

# Repeated calls are not human subjects

The counts are repeated model samples, not independent people.

So p-values and confidence intervals should be treated as descriptive diagnostics.

They help summarize separation.

They do not automatically imply a population-level psychological claim.

For stronger analysis, we should model repetition, prompt, scenario, and model family explicitly.

---

# Remaining confound: one scenario

The strongest current result uses one carefully designed Hanabi state.

That is good for interpretability.

But it raises a question:

```text
Is the effect about the epistemic structure,
or about this exact rank-1 / rank-2 construction?
```

We need scenario replications.

---

# Remaining confound: provider behavior

We also use different providers and routes:

```text
OpenRouter
Amazon Bedrock route
hosted vLLM routes
model-specific reasoning settings
```

The harness logs these details.

But a mature study should replicate important runs across stable provider settings where possible.

---

# Remaining confound: custom engine

Our custom harness gives us microstate control.

But custom engines can contain subtle rule bugs.

The best response is not to abandon the harness.

It is to add reference validation:

```text
hanabi-ck experimental layer
        +
HLE-style parity tests for standard mechanics
```

---

# What makes the current result credible

Despite the caveats, several things strengthen the result:

- paired CK2 / CK3 comparisons
- matched action order within pairs
- minimal-pair wording control
- raw response logging
- strict action validation
- multiple model comparison
- traces consistent with the behavioral story

The effect is not a single fragile observation.

---

# Recommended claim for a paper or talk

> We introduce a Hanabi micro-diagnostic for partner-knowledge-sensitive signaling. In this diagnostic, GPT-5.4 strongly changes its hint choice when receiver convention knowledge becomes assured, while DeepSeek V4 Flash and Claude Sonnet 5.5 largely do not.

That is precise, defensible, and still interesting.

---

# Section 12 takeaway

> **The result is best interpreted as behavioral evidence of partner-knowledge-sensitive policy selection, not as proof of formal common knowledge.**

That careful framing makes the project stronger, not weaker.

---
