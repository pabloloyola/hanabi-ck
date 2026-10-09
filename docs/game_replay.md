# Share a recorded game

The replay is a single HTML file: open it in a browser or send it to a colleague.
Playback makes no API calls and needs no server, credentials, or installation.
The game itself is recorded by the existing full-game runner.

## First try: offline mechanics demonstration

```bash
uv run hanabi-ck run configs/replay_demo_simple.yaml
uv run hanabi-ck replay runs/replay_demo_simple/ck0/seed_000000.jsonl \
  --output demos/hanabi_replay_simple.html
open demos/hanabi_replay_simple.html
```

`open` is the macOS command. On another platform, open the HTML in your browser.
This is an actual engine game played by **rule-based agents**, not LLM evidence.
The agents do not read the experimental convention instructions.

## Record one LLM game

`configs/replay_demo_llm.yaml` uses the established OpenRouter GPT-5.4
settings for both players: `openai/gpt-5.4`, OpenAI provider routing without
fallbacks, medium reasoning, and structured action output. Set
`OPENROUTER_API_KEY` in your terminal (or use the existing `OPENAI_API_KEY`).
Credentials are read from the environment; do not put them in the config.
This runs one two-player game in CK3 with the derived mechanical scaffold,
not a controlled CK2/CK3 comparison. A full game can require dozens of model
calls. Change both agent entries if you want to use a different model.

```bash
uv run hanabi-ck run configs/replay_demo_llm.yaml
uv run hanabi-ck replay runs/replay_demo_llm/ck3_mutual/seed_000000.jsonl \
  --output demos/hanabi_replay_llm.html
open demos/hanabi_replay_llm.html
```

Any existing full-game JSONL can be exported with `replay LOG --output FILE`.
Older logs remain usable: unavailable requests and after-action views are marked
as not recorded. Micro-pair logs are not supported by this first viewer.
Re-running an identical experiment/condition/seed overwrites its source log;
export or copy a replay before repeating it if you want to preserve that run.

## A concise walkthrough

1. Start in **player view**. Explain that the acting player sees partner cards,
   while its own cards are represented by legal hint-derived knowledge.
2. Step through the first hint. Gold outlines show the touched slots. Select
   **After action** to inspect the new knowledge.
3. Jump to the first play. Contrast actual success with a mechanically guaranteed
   safe play. The “Safe” badge is computed by the engine, not a claim about
   the model's internal beliefs.
4. Open **Inspect this decision** for the request, legal actions, returned index,
   parsed/executed action, response, and any fallback.
5. Reveal the researcher view only when explaining the distinction between true
   cards and player knowledge. Finish on the final record and after-action board.

The explanations are deterministic descriptions of recorded mechanics. They do
not invent the model's reasons or infer convention use from a hint alone.

## What is recorded

New full-game logs add:

- `request_payload`: the actual JSON constructed inside the action call, including
  model settings, messages, and response schema. HTTP authentication headers are
  not included. A failed transport call retains its attempted payload.
- `researcher_true_state_after`: the complete engine state after execution.
- `observation_after`: the acting player's observation after execution.
- `game_done`: whether the action ended the game.

Existing fields retain observations, legal actions, private instructions, raw and
API responses (including provider usage when returned), before-state, outcomes,
errors, and fallback information. Request logging is on by default; set
`log_request_payloads: false` to disable it. It is also suppressed when
`log_private_instructions: false`. Other logging controls retain their meanings.
Rule-based agents have no model request or response; the viewer says so.

The HTML embeds the original log, including researcher-only data. Player view is
an explanatory display, not access control: the colleague can inspect the full
record or download the original JSONL. Exact requests are displayed as recorded;
missing data is never reconstructed and presented as an actual request.

## Audit and choose an illustrative game

First audit the existing recording (no model calls):

```bash
uv run hanabi-ck replay-audit runs/replay_demo_llm/ck3_mutual/seed_000000.jsonl
```

`eligible: true` means complete, error-free, with no fallback actions, recorded
LLM requests, and all implemented structural log checks passing. The audit
checks turn indices, legal execution, before/after continuity, stack observations,
and score transitions. It does not reconstruct a model's reasoning or re-run the
whole game engine. Teaching coverage reports knowledge-changing hints, safe
plays, discards, and misplays, with up to three example turn indices (zero-based).

Run the predeclared reference batch using the same established OpenRouter
settings. It writes to a separate experiment directory and preserves your first
recording. Seeds 0–9 are ten new recordings, including a fresh sample of seed 0.
This makes paid model calls and may take time; completed game JSONLs are written
as the runner progresses. The summary is written after the full batch finishes.

```bash
uv run hanabi-ck run configs/replay_reference_10.yaml
uv run hanabi-ck replay-audit runs/replay_demo_llm/ck3_mutual/seed_000000.jsonl \
  --reference runs/replay_reference_10/summary.json
uv run hanabi-ck replay-select runs/replay_reference_10/summary.json \
  --output demos/hanabi_selected.html
open demos/hanabi_selected.html
```

The selection rule is fixed before looking at results: nearest median score,
then nearest median turn count, then coverage of hinting/safe plays/discarding,
then lowest seed. Do not change it to prefer a dramatic or unusually successful
game. Complete games that end by exhausting lives remain eligible; unsuccessful
performance is not an API failure.

The reference distribution uses complete, error-free, structurally verified
games. All excluded runs and their audits remain in the companion
`demos/hanabi_selected.audit.json` report; the HTML caption states the recorded,
eligible, and excluded counts. A high exclusion count limits the illustration's
scope to successful execution. Mixed conditions, models, scaffolds, instructions,
or recorded request settings are not pooled. Request fingerprints exclude
changing messages and per-turn legal-action schema contents.

Comparing the first recording reports medians, observed ranges, and differences
from the medians when recorded settings match. Ten games give a rough empirical
reference, not a claim of population representativeness. A typical CK3 full game
still does not establish CK2→CK3 sensitivity; use the controlled microstate
comparison for that scientific claim.
