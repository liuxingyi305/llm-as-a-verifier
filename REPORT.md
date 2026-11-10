# Reproducing LLM-as-a-Verifier on a Terminal-Bench 2.1 Subset

**Agentic AI for Business and FinTech (FTEC5660) — Reproducibility Work**

Name: _[fill in]_ · Student ID: _[fill in]_ · Date: 10 November 2026

Repository under test: `llm-as-a-verifier/llm-as-a-verifier` (v0.3.0, MIT, 3.3k stars)
My fork: `github.com/liuxingyi305/llm-as-a-verifier` (branch `repro`)

---

## 1. Project summary and what I tried to reproduce

**What the system is.** `llm-verifier` is a general-purpose verifier for agent
trajectories. Given a task and N candidate trajectories produced by some agent,
it ranks them and picks the best one (best-of-N selection). Two mechanisms do
the work, and both are technical rather than prompt-only:

1. **Fine-grained reward from logprobs.** The verifier is asked to place each
   candidate on a 20-point letter scale (A–T). The reward is not the sampled
   letter but the **expectation over the full logprob distribution** of the score
   token: each letter `l_i` is mapped to a value `20 − i`, and the reward is
   `Σ p(l_i) · v(l_i)`. This turns a coarse judgement into a continuous score
   that can rank candidates separated by a hair.
2. **Probabilistic pivot tournament.** Ranking N candidates by pairwise
   comparison is `O(N²)`. The framework instead runs a ring pass to elect
   leaders, then pivot rounds, giving `O(N·k)` comparisons for `k` pivots — a
   knob that trades verification cost against ranking accuracy.

**What I tried to reproduce.** The paper's headline result on Terminal-Bench 2.1
(self-verification, mini-swe-agent trajectories, 5 trials per task):

| Config | Pass@1 | LLM-as-a-Verifier | Oracle |
|---|---|---|---|
| Best-of-3 | 79.4% | 86.5% ± 1.1% | 92.1% |
| Best-of-5 | 78.7% | 88.0% ± 0.6% | 96.6% |

The claim under test is directional and falsifiable: **using the verifier to pick
among existing rollouts beats taking a single rollout (Pass@1), and approaches
the oracle upper bound.** No new agent rollouts are generated, so the experiment
isolates the selection mechanism.

## 2. Setup notes

| Item | Detail |
|---|---|
| Environment | macOS (Apple silicon), Python 3.13, CPU only — no GPU needed |
| Install | `python3 -m venv .venv && ./.venv/bin/pip install -e .` (deps: `openai`, `google-genai`, `tqdm`) |
| Data | Shipped with the repo: `data/terminal_bench_2.1_trajs/mini-swe-agent_deepseek-v4-flash` — 89 tasks × 5 released trajectories (≈500 MB checkout) |
| Verifier backend | DeepSeek-compatible relay (`https://api.dspass.net/v1`), model `deepseek-v4.1-flash` |
| Pricing (relay) | CNY 2 / M input (cache miss), 0.04 / M (cache hit), 8 / M output |
| Config | `pivots=1`, `n_evaluations=2`, `seed=0`, criteria = `specification`, `output_match`, `error_signals` |
| Wall time | Baseline sweep ≈ 25 min at `--max-workers 3` (48 verifier calls) |

**Model substitution (documented, not the modification).** The paper verifies
with `deepseek-flash` on DeepSeek's own endpoint; I used `deepseek-v4.1-flash`
through a relay. Decoding parameters are fixed by the framework (temperature 1.0
for the sampled score tags, `max_tokens` from `DEEPSEEK_MAX_TOKENS`). **Results
are therefore not directly comparable to the paper**; what is comparable is the
direction and size of the verifier-vs-Pass@1 gap.

**Total experimental spend: ≈ CNY 10** (including one discarded pilot and cache
re-computation). A clean re-run of the reported configuration from an empty
cache costs ≈ CNY 7.

## 3. Reproduction target and metric definitions

| Metric | Definition (as implemented by `scripts/run.py`) |
|---|---|
| Pass@1 | Mean released-trial reward on the subset (0/1 per trajectory) |
| LLM-as-a-Verifier | Reward of the trajectory the tournament selects |
| Oracle | Reward of the best available trajectory (upper bound) |
| Comparisons / task | `9.0` (3 criteria × 2 repeated evaluations × pivot comparisons) |

**Scope: a 10-task subset.** Following the assignment's guidance to reproduce
"one benchmark, one table row", I took the first 10 task directories of the
released Terminal-Bench 2.1 trajectories in lexicographic order. The verifier
only ever sees `problem` and `trace`; `reward` stays held out and is used only
for scoring.

## 4. Results: my numbers vs the reported numbers

### 4.1 The run

