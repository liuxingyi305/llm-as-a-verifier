# Reproduction notes — LLM-as-a-Verifier (Terminal-Bench 2.1, Best-of-3)

Course: Agentic AI for Business and FinTech (FTEC5660) — Reproducibility Work
Author: liuxingyi
Repo under test: https://github.com/llm-as-a-verifier/llm-as-a-verifier (v0.3.0, MIT)

---

## 1. What this repository does

`llm-verifier` scores a finished agent trajectory and uses the score to pick the
best of N candidate trajectories (best-of-N selection). Two mechanisms matter:

1. **Fine-grained reward.** Instead of a binary judgement, the verifier is asked
   for a score letter on a 20-point scale (A–T). The reward is the *expectation
   over the full logprob distribution* of the score token, not the sampled digit.
2. **Probabilistic pivot tournament.** Ranking N candidates takes `O(N·k)`
   pairwise comparisons instead of a full `O(N²)` round robin; `k` is explicit
   and trades verification cost against ranking accuracy.

## 2. Target claim reproduced

Paper claim (README, Terminal-Bench 2.1, mini-swe-agent × deepseek-v4-flash,
5 trials per task):

| Config | Pass@1 | LLM-as-a-Verifier | Oracle |
|---|---|---|---|
| Best-of-3 | 79.4% | 86.5% ± 1.1% | 92.1% |
| Best-of-5 | 78.7% | 88.0% ± 0.6% | 96.6% |

**Reproduction scope.** A fixed 10-task subset of the released
`data/terminal_bench_2.1_trajs/mini-swe-agent_deepseek-v4-flash` (first 10 task
directories in lexicographic order: `chess-best-move`, `break-filter-js-from-html`,
`cancel-async-tasks`, …). Per task we use the first 3 of the 5 released
trajectories, matching the Best-of-3 script. `pivots=1`, `seed=0`,
`n_evaluations=2`, criteria = the paper's three (`specification`,
`output_match`, `error_signals`).

Reported as a subset, so absolute values are not directly comparable to the
paper; what is testable is whether *the mechanism* (verifier selection beating
Pass@1) shows up at all.

## 3. Setup notes

- macOS, Python 3.13, CPU only; no GPU needed (verifier calls are API calls).
- `python3 -m venv .venv && ./.venv/bin/pip install -e .`
- Verifier backend: a DeepSeek-compatible relay (`https://api.dspass.net/v1`),
  model `deepseek-v4.1-flash`. The paper's verifier was `deepseek-flash` on
  DeepSeek's own endpoint, so **the backbone model differs**; results are
  indicative, not directly comparable.
- Prices quoted by the relay: CNY 2 / M input (cache miss), 0.04 / M (cache hit),
  8 / M output.

### Provider compatibility patch (not the modification)

The relay exposes the DeepSeek API surface (including token-level `logprobs`)
but is not `api.deepseek.com`, so `create_openai_client()` would classify it as
a generic OpenAI-compatible server and take the vLLM *prefill* path for reading
score tags. That path needs `continue_final_message` / `structured_outputs`,
which the relay ignores, and the scores silently collapse to 0.5.

Fix: honour a `VERIFIER_MODEL` environment variable in `create_openai_client()`
and tag the client with the DeepSeek call path
(`llm_verifier/fine_grained_reward.py`). Verified: the same three-candidate
example goes from `[0.5, 0.5, 0.5]` to `[0.6733, 0.3460, 0.4230]`, picking the
correct candidate.

## 4. Debug diary

| # | Blocker | What happened | Resolution |
|---|---|---|---|
| 1 | API key rejected | The key was issued by a relay, not by DeepSeek; sent to `api.deepseek.com` it returns 401 — different platforms. | Pointed `OPENAI_BASE_URL` at the relay instead. |
| 2 | Silent 0.5 scores | Generic OpenAI-compatible path uses the vLLM prefill trick; the relay ignores `continue_final_message`, scores fall back to a tie. | `VERIFIER_MODEL` patch → DeepSeek call path (see §3). |
| 3 | `DEEPSEEK_EFFORT=off/low` does not reduce cost | The relay accepts the `thinking` field but ignores it: `reasoning_content` is still produced. Scores also collapse to 0.5 through that path. | Abandoned; cost reduced by scope instead (subset + cache reuse). |
| 4 | Rate-limit errors | `--max-workers 8` produced 10 scoring errors in the first sweep. | `--max-workers 3` → 0 errors. |
| 5 | Cache reuse semantics | Cache key is `criterion|task|pair|rep`; it does **not** include K. | This is what makes the `K=2 → K=1` ablation almost free: K=1 reuses the cached rep-0 scores. |
| 6 | Long prompts | One comparison ≈ 110k input tokens (two full terminal transcripts + criteria). | Prefix caching absorbs ~99% of input; cost is dominated by output (reasoning) tokens. |

## 5. Cost ledger (measured)

| Item | Calls | Cost |
|---|---|---|
| 10-task pilot sweep (K=2) | 90 | ≈ CNY 6 |
| Baseline completion (cache hits) | 4 + 44 | ≈ CNY 3 |
| K=1 modification (cache reuse) | — | ≈ CNY 1 |

## 6. Files

- `scripts/repro_all.sh` — runs baseline (K=2) then modification (K=1)
- `scripts/smoke_proxy.py` — one-candidate-pool sanity check of the backend
- `cache/cache_tb21_10.json` — verifier score cache (re-runs are free)
- `results/tb21_K2.txt`, `results/tb21_K1.txt` — result tables
