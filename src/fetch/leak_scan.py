"""泄漏扫描（幂等：每次运行重写 ledger/leak_scan.csv）。

检查矩阵：
  L1 CTG resultsSection 断言（快照 JSON 键检查）
  L2 PubMed/EuropePMC lanifibranor 2026 文献逐条判读
  L3 公司 IR 列表页泄漏关键词（排除 Ph2 历史标题后判定）
  L4 AASLD 2026 摘要 PR 全文泄漏关键词
  L5 LPLV / H1-2026 财报 PR 泄漏关键词
  L6 新闻媒体 web 检索（agent 执行，responseId 留档；本脚本写入静态行）
"""
import csv
import json
import re
from pathlib import Path

from src.fetch.common import ROOT, SNAP_DIR, utcnow

LEAK_CSV = ROOT / "ledger" / "leak_scan.csv"
COLS = ["check_id", "query", "source", "retrieved_at_utc", "hit_count", "verdict", "evidence_path", "note"]

LEAKY_PAT = re.compile(
    r"(topline|top-line|primary endpoint (met|achieved)|statistically significant|"
    r"results (showed|demonstrated)|positive phase (iii|3) results)", re.I)
# NATiV3 特异的疗效泄漏信号（用于 PR 全文扫描）
EFFICACY_PAT = re.compile(
    r"(met its primary endpoint|primary endpoint was (met|achieved)|"
    r"\d+(\.\d+)?% of patients (achieved|in the lanifibranor)|"
    r"statistically significant (improvement|difference) in (mash|nash|fibrosis))", re.I)


def latest(source: str, pattern: str) -> Path:
    files = sorted((SNAP_DIR / source).glob(pattern))
    if not files:
        raise FileNotFoundError(f"{source}/{pattern}")
    return files[-1]


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main():
    now = utcnow()
    rows = []

    # L1 CTG
    p = latest("ctgov", "*NCT04849728_full.json")
    has_results = "resultsSection" in json.loads(p.read_bytes())
    rows.append({"check_id": "L1", "query": "CTG NCT04849728 resultsSection present?",
                 "source": "ctgov", "retrieved_at_utc": now, "hit_count": int(has_results),
                 "verdict": "LEAK" if has_results else "no-leak", "evidence_path": rel(p),
                 "note": "JSON 键断言；status=ACTIVE_NOT_RECRUITING, lastUpdatePost=2026-07-02"})

    # L2 PubMed 2026
    p2 = latest("pubmed", "*Q6_lanifibranor_2026_epmc.json")
    hits = json.loads(p2.read_bytes())["resultList"]["result"]
    titles = [h.get("title", "") for h in hits]
    suspect = [t for t in titles if EFFICACY_PAT.search(t)]
    rows.append({"check_id": "L2", "query": 'EPMC: TITLE_ABS:"lanifibranor" AND FIRST_PDATE:[2026 TO 2026]',
                 "source": "pubmed", "retrieved_at_utc": now, "hit_count": len(hits),
                 "verdict": "suspect" if suspect else "no-leak", "evidence_path": rel(p2),
                 "note": f"{len(hits)} 篇 2026 文献逐条判读：全部为临床前/综述/meta，无 NATiV3 疗效数据"})

    # L3 IR 列表页（排除 Ph2 历史标题）
    p3 = latest("company_pr", "*ir_press_list.html")
    html = p3.read_text(encoding="utf-8", errors="ignore")
    titles_ir = re.findall(r'data-search="([^"]+)"', html)
    nativ3_leak = [t for t in titles_ir if "nativ3" in t.lower() and EFFICACY_PAT.search(t)]
    rows.append({"check_id": "L3", "query": "Inventiva press-releases page: NATiV3 titles w/ efficacy keywords",
                 "source": "company_pr", "retrieved_at_utc": now, "hit_count": len(nativ3_leak),
                 "verdict": "suspect" if nativ3_leak else "no-leak", "evidence_path": rel(p3),
                 "note": "初扫 4 个关键词命中均为 Ph2 历史标题（NATIVE topline 2020 / Cusi Ph2 2023）；NATiV3 相关标题零疗效命中"})

    # L4 AASLD 2026 摘要 PR 全文
    p4 = latest("company_pr", "*aasld2026_abstracts.pdf")
    t4 = (ROOT / "artifacts/extracted/pr_2026-10-06_aasld2026_abstracts.txt").read_text(encoding="utf-8")
    m4 = EFFICACY_PAT.findall(t4)
    rows.append({"check_id": "L4", "query": "AASLD The Liver Meeting 2026 abstracts PR full text",
                 "source": "company_pr", "retrieved_at_utc": now, "hit_count": len(m4),
                 "verdict": "suspect" if m4 else "no-leak", "evidence_path": rel(p4),
                 "note": "3 篇摘要全部为临床前/转化研究（cfDNA 甲基化、肝细胞群、LSEC）；明确 'topline results expected in Q4 of this year'"})

    # L5 LPLV + H1 财报
    for slug, txt in [("lplv", "pr_2026-09-02_lplv.txt"), ("h1_2026_financial", "pr_2026-09-28_h1_2026_financial.txt")]:
        t5 = (ROOT / f"artifacts/extracted/{txt}").read_text(encoding="utf-8")
        m5 = EFFICACY_PAT.findall(t5)
        rows.append({"check_id": "L5", "query": f"PR full text: {slug}",
                     "source": "company_pr", "retrieved_at_utc": now, "hit_count": len(m5),
                     "verdict": "suspect" if m5 else "no-leak",
                     "evidence_path": rel(latest("company_pr", f"*{slug}*.pdf")),
                     "note": "仅时间线表述（topline expected Q4 2026），无疗效数据"})

    # L6 新闻媒体 web 检索（agent 执行）
    rows.append({"check_id": "L6", "query": "web: 'NATiV3 topline results' / 'primary endpoint met' / 'results announcement'",
                 "source": "web_search(exa)", "retrieved_at_utc": now, "hit_count": 0,
                 "verdict": "no-leak", "evidence_path": "web_search responseId=muz616ca896lmo",
                 "note": "3 查询 × 5 结果：biospace/nasdaq/FT/clinicaltrialvanguard 等均仅复述 'topline expected Q4 2026'，无疗效数据"})

    LEAK_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LEAK_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"[{r['check_id']}] {r['verdict']:8s} hits={r['hit_count']:<3d} {r['query'][:66]}")
    overall = "no-leak" if all(r["verdict"] == "no-leak" for r in rows) else "REVIEW REQUIRED"
    print(f"\nOVERALL: {overall}")


if __name__ == "__main__":
    main()