```
TERMINAL-BENCH 2.1 SUBSET (10 tasks, mini-swe-agent, deepseek-v4-flash, x5)
  K=2  pivots=1  seed=0   tasks=10  swing=3  N(trials)=5
------------------------------------------------------------------------
Method                    Score     Rate
Pass@1                 8.60/10    86.0%
LLM-as-a-Verifier        10/10   100.0%
Oracle (Bo5)             10/10   100.0%
```

| | Paper (89 tasks, deepseek-flash) | Mine (10 tasks, deepseek-v4.1-flash) |
|---|---|---|
| Pass@1 | 79.4% (Bo3) / 78.7% (Bo5) | **86.0%** |
| Verifier | 86.5% / 88.0% | **100.0%** |
| Oracle | 92.1% / 96.6% | **100.0%** |
| Verifier − Pass@1 | +7.1 / +9.3 pp | **+14.0 pp** |

### 4.2 The honest reading: the subset is too easy

The 10 tasks break down as **7 all-pass** (5/5 trials succeed), **3 swing**
(mixed), **0 all-fail**. On the 7 all-pass tasks every method scores 100% by
construction, so only 3 tasks carry information:

| Slice | Pass@1 | Verifier | Oracle |
|---|---|---|---|
| All 10 tasks | 86.0% | 100% | 100% |
| **3 swing tasks only** | **53.3% (8/15)** | **100% (3/3)** | 100% |

On the informative slice the verifier recovered *every* task (+46.7 pp), which is
the direction the paper reports. But n = 3, so this is an existence proof, not a
replication: the confidence interval on 3 tasks spans almost everything.

**A useful side-check on the data itself.** Over all 89 tasks the released
trajectories split into 50 all-pass / 36 swing / 3 all-fail, with an overall
reward rate of **78.7%** — exactly the paper's reported Bo5 Pass@1 (78.7%).
That the corpus aggregates to the published number is reassuring: the failure to
reproduce the *gap* is a property of my subset, not of the data.

### 4.3 Cost structure (measured, not estimated)

| Quantity | Value |
|---|---|
| Verifier calls for the baseline | 48 |
| Input tokens / call (avg) | 64,088 |
| Input served from prefix cache | **92.7%** |
| Output tokens, of which reasoning | 429,089 → **98.6% reasoning** |
| Cost / call | ≈ CNY 0.083 |
| Cost / task | ≈ CNY 0.40 |

Two findings worth carrying into any future work on this framework:

- **Input is huge but cheap.** One comparison ingests two full terminal
  transcripts (~64k tokens average, up to ~110k). Prefix caching absorbs 92.7%
  of it, so input accounts for only ~14% of the bill.
- **Output is the cost driver, and 98.6% of output is reasoning tokens.** The
  relay accepts DeepSeek's `thinking` / `reasoning_effort` fields but ignores
  them — disabling thinking is *not* a cost lever here. Cost scales with the
  verifier's deliberation, not with context length.

## 5. My modification and its measured impact

**Change: `n_evaluations` K = 2 → 1.** The paper's third stated mechanism is
"scale repeated evaluation": each criterion is scored K times and averaged to
reduce variance. I halved K while holding everything else fixed — same 10 tasks,
same 3 criteria, `pivots=1`, `seed=0`, same model, same backend.

**Result.**

| Config | Pass@1 | Verifier | Additional calls | Selection identical? |
|---|---|---|---|---|
| K = 2 (baseline) | 86.0% | 100% | 48 | — |
| K = 1 (modification) | 86.0% | 100% | **0** (cache reuse) | **yes, all 10 tasks** |

**Why zero calls, and why that is not cheating.** The score cache is keyed by
`criterion | task | comparison-pair | repetition-index`. Because K=1 requests only
repetition 0, every required score was already present from the K=2 sweep, so the
modification re-derived the ranking from cached rep-0 scores at no cost. This is
a real property of the implementation, and it means **K=1 is strictly cheaper
than K=2 for identical output** — but only on a subset where the answer is
already saturated.

**Interpretation, stated honestly.** The modification produced **no measurable
difference**, and the ceiling effect explains why: with 7 of 10 tasks passing in
every trial, a ranking change cannot surface even if repetition variance exists.
The correct conclusion is not "K is useless" but "**K's effect is not
identifiable on this subset**". Testing it properly requires a swing-heavy subset
(where Pass@1 sits near 50%), which I costed at ≈ CNY 9 for 6 tasks and did not
run, to stay inside the assignment's compute budget.

## 6. Debug diary

