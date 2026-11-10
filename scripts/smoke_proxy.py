"""Smoke test: can a DeepSeek-compatible proxy back the verifier?

Builds an OpenAI client against OPENAI_BASE_URL, tags it with the DeepSeek
call path (score tags sampled by the model, no vLLM prefill), and runs a
single best-of-3 selection. Prints the scores and the billed token usage.

Usage:
    python scripts/smoke_proxy.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from openai import OpenAI

import llm_verifier
from llm_verifier.fine_grained_reward import load_dotenv

load_dotenv(ROOT)

BASE_URL = os.environ["OPENAI_BASE_URL"]
MODEL = os.environ.get("VERIFIER_MODEL", "deepseek-v4.1-flash")

client = OpenAI(base_url=BASE_URL, api_key=os.environ["OPENAI_API_KEY"])
client._llm_verifier_model = MODEL
client._llm_verifier_deepseek = True

problem = "Write a function that reverses a string."
candidates = [
    "def rev(s): return s[::-1]",
    "def rev(s): return s",
    "def rev(s): return ''.join(sorted(s))",
]

result = llm_verifier.select(
    problem=problem,
    candidates=candidates,
    criteria={"Correctness": "Does the code actually reverse the string?"},
    model=MODEL,
    n_evaluations=2,
    pivots=1,
    client=client,
)

print("model:", MODEL)
print("picked index:", result.index, "(expected 0)")
print("scores:", [round(s, 4) for s in result.scores])
print("ranking:", result.ranking)
print("token usage:", llm_verifier.token_usage())
