#!/usr/bin/env python3
"""#012: one long resumed session (14 turns, one package per turn) at two auto-compaction limits.
Per-chain totals -> results/summary.csv, per-turn -> results/per_turn.csv, chart -> results/chart.png.
Also counts compactions straight from the session rollouts (top-level "compacted" records)."""
import glob, json, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P_IN, P_CACHED, P_OUT = 2.00, 0.10, 10.00
df = pd.read_csv(os.path.join(HERE, "results", "runs.csv"))
df["turn"] = df.groupby(["cond", "rep"]).cumcount() + 1


def rollout_compactions(tid):
    hits = glob.glob(os.path.expanduser(f"~/.codex/sessions/**/*{tid}*.jsonl"), recursive=True)
    n = 0
    for h in hits:
        for line in open(h):
            if line.startswith("{") and '"type":"compacted"' in line[:200]:
                n += 1
    return n


rows = []
for (cond, rep), g in df.groupby(["cond", "rep"]):
    tid = g.thread_id.iloc[0]
    rows.append(dict(
        cond=cond, rep=rep, thread_id=tid, turns=len(g), turns_passed=int(g.passed.sum()),
        final_packages_passing=int(g.subtests_passed.iloc[-1]), suite_all_pass=int(g.subtests_passed.iloc[-1] == 14),
        total_tokens=int(g.total_tokens.sum()), input_tokens=int(g.input_tokens.sum()),
        cached_input_tokens=int(g.cached_input_tokens.sum()), uncached_input_tokens=int(g.uncached_input_tokens.sum()),
        output_tokens=int(g.output_tokens.sum()), cache_share=round(g.cached_input_tokens.sum() / g.input_tokens.sum(), 4),
        est_cost_usd=round(g.est_cost_usd.sum(), 4), model_calls=int(g.model_calls.sum()),
        peak_context_max=int(g.peak_context_tokens.max()), compactions_in_rollout=rollout_compactions(tid),
        wall_s=round(g.wall_s.sum(), 1)))
chains = pd.DataFrame(rows)
chains.to_csv(os.path.join(HERE, "results", "summary.csv"), index=False)
print(chains.to_string())
complete = chains[chains.turns == 14]
arm = complete.groupby("cond").agg(chains=("rep", "count"), all_pass=("suite_all_pass", "sum"),
                                 total_tokens_mean=("total_tokens", "mean"), cached_mean=("cached_input_tokens", "mean"),
                                 uncached_mean=("uncached_input_tokens", "mean"), output_mean=("output_tokens", "mean"),
                                 cache_share_mean=("cache_share", "mean"), cost_mean=("est_cost_usd", "mean"),
                                 cost_min=("est_cost_usd", "min"), cost_max=("est_cost_usd", "max"),
                                 compactions_mean=("compactions_in_rollout", "mean"), peak_ctx=("peak_context_max", "mean"))
arm.round(4).to_csv(os.path.join(HERE, "results", "summary_by_arm.csv"))
print(arm.round(4).to_string())
df[["cond", "rep", "turn", "task", "passed", "subtests_passed", "input_tokens", "cached_input_tokens",
    "uncached_input_tokens", "output_tokens", "est_cost_usd", "model_calls", "peak_context_tokens", "compactions",
    "wall_s"]].to_csv(os.path.join(HERE, "results", "per_turn.csv"), index=False)

colors = {"default": "#4c72b0", "early25k": "#c44e52"}
names = {"default": "default (no early compaction)", "early25k": "model_auto_compact_token_limit=25000"}
fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
for (cond, rep), g in df.groupby(["cond", "rep"]):
    ls = {1: "-", 2: ":", 3: "--", 4: "-."}.get(int(rep), "-")
    ax[0].plot(g.turn, g.peak_context_tokens / 1000, ls, marker="o", ms=3, color=colors.get(cond, "gray"),
               label=f"{cond} r{rep}")
    ax[1].plot(g.turn, g.est_cost_usd.cumsum() * 100, ls, marker="o", ms=3, color=colors.get(cond, "gray"),
               label=f"{cond} r{rep}")
    comp = g[g.compactions > 0]
    ax[0].scatter(comp.turn, comp.peak_context_tokens / 1000, marker="x", s=60, color="black", zorder=4)
ax[0].set_title("Context size per turn (largest request, K tokens)\nx = turn with a compaction", fontsize=10)
ax[0].set_xlabel("turn (one package per turn)")
ax[1].set_title("Cumulative est. API cost (US cents)", fontsize=10)
ax[1].set_xlabel("turn")
for a in ax[:2]:
    a.grid(alpha=0.3)
    a.legend(fontsize=7)
arms = list(arm.index)
x = range(len(arms))
w = 0.38
ax[2].bar([i - w / 2 for i in x], arm.cached_mean / 1000, w, color="#8fbcd4", label="cached input (K)")
ax[2].bar([i + w / 2 for i in x], (arm.uncached_mean + arm.output_mean) / 1000, w, color="#e3a07a",
          label="uncached input + output (K)")
for i, c in enumerate(arms):
    ax[2].text(i, max(arm.cached_mean) / 1000 * 1.02, f"${arm.cost_mean[c]:.3f}/chain", ha="center", fontsize=8)
ax[2].set_xticks(list(x))
ax[2].set_xticklabels([names.get(c, c) for c in arms], fontsize=8)
ax[2].set_title("Tokens per 14-turn session (mean of chains)", fontsize=10)
ax[2].set_ylim(0, max(arm.cached_mean) / 1000 * 1.2)
ax[2].legend(fontsize=8, loc="center right")
ax[2].grid(axis="y", alpha=0.3)
fig.suptitle("Codex 0.162.1 (gpt-6.1-sol): one resumed session fixing 14 packages, early vs default auto-compaction", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "results", "chart.png"), dpi=130)
print("wrote chart")
