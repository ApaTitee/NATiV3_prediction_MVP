"""LLM 客户端：OpenAI 兼容接口 + 全量审计落盘 + 成本台账。

纪律：temperature=0；每次调用记录 model_id/prompt_sha256/response_sha256/usage/cost；
产物视为版本化中间产物（artifacts/llm/{role}/{run_id}.json），数值层只读这些文件。
"""
import csv
import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.fetch.common import ROOT, utcnow

LLM_DIR = ROOT / "artifacts" / "llm"
COST_CSV = ROOT / "ledger" / "cost_report.csv"
HARD_CAP_USD = 35.0


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _client() -> OpenAI:
    load_dotenv(ROOT / ".env")
    return OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])


def _pricing() -> dict:
    return json.loads((ROOT / "config" / "llm_pricing.json").read_text(encoding="utf-8"))


def cumulative_cost() -> float:
    if not COST_CSV.exists():
        return 0.0
    rows = list(csv.DictReader(COST_CSV.open(encoding="utf-8")))
    return sum(float(r["cost_usd"]) for r in rows if r.get("cost_usd"))


def call(role: str, model: str, system: str, user: str, run_id: str, max_tokens: int | None = None) -> dict:
    """单次调用 + 落盘 + 成本行。超过硬上限即抛异常中断。"""
    if cumulative_cost() >= HARD_CAP_USD:
        raise RuntimeError(f"hard cap ${HARD_CAP_USD} reached; aborting LLM calls")
    client = _client()
    t0 = time.time()
    kwargs = dict(model=model, temperature=0,
                  messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**kwargs)
    latency = time.time() - t0
    msg = resp.choices[0].message.content
    u = resp.usage
    pr = _pricing().get(model, {"in_per_mtok": 0, "in_cached_per_mtok": 0, "out_per_mtok": 0})
    cached = getattr(u, "prompt_cache_hit_tokens", 0) or 0
    cost = ((u.prompt_tokens - cached) * pr["in_per_mtok"] + cached * pr["in_cached_per_mtok"]
            + u.completion_tokens * pr["out_per_mtok"]) / 1e6

    out_dir = LLM_DIR / role
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "run_id": run_id, "role": role, "model_id": model, "ts_utc": utcnow(),
        "latency_s": round(latency, 2), "temperature": 0,
        "prompt_sha256": sha(system + "\n" + user), "response_sha256": sha(msg),
        "usage": {"in": u.prompt_tokens, "out": u.completion_tokens, "cached": cached},
        "cost_usd": round(cost, 5),
        "system": system, "user": user, "response": msg,
    }
    (out_dir / f"{run_id}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    cum = cumulative_cost() + cost
    with COST_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=["ts_utc", "run_id", "role", "model_id", "prompt_tokens",
                                      "completion_tokens", "cached_tokens", "unit_price_in",
                                      "unit_price_out", "cost_usd", "cumulative_usd", "note"]).writerow(
            {"ts_utc": rec["ts_utc"], "run_id": run_id, "role": role, "model_id": model,
             "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
             "cached_tokens": cached, "unit_price_in": pr["in_per_mtok"],
             "unit_price_out": pr["out_per_mtok"], "cost_usd": round(cost, 5),
             "cumulative_usd": round(cum, 4), "note": ""})
    print(f"[llm:{role}] {run_id} in={u.prompt_tokens} out={u.completion_tokens} "
          f"cached={cached} cost=${cost:.4f} cum=${cum:.3f}")
    return rec
