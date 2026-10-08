---
marp: true
theme: default
size: 16:9
title: Section 13 — Interpretation and next replication
paginate: true
style: |
  section { font-size: 28px; padding: 44px 60px; }
  h1 { font-size: 42px; margin-bottom: 0.55em; }
  h2 { font-size: 32px; }
  table { font-size: 21px; }
  pre, code { font-size: 20px; }
  blockquote { font-size: 27px; }
---

# 13. Interpretation and next replication

## The claim is stronger — and more specific

The old headline was:

~~~text
GPT-5.4 is sensitive to CK2 vs CK3
~~~

The new result says that this sensitivity depends on how mechanically derived
consequences are made available to the action policy.

---

# Recommended paper claim

> In a controlled Hanabi signaling diagnostic, GPT-5.4 can independently
> recover both the relevant hint mechanics and the partner-knowledge state.
> Nevertheless, its raw CK2 action policy usually relies on the convention.
> Feeding back only the model's own mechanical derivation restores the
> condition-appropriate CK2 policy.

This is narrower than "formal common knowledge," but more mechanistically useful.

---

# What we should not claim

Do not say:

~~~text
GPT-5.4 internally computed the mechanics
and consciously ignored them
~~~

The shadow probes are separate calls.

Do not say:

~~~text
GPT-5.4 has formal common knowledge
~~~

CK2 → CK3 is a finite partner-knowledge-assurance manipulation.

---

# Why the factorial result matters

It rules out several simpler stories.

~~~text
"just give it another try"
    -> fresh reaches only 30%

"just remind it receiver knowledge is unknown"
    -> epistemic-only reaches only 10%

"surface the hint consequences"
    -> mechanical reaches 100%
~~~

That is a causal localization, not only a correlation.

---

# Remaining limitation: one mechanical construction

The robust route in the current scenario depends on negative information:

~~~text
newest was not touched by rank 1
        ↓
therefore newest cannot be rank 1
        ↓
therefore newest is Y2
~~~

So the next replication should change the *mechanical route*.

---

# Chosen next replication

Build a second sender-reliance microstate where the robust route uses
**direct positive information** rather than the current negative-information
chain.

Preserve:

~~~text
CK2 expected -> robust signal
CK3 expected -> convention-dependent signal
~~~

Change rank/color values, touch pattern, stack state, and the mechanism
establishing robust playability.

---

# Why this replication is high value

If the same pattern appears:

~~~text
derived -> strong CK switch
raw -> weak CK switch
mechanical self-feedback -> rescue
~~~

then the result is unlikely to be an artifact of one negative-information
deduction.

That is a stronger generalization than immediately adding more models.

---

# After scenario replication

1. run the positive-information scenario on GPT-5.4;
2. repeat derived/raw/factorial controls;
3. then run the strongest contrasting models;
4. fit model × condition × scaffold × scenario analysis;
5. return to longer-horizon sender → receiver or full-game tests.

---

# Statistical framing

Repeated API calls are not independent human subjects.

Use paired exact tests and Wilson intervals as descriptive diagnostics.

For the mature study, model:

~~~text
action ~ condition * scaffold * model * scenario
~~~

with repetition/provider variation represented explicitly where possible.

---

# Section 13 takeaway

> **The next replication should change the Hanabi mechanics, not merely the
> wording or the model.**

A positive-information reliance scenario is the clearest next generalization
test.

---
