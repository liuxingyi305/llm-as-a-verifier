# Reproducing LLM-as-a-Verifier on a Terminal-Bench 2.1 Subset

**FTEC5660 — Reproducibility Work**

Name: _[fill in]_ · Student ID: _[fill in]_ · 10 November 2026

Repo: `llm-as-a-verifier/llm-as-a-verifier` v0.3.0 · My fork: <https://github.com/liuxingyi305/llm-as-a-verifier> (branch `repro`)
Install/run steps and the list of added files: the fork's README.

---

## 1. What I tried to reproduce

`llm-verifier` ranks N agent trajectories and returns the best one. Two
mechanisms do the work: the reward is the **expectation over the logprob
distribution** of a 20-point score token (A–T), not the sampled letter; and
ranking runs as a **probabilistic pivot tournament**, `O(N·k)` instead of
`O(N²)`.

The claim under test is one line: **selecting among rollouts that already exist
beats taking a single rollout, and approaches the oracle.** On Terminal-Bench 2.1
(self-verification, mini-swe-agent, 5 trials/task) the paper reports:

| | Pass@1 | Verifier | Oracle |
|---|---|---|---|
| Best-of-3 | 79.4% | 86.5% ± 1.1% | 92.1% |
| Best-of-5 | 78.7% | 88.0% ± 0.6% | 96.6% |

No new rollouts are generated, so the only thing that can move the number is
the selection mechanism.

## 2. Setup

| Item | Detail |
|---|---|
| Environment | macOS (Apple silicon), Python 3.13, **CPU only** |
| Data | Shipped with the repo: 89 tasks × 5 released trajectories, reward held out |
| Backend | DeepSeek-compatible relay, `deepseek-v4.1-flash`; CNY 2 / M input (0.04 cached), 8 / M output |
| Config | `pivots=1`, `n_evaluations=2`, `seed=0`, criteria: specification, output_match, error_signals |
| Cost / time | ≈ CNY 10 total; baseline = 48 verifier calls, ~25 min at `--max-workers 3` |

**Model substitution (documented, not the modification).** The paper verifies
with `deepseek-flash` on DeepSeek's own endpoint; I used a relay. Decoding
parameters are fixed by the framework (temperature 1.0 for score tags,
`max_tokens` from `DEEPSEEK_MAX_TOKENS`), prompts unchanged. **Results are
therefore not directly comparable to the paper** — what is comparable is the
direction and size of the verifier-vs-Pass@1 gap.

## 3. Target and metrics

Pass@1 = mean reward of the released trials; Verifier = reward of the trajectory
the tournament selects; Oracle = reward of the best available trajectory.
9.0 comparisons per task.

**Scope: 10 of 89 tasks**, taken in lexicographic order (assignment §2 permits
one benchmark, one table row). The verifier only sees `problem` and `trace`.

## 4. Results

```
K=2  pivots=1  seed=0   tasks=10  swing=3  N(trials)=5
Pass@1                 8.60/10    86.0%
LLM-as-a-Verifier        10/10   100.0%
Oracle (Bo5)             10/10   100.0%
```

| | Paper (89 tasks) | Mine (10 tasks) |
|---|---|---|
| Pass@1 | 79.4 / 78.7% | **86.0%** |
| Verifier | 86.5 / 88.0% | **100%** |
| Oracle | 92.1 / 96.6% | **100%** |
| Verifier − Pass@1 | +7.1 / +9.3 pp | **+14.0 pp** |

**That +14 pp is not a replication, and the reason is composition.** The 10
tasks split into **7 all-pass, 3 swing, 0 all-fail**. On the 7, every method
scores 100% by construction. Only the 3 carry information:

| Slice | Pass@1 | Verifier |
|---|---|---|
| All 10 | 86.0% | 100% |
| **3 swing tasks** | **53.3% (8/15)** | **100% (3/3)** |

The verifier recovered every informative task — the direction the paper reports
— but n = 3, so this is an existence proof, not a replication.

**The data itself checks out.** Over all 89 tasks the released trajectories give
**50 all-pass / 36 swing / 3 all-fail, reward rate 78.7%** — exactly the paper's
reported Bo5 Pass@1. The corpus is faithful; the missing gap is a property of my
sample, not of the data.

