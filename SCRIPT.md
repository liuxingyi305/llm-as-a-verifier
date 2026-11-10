# Zoom Presentation Script (≤15 min)

**Reproducing LLM-as-a-Verifier on a Terminal-Bench 2.1 Subset**
Recorded presentation, target 13:30–14:30 so there is slack.

Stage directions are in 【 】. Spoken lines are in plain text, written to be read
aloud — short sentences, no nested clauses.

---

## 0:00 – 1:30 | Opening: what I tried to reproduce

【Slide 1: title + the paper's table, big】

My project is LLM-as-a-Verifier, a framework that scores agent trajectories and
picks the best of N candidates.

The claim I tried to reproduce is one line: **a verifier can beat Pass@1 by
selecting among rollouts that already exist.**

The paper reports, on Terminal-Bench 2.1, Best-of-3: Pass@1 79.4%, verifier
86.5%, oracle 92.1%. Best-of-5: 78.7%, 88.0%, 96.6%.

So the gap I am testing is about seven to nine points.

I want to be clear about what this assignment is. It is not "is this paper
right". It is: what reproduces, what does not, and why.

---

## 1:30 – 4:00 | What the system actually does

【Slide 2: two mechanisms, one diagram each (or a simple sketch)】

Two mechanisms do the work, and neither is prompt engineering.

**First: the reward comes from logprobs, not from the sampled answer.**

The verifier is asked to put each candidate on a twenty-point letter scale, A
through T. The framework does not read the letter the model happened to emit. It
reads the whole probability distribution over those twenty letters, and takes the
expectation.

So if the model is 60% sure it is a B and 40% sure it is a C, you get a number
between B and C, not a coin flip. That is why two candidates that look equally
good can still be ranked.

**Second: the tournament is `O(N·k)`, not `O(N²)`.**

Ranking N candidates pairwise is quadratic. The framework runs a ring pass to
elect leaders, then pivot rounds against those leaders. `k` is the number of
pivots, and it is an explicit dial: more pivots, more comparisons, better ranking.

That dial is the thing I modified later.

---

## 4:00 – 6:30 | What I ran: setup and scope

【Slide 3: setup table — env, backend, data, cost】

The good news about this repo is that it ships the agent trajectories. I did not
generate a single rollout. Data: 89 Terminal-Bench tasks, five trajectories each,
with the ground-truth reward held out.

So every dollar goes to verification, which is exactly the mechanism under test.

My environment: macOS, Python 3.13, CPU only. No GPU.

One documented substitution: the paper verifies with `deepseek-flash` on
DeepSeek's endpoint. I used `deepseek-v4.1-flash` through a compatible relay.
Same API surface, different backbone, so **my absolute numbers are not directly
comparable to the paper**, and I say that in the report.

Scope: a ten-task subset. The assignment explicitly allows one benchmark, one
table row. Ten tasks, three criteria, one pivot, two repeated evaluations, single
seed.

Total spend: about ten Chinese yuan. A clean re-run is about seven.

---

## 6:30 – 9:00 | Results: the honest part

【Slide 4: the result table + the composition table】

Here is what came out.

Pass@1: 86.0%. Verifier: 100%. Oracle: 100%.

At first glance that looks like a win: plus fourteen points. It is not. Look at
the composition.

Seven of my ten tasks pass in all five trials. Those tasks are 100% for every
method by construction. Only three tasks actually disagree between trials.

On those three: Pass@1 is 53.3%, and the verifier picked a passing trajectory
three out of three times. That is the direction the paper reports, and it is a
large effect — but n equals three, so it is an existence proof, not a replication.

【pause】

One check that I think is more convincing than the headline. I computed the
statistics over all 89 tasks locally, for free. Fifty all-pass, thirty-six swing,
three all-fail. The overall reward rate is 78.7% — which is exactly the paper's
reported Best-of-5 Pass@1.

So the corpus is faithful. What I failed to reproduce is the *gap*, and that is a
property of my subset, not of the data.

---

## 9:00 – 11:00 | The modification

【Slide 5: K=2 vs K=1 table】

My modification is one variable: repeated evaluations, K, from two down to one.

