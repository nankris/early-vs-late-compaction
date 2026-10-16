# Compacting early made a long Codex session 22% cheaper, and nothing broke

*Draft. Tech in General experiment #012. Numbers are from 84 headless Codex turns (6 sessions of 14 turns) on 2026-10-14. All $ figures are estimates at API list price.*

Coding agents keep the whole conversation in context, so a long session re-reads more and more on every turn. Codex can summarize ("compact") the history once the context passes a limit, set by `model_auto_compact_token_limit`. The usual worry: compact too early and the agent forgets things it needs. I wanted to know what early compaction actually buys you, and what it costs.

## The setup

One Codex session (CLI 0.162.1, gpt-6.1-sol, ChatGPT Plus login) fixed 14 small JavaScript packages, one per turn, using `codex exec resume` so every turn continued the same thread. I ran it two ways:

- **early**: compact once the context passes 25K tokens
- **default**: no limit set (Codex's own limit is far above anything this session reached)

Three full sessions each. A fourth pair died halfway when my sandbox restarted, so I left it out.

## What happened

Every session fixed all 14 packages. The difference was the bill:

| | Tokens per session | Est. cost per session | Peak context |
|---|---|---|---|
| default | 1.62M | $0.352 | 41–60K |
| compact at 25K | 0.91M | $0.275 | 25–29K |

With the default setting the context climbed every turn and never compacted. With the 25K limit Codex compacted every 4–5 turns, and the context dropped back to about 16–20K each time.

## Why tokens fell 44% but cost only 22%

Nearly all the tokens early compaction removed were **cache reads**. Codex re-sends the conversation each turn, and the provider caches the repeated part, which is billed at $0.10 per million instead of $2. Fresh input (about 76K per session) and output (about 4K) were the same in both arms. So most of the saving comes from re-reading a smaller cached history 40-odd times, and that's worth about 8 cents a session at list price.

## Did the agent forget anything?

Not here. Every turn passed, and the compacted sessions used about the same number of model calls (47 vs 44 per session). These tasks were independent of each other, though. Package 9 never needed anything from package 3. On work where later steps depend on early details, a summary could drop something that matters, and this test can't see that.

## The takeaway

For a long Codex session made of mostly independent steps, a low compaction limit is a cheap win: about a fifth off the estimated cost, no lost tasks. Just don't expect it to cut cost as much as it cuts tokens, because most of those tokens were already cheap.

*Caveats: 3 sessions per arm, small tasks, default reasoning effort. Full tables and raw logs are in the repo README.*
