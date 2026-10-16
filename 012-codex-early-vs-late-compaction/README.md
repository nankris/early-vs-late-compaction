# #012 Early vs late compaction in one long Codex session

**Question.** In one long Codex session, does compacting early (a low `model_auto_compact_token_limit`) save money compared with letting the context grow, and does it cost any task success?

**Short answer (this build, these tasks).** Early compaction at 25K tokens cut total tokens per session by **44%** (1.62M → 0.91M, mean of 3 sessions each) and estimated cost by **22%** ($0.352 → $0.275 per 14-task session, *estimate*). All 6 sessions fixed all 14 packages (84/84 turns passed). The saving is smaller than the token drop because nearly all the tokens removed were cheap cached reads; uncached input (~76K) and output (~4K) were about the same in both arms. n = 3 sessions per arm, so treat the size of the saving as rough.

## Setup

- Codex CLI `codex-cli 0.162.1`, model `gpt-6.1-sol`, default reasoning effort, ChatGPT Plus login. Headless `codex exec --json`, then `codex exec resume <thread_id>` for every later turn, so all 14 turns of a session are one thread.
- Workload: the 14-package suite (`scripts/harness/fixtures/SUITE14`: 3 noisy-log bugs N01–N03 and 11 small edit tasks T01–T11). One package per turn, in a fixed order, in one shared working directory. Prompt per turn: ``Make `node test.js` pass inside the package folder `<pkg>/` by fixing that package's code. Do not edit any test.js. Only work on <pkg>/ in this turn.``
- Pass = that package's `node test.js` exits 0 and no `test.js` changed (hash check). Suite total = `node run_all.js` at the end.
- Arms (run in parallel pairs, so both arms of a rep saw the same time window):
  - `early25k`: `-c model_auto_compact_token_limit=25000`
  - `default`: key unset (the model's built-in limit; never reached here)
- Reps: 1, 3, 4. **Rep 2 was lost**: the sandbox VM restarted mid-run (14:45 UTC) and killed both rep-2 sessions after 6–7 turns. Those rows are kept in `results/interrupted_rep2.csv` and `results/raw_interrupted_rep2/` but excluded. A first attempt that failed to resume (a harness bug) is in `results/discarded_bad_resume/`, also excluded.
- Cost estimate: gpt-6.1-sol API list price $2.00/M uncached input, $0.10/M cached input, $10.00/M output (https://developers.openai.com/api/docs/models/gpt-6.1-sol, checked 2026-10-14). **All $ figures are estimates**; Plus is a flat subscription.

## Exact commands

```bash
source /workspace/tools/setup.sh
# one session = 14 turns: chain.sh EXP COND REP [config...]
scripts/harness/chain.sh . early25k 1 model_auto_compact_token_limit=25000
scripts/harness/chain.sh . default 1
# both arms for reps (as run)
REPS="1 2" scripts/run_chains.sh ; REPS=3 scripts/run_chains.sh ; REPS=4 scripts/run_chains.sh
# analysis (needs pandas + matplotlib)
/workspace/tools/mlenv/bin/python scripts/analyze.py
```

## Results (84 turns in 6 complete sessions, 2026-10-14 14:19–15:21 UTC / 19:49–20:51 IST)

Per session:

| Arm | Rep | Turns passed | Total tokens | Cached input | Uncached input | Output | Peak context | Compactions | Est. cost |
|---|---|---|---|---|---|---|---|---|---|
| default | 1 | 14/14 | 2.05M | 1.98M | 59.2K | 4.5K | 59.8K | 0 | $0.362 |
| default | 3 | 14/14 | 1.48M | 1.40M | 82.2K | 4.3K | 45.1K | 0 | $0.347 |
| default | 4 | 14/14 | 1.34M | 1.25M | 90.4K | 4.0K | 40.7K | 0 | $0.346 |
| early25k | 1 | 14/14 | 0.97M | 0.90M | 70.2K | 3.9K | 28.7K | 1 | $0.269 |
| early25k | 3 | 14/14 | 0.92M | 0.84M | 78.8K | 4.2K | 26.5K | 3 | $0.283 |
| early25k | 4 | 14/14 | 0.84M | 0.76M | 78.3K | 3.9K | 25.4K | 2 | $0.272 |

Mean per arm:

| Arm | Sessions | All 14 pass | Total tokens | Cached share | Uncached input | Output | Est. cost / session (range) |
|---|---|---|---|---|---|---|---|
| default | 3 | 3/3 | 1.62M | 94.9% | 77.3K | 4.3K | $0.352 ($0.346–0.362) |
| early25k | 3 | 3/3 | 0.91M | 91.6% | 75.7K | 4.0K | $0.275 ($0.269–0.283) |

Chart: `results/chart.png` (context size per turn with compaction marks, cumulative est. cost, token mix per arm).

### What the numbers say
1. **Early compaction kept context flat.** Peak request size stayed at 25–29K with a compaction every ~4–5 turns; the default arm grew steadily to 41–60K by turn 14 and never compacted.
2. **Tokens fell 44%, cost fell 22%.** Almost all the removed tokens were cache reads ($0.10/M). The cost gap is the per-turn re-read of a bigger cached prefix, which adds up over 14 turns.
3. **No success cost at this size.** Every turn passed in both arms, and the compacted sessions didn't need more model calls (46.7 vs 44.0 per session, within noise).
4. **Session-to-session variance is large in the default arm** (1.34M–2.05M tokens). Rep 1 started with a larger exploratory turn and carried that context forward. The cost ranges of the two arms don't overlap.

## Caveats
- n = 3 sessions per arm. Tasks are small and independent, so a summary loses little; work where later turns depend on details from earlier ones could suffer more from compaction.
- Each compaction is itself a model call; its tokens are included in the totals.
- Rate-limit percentages in `runs.csv` include other experiments on the same account at the same time.
- 10 turns hit transient 429 "Reconnecting…" retries that Codex recovered from on its own.
- Default reasoning effort; reasoning tokens were reported as 0.

## Files
- `scripts/harness/`: copy of the shared harness (`run_one.py`, `chain.sh`, `driver.sh`, `backfill.py`, fixtures)
- `scripts/run_chains.sh`, `scripts/analyze.py`
- `results/runs.csv` (one row per turn), `results/per_turn.csv`, `results/summary.csv` (per session), `results/summary_by_arm.csv`, `results/chain.log`
- `results/raw/*.jsonl`: raw `codex exec --json` streams per turn
- `results/interrupted_rep2.csv`, `results/raw_interrupted_rep2/`, `results/discarded_bad_resume/`: excluded runs, kept for transparency
