#!/bin/bash
# Two long sessions in parallel per rep: early compaction (25K) vs default (unset).
E3=/workspace/work/tig/012-codex-early-vs-late-compaction
H=/workspace/work/tig/_harness
for rep in ${REPS:-1 2}; do
  [ -e $H/QUOTA_HIT ] && break
  $H/chain.sh $E3 early25k $rep model_auto_compact_token_limit=25000 >> $E3/results/chain.log 2>&1 &
  $H/chain.sh $E3 default $rep >> $E3/results/chain.log 2>&1 &
  wait
done
echo "ALL_DONE $(date -u +%s)" >> $E3/results/chain.log
