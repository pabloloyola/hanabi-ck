---
marp: true
theme: default
size: 16:9
title: Section 5 — Early failures and harness fixes
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

# 5. Early failures and harness fixes

## Why this section matters

Before trusting an epistemic result, we first had to make sure we were not measuring:

- a weak baseline policy
- an API formatting quirk
- provider-specific output behavior
- an invalid action
- a truncated completion
- an action-order shortcut

Many of the harness features exist because one of these things actually failed.

---

# Failure 1 — a legal agent can still be useless

An early simple policy could remain technically legal while making almost no progress.

For example:

```text
not sure what to play
        ↓
discard
        ↓
still not sure
        ↓
discard again
```

A legal-action engine alone is therefore not enough.

We need a baseline that makes **epistemically justified** progress.

---

# Fix 1 — an epistemically safe baseline

The deterministic `SimpleAgent` now follows a hierarchy:

```text
1. play a card only if it is provably playable
2. prefer a hint that creates a provably playable card
3. discard only a provably obsolete card when possible
4. otherwise cycle a card / give useful information
```

The baseline ignores the experimental CK convention.

That is intentional: it checks the ordinary Hanabi mechanics without contaminating the CK treatment.

---

# Failure 2 — "no answer" did not always mean no answer

Different reasoning-model APIs place text in different fields.

A response may contain:

```text
message.content
message.reasoning_content
message.reasoning
```

Some models returned an empty `content` field while useful text existed in a reasoning field.

If the harness inspected only `content`, a valid response could look like a failure.

---

# Fix 2 — normalize response channels

The agent wrapper now checks, in order:

```text
content
  ↓
reasoning_content
  ↓
reasoning
```

and records which channel supplied the text.

This matters because:

> **transport format should not become an experimental variable.**

We still log the raw API response so unusual provider behavior remains inspectable.

---

# Failure 3 — HTTP 200 does not imply a usable action

A request can succeed at the HTTP level but still be unusable.

Examples:

```text
finish_reason = length
reasoning consumed the token budget
no final JSON emitted
invalid JSON
action_index outside the legal range
```

So "the API call worked" and "the experimental sample is valid" are different statements.

---

# Fix 3 — explicit validation

Before executing an action, the harness checks:

```text
completion not truncated
        ↓
JSON object can be extracted
        ↓
exactly one field: action_index
        ↓
action_index is an integer
        ↓
index lies inside the legal-action list
```

Invalid output is recorded as an error rather than silently converted into a different decision.

---

# Failure 4 — structured output is provider-dependent

We initially wanted every model to use strict JSON-schema output.

That worked for some routes.

It did **not** work for every provider/model combination.

Example from our Sonnet setup:

```text
basic chat          ✓
strict json_schema  ✗
```

The model itself was reachable; the selected provider route simply did not support the requested schema mode.

---

# Fix 4 — test the exact request mode first

The `api-check` command now tests the controls used by the experiment:

```text
model
provider routing
temperature
max_tokens
reasoning settings
structured_output
```

If strict structured output is disabled, the harness instead:

```text
asks for JSON in the prompt
        +
validates JSON client-side
```

This keeps unsupported API features from masquerading as model failures.

---

# Failure 5 — a reasoning model can run out of tokens before answering

We observed calls where the model produced substantial reasoning but never reached the final action.

The API reported a length stop.

That is qualitatively different from:

```text
model chose an invalid action
```

or:

```text
model chose the wrong epistemic policy
```

A generation failure should not be counted as behavioral evidence.

---

# Fix 5 — truncation is an explicit error

The harness checks both:

```text
finish_reason
native_finish_reason
```

If the completion ended because of the token limit, the sample is marked invalid.

We preserve:

- whether final content was present
- whether reasoning was present
- the raw response
- the provider metadata

This is why our DeepSeek minimal-pair run could be reported as **18/20 valid CK2 calls**, rather than pretending all 20 were behavioral observations.

---

# Failure 6 — silent fallback can corrupt an experiment

Suppose the model fails and the harness quietly substitutes a safe action.

Then the log could look like:

```text
model condition → safe action
```

even though the model never chose that action.

That would contaminate the treatment effect.

---

# Fix 6 — error policy is explicit

The runner supports an explicit error policy.

For our diagnostic experiments we generally use:

```text
agent_error_policy: abort
```

So a failed model call does not become a synthetic model decision.

If a fallback is ever enabled, the log marks:

```text
fallback_used
fallback_policy
model_action_index
executed_action_index
```

The distinction remains visible.

---

# Failure 7 — action ordering can become a shortcut

If the important action always appears at the same index, a model might learn or prefer:

```text
"choose option 2"
```

rather than reasoning about the Hanabi state.

That would be an **index bias**, not epistemic coordination.

---

# Fix 7 — shuffle, but pair the shuffle

Legal actions are shuffled.

But within a paired CK2 / CK3 comparison, the action order is held matched.

```text
repetition 7

CK2: same shuffled legal-action order
CK3: same shuffled legal-action order
```

Across repetitions, the positions vary.

So a CK2 → CK3 switch cannot be explained by the target action moving to a different index.

---

# Why raw logs matter

Aggregate numbers tell us **that** behavior differs.

Raw logs help us understand **why**.

For each sample we can inspect:

```text
prompt treatment
observation
legal actions
action ordering
raw model response
provider response
parsed action
diagnostic label
error state
```

This is how we discovered several of the failure modes in this section.

---

# What these fixes buy us

After these fixes, a recorded action has a much clearer meaning:

```text
the intended model/provider was called
        ↓
the request completed
        ↓
the response was parseable
        ↓
the chosen index was legal
        ↓
no hidden fallback replaced it
        ↓
the action can be compared across CK treatments
```

That is the minimum foundation needed before interpreting epistemic behavior.

---

# Section 5 takeaway

> **Most harness engineering is about preventing infrastructure failures from looking like cognitive results.**

Only after controlling parsing, truncation, provider behavior, fallbacks, and action ordering can we credibly ask:

> Did the model choose differently because its knowledge about the partner changed?

---