| # | Symptom | Diagnosis | Resolution |
|---|---|---|---|
| 1 | `401 Authentication Fails` on the first key | Key belonged to a relay, not to `api.deepseek.com` | Pointed `OPENAI_BASE_URL` at the relay |
| 2 | Scores silently all `0.5` | Generic OpenAI-compatible client takes the vLLM **prefill** path (`continue_final_message`, `structured_outputs`); the relay ignores both, so no score distribution is returned and every tie resolves to 0.5 | Patch: honour `VERIFIER_MODEL` and tag the client with the DeepSeek call path (model emits the tags itself). Verified `[0.5,0.5,0.5]` → `[0.6733,0.3460,0.4230]`, correct candidate picked |
| 3 | `DEEPSEEK_EFFORT=off/low` has no effect | The relay accepts the `thinking` field and still returns `reasoning_content` | Abandoned as a cost lever; reduced scope instead |
| 4 | 10 scoring errors in the first sweep | Concurrency 8 tripped relay rate limits | `--max-workers 3` → 0 errors in 48 calls |
| 5 | Crash at 92% with no result file | Local temp-directory restriction in the harness, not a framework bug | Re-ran with `TMPDIR` inside the workspace; cache made the re-run nearly free |
| 6 | Aborted a swing-subset run at 0/300 jobs | A swing-heavy subset makes the loader score **all 5 trials** (300 comparisons ≈ CNY 25), not the 90 I had estimated for an easy subset | Killed before spending; cost model revised: comparisons scale with the number of *informative* tasks |

## 7. Conclusions

**What reproduces.**

- Installation, data, and the full scoring pipeline run end-to-end on a laptop
  with no GPU: 48 verifier calls, 25 minutes, ≈ CNY 4.
- The **mechanism** reproduces directionally: on the three tasks where rollouts
  actually disagree, the verifier picks a passing trajectory every time
  (53.3% → 100%).
- The **corpus** is faithful: all 89 tasks aggregate to 78.7% mean reward, the
  paper's reported Bo5 Pass@1.

**What does not reproduce (and why).**

- The **size of the gap** (+7.1 pp in the paper): my +14 pp comes from 3
  informative tasks and has no statistical weight. The binding constraint is
  benchmark composition, not the method — 56% of the corpus (50/89) is all-pass,
  so a random or lexicographic subset has almost no headroom.
- **Absolute numbers**: different backbone (`deepseek-v4.1-flash` vs
  `deepseek-flash`), different subset, single seed, no repeated-seed variance.
- **The K ablation**: unidentifiable on a saturated subset (see §5).

**Three things I would tell the next person.**

1. **Check the score distribution before trusting any number.** If the client
   takes the wrong path (prefill vs sampled tags), the framework scores a
   silent 0.5 tie and your accuracy looks plausible but meaningless. Print the
   scores of one known-good triple first.
2. **Choose tasks by outcome variance, not by order.** Filter to tasks where the
   released trials disagree (`0 < passes < 5`); with 36 such tasks in this corpus,
   a 10-task swing subset is the smallest experiment that can actually detect the
   effect. Budget ≈ CNY 0.8 per task, so ≈ CNY 8 for a defensible run.
3. **Budget by comparisons, not by tasks.** A task with mixed outcomes costs
   6× a task that always passes (30 comparisons vs 0). Two "similar" subsets can
   differ by an order of magnitude in cost — I learned this the expensive way
   (§6, item 6).

**Reproducibility verdict.** The *framework* is reproducible: install, data,
scoring and cost accounting all behave as documented, and the provider layer is
the only genuinely fragile part. The *headline number* is not reproducible within
a student compute budget, not because the method fails but because measuring a
+7 pp selection gain needs a swing-heavy benchmark and repeated seeds — which is
itself a finding about how reproducibility cost scales with statistical power.

---

### Appendix A — Commands

```bash
# environment
python3 -m venv .venv && ./.venv/bin/pip install -e .

# backend (.env)
OPENAI_BASE_URL=https://api.dspass.net/v1
OPENAI_API_KEY=***
VERIFIER_MODEL=deepseek-v4.1-flash

# one-shot sanity check of the score distribution
./.venv/bin/python scripts/smoke_proxy.py

# baseline (K=2), then modification (K=1) — see scripts/repro_all.sh
./.venv/bin/python scripts/run.py tb21_10 --pivots 1 --n-evaluations 2 --max-workers 3
./.venv/bin/python scripts/run.py tb21_10 --pivots 1 --n-evaluations 1 --max-workers 3
```

### Appendix B — Files added to the fork

| File | Purpose |
|---|---|
| `scripts/smoke_proxy.py` | Backend sanity check (logprob path) |
| `scripts/repro_all.sh` | Runs baseline then modification, saves both tables |
| `scripts/make_subsets.py` | Builds the two subsets as relative symlinks; `--verify` reports how many tasks are informative |
| `llm_verifier/fine_grained_reward.py` | `VERIFIER_MODEL` provider-compatibility patch (~6 lines) |
| `llm_verifier/benchmarks.py` | Two subset entries: `tb21_10`, `tb21_swing10` |
| `data/subsets/` | Task subsets, linked into the released corpus |
| `REPRODUCTION_NOTES.md` | Running notes and cost ledger |
| `THINKING_MAP.md` | What was reproduced vs. changed, mapped to each assignment requirement |
| `SCRIPT.md` | 15-minute presentation script |
| `results/tb21_K2.txt`, `results/tb21_K1.txt` | Raw result tables |