**Cost structure (measured).** 64k input tokens per comparison, **92.7% served
from prefix cache**; 429k output tokens of which **98.6% is reasoning**. Input is
big but cheap; the bill is set by how long the verifier thinks, not by context
length. ≈ CNY 0.083/call, 0.40/task.

## 5. Modification: K = 2 → 1

The paper's third mechanism is "scale repeated evaluation" — score each criterion
K times and average to cut variance. I halved K and froze everything else: same
tasks, criteria, `pivots=1`, `seed=0`, same model and backend.

| Config | Pass@1 | Verifier | Additional calls | Identical selection? |
|---|---|---|---|---|
| K = 2 | 86.0% | 100% | 48 | — |
| K = 1 | 86.0% | 100% | **0** | **yes, 10/10** |

Zero calls because the score cache is keyed by `criterion | task | pair |
repetition-index`: K=1 only asks for repetition 0, which the K=2 sweep already
computed. So the modification re-derived the ranking from cached scores for free.

**This is a non-identification, not a null result.** With 7 of 10 tasks passing
in every trial, a ranking change cannot surface even if repetition variance
exists. The honest claim is "K's effect is not identifiable on this subset" —
testing it needs a subset centred near 50% Pass@1, which I costed at ≈ CNY 9
for 6 swing tasks and did not run, to stay inside the compute budget.

## 6. Debug diary

| # | Symptom | Cause → fix |
|---|---|---|
| 1 | `401` on the first key | Key was issued by a relay, not DeepSeek; repointed `OPENAI_BASE_URL` |
| 2 | **All scores silently `0.5`** | The relay's URL isn't DeepSeek's, so the client took the generic OpenAI path, which reads the score by vLLM *prefill* (`continue_final_message`, `structured_outputs`). The relay accepts and ignores both, so no distribution returns and every tie resolves to 0.5 — no error, plausible accuracy. Fixed with an opt-in `VERIFIER_MODEL` that selects the DeepSeek path (model emits the tag). Verified `[0.5,0.5,0.5]` → `[0.6733,0.3460,0.4230]`, correct candidate |
| 3 | `DEEPSEEK_EFFORT=off` changes nothing | Relay accepts `thinking` and still returns reasoning → not a cost lever; reduced scope instead |
| 4 | 10 errors in the first sweep | Concurrency 8 tripped rate limits → `--max-workers 3`, 0 errors in 48 calls |
| 5 | Crash at 92%, no output | Local temp-dir restriction, not a framework bug → `TMPDIR` inside the workspace; cache made the re-run nearly free |
| 6 | Aborted a swing-subset run at 0/300 jobs | A swing subset makes the loader score **all 5 trials** (300 comparisons ≈ CNY 25), not the 90 I budgeted. Killed at zero spend — the estimate was low by 3× |

## 7. Conclusions

**What reproduces.** Install, data and scoring run end-to-end on a laptop, no
GPU: 48 calls, 25 minutes, ≈ CNY 4. The mechanism reproduces directionally —
53.3% → 100% on the three tasks where rollouts actually disagree. And the corpus
is faithful: 78.7% mean reward over 89 tasks, the paper's Bo5 Pass@1.

**What does not, and why.** The *size* of the gap does not: my +14 pp rests on 3
tasks and has no statistical weight. The binding constraint is benchmark
composition, not the method — 50 of 89 tasks are all-pass, so a lexicographic
subset has almost no headroom. Absolute numbers also differ (different backbone,
single seed, no run-to-run variance).

**Verdict.** The framework is reproducible; the provider layer is its fragile
part. The headline number is not reproducible on a student budget — not because
the method fails, but because measuring a 7-point selection gain needs a
swing-heavy benchmark and repeated seeds. That gap between "the code runs" and
"the claim is testable" is the result of this exercise.

**Three things to tell the next person.** (1) Print the scores of one known-good
triple before trusting any number — the wrong code path fails silently at 0.5.
(2) Choose tasks by outcome variance, not by order; 36 swing tasks exist, and 10
of them is the smallest experiment that can detect the effect (≈ CNY 8).
(3) Budget by comparisons, not tasks — an all-pass task needs none; a
mixed-outcome one needs all 5 trials scored.
