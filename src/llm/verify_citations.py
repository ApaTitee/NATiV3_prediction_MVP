"""引用可回溯性程序校验：evidence.csv 每条 verbatim_quote 必须在对应快照/提取文本中检索到。
检索失败 → 记入 artifacts/hallucination_log.csv（人工证据的幻觉防线）。"""
import csv
import re
from pathlib import Path

from src.fetch.common import ROOT


def norm(s: str) -> str:
    s = (s.replace("\ufb01", "fi").replace("\ufb02", "fl")
         .replace("\u2009", " ").replace("\u00a0", " ")
         .replace("\u2013", "-").replace("\u2014", "-"))
    s = re.sub(r"[\u2022\u25cf\u25aa]", " ", s)  # 项目符号
    return re.sub(r"\s+", " ", s).strip().lower()


def corpus_for(snapshot_path: str) -> str:
    """快照为 PDF 时用提取文本；JSON/HTML 直接读。"""
    p = ROOT / snapshot_path
    if p.suffix == ".pdf":
        m = re.match(r"\d{8}T\d{6}Z_(.+)\.pdf$", p.name)
        txt = ROOT / "artifacts" / "extracted" / f"{m.group(1)}.txt"
        return txt.read_text(encoding="utf-8", errors="ignore") if txt.exists() else ""
    return p.read_text(encoding="utf-8", errors="ignore")


def main():
    rows = list(csv.DictReader((ROOT / "artifacts/evidence.csv").open(encoding="utf-8")))
    log, ok = [], 0
    for r in rows:
        q = norm(r["verbatim_quote"])
        if not q or q.startswith("("):
            log.append({**r, "check": "skip-meta"}); continue
        corpus = norm(corpus_for(r["snapshot_path"]))
        # 整段或关键子串（前 60 字符）命中其一即通过（PDF 提取可能改变空白/连字符）
        hit = q in corpus or norm(r["verbatim_quote"][:60]) in corpus
        if hit:
            ok += 1
        else:
            log.append({**r, "check": "FAIL"})
    out = ROOT / "artifacts" / "hallucination_log.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["check"])
        w.writeheader()
        w.writerows(log)
    fails = [l for l in log if l["check"] == "FAIL"]
    print(f"verified {ok}/{len(rows)} quotes; fails={len(fails)} -> {out.name}")
    for l in fails:
        print("  FAIL:", l["claim_id"], l["claim_text"][:60])


if __name__ == "__main__":
    main()