The paper's third mechanism is "scale repeated evaluation" — score each criterion
K times and average, to reduce variance. I halved K and froze everything else.

The result is uninteresting in the way that matters: identical selection on all
ten tasks, at zero additional verifier calls.

Zero, because the score cache is keyed by criterion, task, comparison pair and
repetition index. K equals one only asks for repetition zero. Those scores were
already there.

So what is the correct conclusion? Not "K is useless". The correct conclusion is:
**on this subset, K's effect is not identifiable.** With seven of ten tasks
saturated, a ranking change cannot surface even if repetition variance exists.

To measure it properly you need a subset centred near fifty percent Pass@1. I
costed that at about nine yuan — six swing tasks, three trials each — and did not
run it, to stay inside the budget. I would rather report an honest
non-identification than a number I cannot defend.

---

## 11:00 – 12:30 | What broke, and what it taught me

【Slide 6: debug diary, three rows highlighted】

Three things broke, and one of them is the most useful finding in this project.

**First.** My key was rejected. It belonged to a relay, not to DeepSeek's
endpoint.

**Second, and this is the dangerous one.** After fixing the key, the scores came
back as 0.5, 0.5, 0.5 — a perfect tie, every candidate. The framework has two
paths for reading score tokens: one for vLLM, which prefills the tag, and one for
DeepSeek, which lets the model emit the tag itself. My relay is DeepSeek-shaped
but not DeepSeek's URL, so it took the vLLM path. The relay silently ignored the
prefill parameters, and every score collapsed to a tie.

That failure is silent. Accuracy looks plausible. Nothing errors. I only caught
it because I printed the scores of one known-good triple first.

**Third.** My cost model was wrong, and I caught it after starting a run. A task
where the trials disagree needs thirty comparisons. A task where they all pass
needs none. So two subsets with the same number of tasks can differ severalfold
in price. I had costed the swing subset at ninety comparisons; it was three
hundred. I stopped the run at zero progress and lost almost nothing.

---

## 12:30 – 14:00 | Lessons for the next person

【Slide 7: three recommendations】

Three things I would tell anyone doing this again.

**One: verify the score distribution before you trust a number.** Print one
comparison where you know the right answer. If it comes back as a tie, you are on
the wrong code path, and every downstream number is noise.

**Two: choose tasks by outcome variance, not by order.** Filter to tasks where
the released trials disagree. In this corpus there are 36 of them. Ten of those is
the smallest experiment that can actually detect the effect.

**Three: budget by comparisons, not by tasks.** That is the mistake I made.

And a note on cost structure, because it surprised me: a single comparison
ingests about sixty-four thousand input tokens — two full terminal transcripts —
but prefix caching absorbs over ninety-two percent of it. Ninety-eight point six
percent of the output tokens are reasoning. So the bill is set by how long the
verifier thinks, not by how much context you feed it. On this relay, disabling
thinking is not even an option — the parameter is accepted and ignored.

---

## 14:00 – 14:30 | Close

So, to answer the assignment's question directly.

The framework is reproducible: install, data, scoring, cost accounting all behave
as documented. The mechanism reproduces directionally where there is headroom to
measure it.

The headline number does not reproduce within a student budget — not because the
method fails, but because measuring a seven-point selection gain requires a
swing-heavy benchmark and repeated seeds.

That gap between "the code works" and "the claim is testable" is, I think, the
real result of this exercise. Thank you.

---

## Backup slide (only if asked)

- Full result tables: `results/tb21_K2.txt`, `results/tb21_K1.txt`
- Provider patch diff: `llm_verifier/fine_grained_reward.py` (`VERIFIER_MODEL`)
- Cost ledger: `REPRODUCTION_NOTES.md`
- Corpus statistics: 89 tasks = 50 all-pass / 36 swing / 3 all-fail, 78.7% reward rate

---

## Recording checklist

- [ ] Screen share the slides, not the terminal (terminal fonts are unreadable at 720p)
- [ ] Show the result table at 6:30 and the K table at 9:00 — those are the two moments that carry the grade
- [ ] Say the words "not directly comparable" once, near the model-substitution point
- [ ] Keep the [pause] at 7:30; it makes the honest framing land
- [ ] Stop at 14:30. Cut the cost-structure paragraph first if running long
