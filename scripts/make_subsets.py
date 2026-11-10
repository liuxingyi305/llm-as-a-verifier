"""Build the Terminal-Bench 2.1 task subsets used in the reproduction report.

The framework's loader expects a directory laid out like the released data:

    data/subsets/<subset>/mini-swe-agent_deepseek-v4-flash/<task>/...

Rather than copying ~56 MB of trajectories per subset, we link each task
directory back into the released corpus with a *relative* symlink, so the
checkout stays small and works on any machine after `git clone`.

Usage:
    python scripts/make_subsets.py            # build both subsets
    python scripts/make_subsets.py --verify   # check links resolve, print stats

Subsets
-------
tb21_10       first 10 task directories in lexicographic order (the subset the
              report's baseline actually ran on).
tb21_swing10  ten tasks whose released trials disagree (0 < passes < 5). This
              subset was costed but not run; see report section 5.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "data" / "terminal_bench_2.1_trajs" / "mini-swe-agent_deepseek-v4-flash"
SUBSETS = REPO / "data" / "subsets"

# Task names are pinned explicitly so the committed links stay reproducible even
# if the upstream corpus gains tasks later.
TB21_10 = [
    "adaptive-rejection-sampler",
    "bn-fit-modify",
    "break-filter-js-from-html",
    "build-cython-ext",
    "build-pmars",
    "build-pov-ray",
    "caffe-cifar-10",
    "cancel-async-tasks",
    "chess-best-move",
    "circuit-fibsqrt",
]

TB21_SWING10 = [
    "cancel-async-tasks",
    "chess-best-move",
    "db-wal-recovery",
    "dna-assembly",
    "dna-insert",
    "extract-elf",
    "extract-moves-from-video",
    "gcode-to-text",
    "gpt2-codegolf",
    "mailman",
]

SUBSETS_TO_BUILD = {"tb21_10": TB21_10, "tb21_swing10": TB21_SWING10}


def link_subset(name: str, tasks: list[str]) -> None:
    target_dir = SUBSETS / name / CORPUS.name
    target_dir.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        src = CORPUS / task
        if not src.is_dir():
            raise SystemExit(f"missing task in corpus: {src}")
        link = target_dir / task
        if link.is_symlink() or link.exists():
            link.unlink()
        # relative link: <subset>/<agent>/<task> -> ../../../terminal_bench_2.1_trajs/<agent>/<task>
        link.symlink_to(os.path.relpath(src, target_dir))
    print(f"{name}: linked {len(tasks)} tasks -> {target_dir.relative_to(REPO)}")


def _rewards(task_dir: Path) -> list[float]:
    """Released corpus stores one `<task>/<task>__<id>_trajectory.json` per trial."""
    rewards = []
    for path in sorted(task_dir.glob("*_trajectory.json")):
        rewards.append(float(json.loads(path.read_text()).get("reward", 0)))
    return rewards


def verify() -> None:
    for name, tasks in SUBSETS_TO_BUILD.items():
        root = SUBSETS / name / CORPUS.name
        broken = [t for t in tasks if not _rewards(root / t)]
        if broken:
            print(f"{name}: BROKEN -> {broken}")
            sys.exit(1)
        swing = 0
        for task in tasks:
            rewards = _rewards(root / task)
            passes = sum(1 for r in rewards if r > 0)
            if passes not in (0, len(rewards)):
                swing += 1
        print(f"{name}: ok, {len(tasks)} tasks readable, {swing} swing task(s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="only check existing links")
    args = ap.parse_args()
    if not CORPUS.is_dir():
        raise SystemExit(f"corpus not found: {CORPUS}")
    if not args.verify:
        for subset_name, subset_tasks in SUBSETS_TO_BUILD.items():
            link_subset(subset_name, subset_tasks)
    verify()
