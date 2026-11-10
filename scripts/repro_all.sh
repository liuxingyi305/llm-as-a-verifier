#!/usr/bin/env bash
# Reproduce the LLM-as-a-Verifier Best-of-3 result on a 10-task subset of
# Terminal-Bench 2.1, then run the single-variable modification (K: 2 -> 1).
#
# Budget: the K=2 scores are already cached, so this run only pays for the
# handful of cells that failed the first time (~CNY 3).
set -uo pipefail
cd "$(dirname "$0")/.."

PY=./.venv/bin/python
mkdir -p results

echo "=============================================="
echo "[1/2] BASELINE  K=2, 3 criteria, pivots=1"
echo "=============================================="
$PY scripts/run.py tb21_10 --pivots 1 --n-evaluations 2 --max-workers 3 \
  2>&1 | tee results/run_baseline_K2.log | grep -v "^Scoring"
cp -f results/tb21_10.txt results/tb21_K2.txt 2>/dev/null || true

echo
echo "=============================================="
echo "[2/2] MODIFICATION  K=1, 3 criteria, pivots=1"
echo "=============================================="
$PY scripts/run.py tb21_10 --pivots 1 --n-evaluations 1 --max-workers 3 \
  2>&1 | tee results/run_mod_K1.log | grep -v "^Scoring"
cp -f results/tb21_10.txt results/tb21_K1.txt 2>/dev/null || true

echo
echo "=============================================="
echo "DONE. Result tables:"
echo "  results/tb21_K2.txt   (baseline, K=2)"
echo "  results/tb21_K1.txt   (modification, K=1)"
echo "=============================================="
cat results/tb21_K2.txt 2>/dev/null
echo
cat results/tb21_K1.txt 2>/dev/null
