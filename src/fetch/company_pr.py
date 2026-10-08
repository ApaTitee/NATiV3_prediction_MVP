"""D3: 公司 IR / 新闻稿快照（B 级自利来源，入模需标注并做敏感性）。

globenewswire.com 从本网络不可达，改用 inventivapharma.com 官方 PDF 版本（同一文件）。
"""
from src.fetch.common import fetch_and_snapshot

BASE = "https://inventivapharma.com/wp-content/uploads"
DOCS = BASE + "/inventiva-documents"

URLS = {
    # —— 泄漏关键 + 时间线（2026） ——
    "pr_2026-10-06_aasld2026_abstracts": f"{BASE}/INVENTIVA-AALSD-Abstracts-PR-EN-10.6.2026-1.pdf",
    "pr_2026-09-02_lplv": f"{BASE}/Inventiva-PR-Inventiva-LVLP-EN-09-02-2026.pdf",
    "pr_2026-09-28_h1_2026_financial": f"{BASE}/Inventiva-PR-H1-2026-Financial-Results-EN-09-28-2026.pdf",
    "pr_2026-03-30_fy2025_results": f"{DOCS}/Inventiva-PR-Full-Year-results-2025-EN-03-30-2026-1.pdf",
    "deck_2026-02-05_guggenheim": f"{DOCS}/Inventiva-Guggenheim-Feb-2026-EN-02-05-2026.pdf",
    "pr_2026-05-13_easl2026_abstracts": f"{DOCS}/Inventiva-PR-Abstracts-EASL-2026-EN-05-13-2026.pdf",
    # —— 设计与执行（2024–2025） ——
    "pr_2025-04-01_end_randomization": f"{DOCS}/Inventiva-PR-End-of-Patient-Randomization-EN-04-01-2025.pdf",
    "pr_2025-10-07_aasld2025_abstracts": f"{DOCS}/Inventiva-PR-AASLD-Abstracts-2025-EN-10-07-2025-1.pdf",
    "pr_2024-10-30_5th_dmc": f"{DOCS}/Inventiva-PR-5th-DMC-NATiV3-EN-10-30-2024-1.pdf",
    "pr_2024-11-15_aasld_latebreaker_legend": f"{DOCS}/Inventiva-PR-Lanifibranor-AASLD-Late-Breaker-EN-11-15-2024.pdf",
    "pr_2025-04-24_biomarkers_cgh": f"{DOCS}/Inventiva-PR-Biomarkers-paper-CGH-EN-04-24-2025.pdf",
    # —— NATIVE Ph2b 公司口径（2020） ——
    "pr_2020-06-15_native_topline": f"{DOCS}/Inventiva-PR-NATIVE-top-line-results-EN-15062020.pdf",
}


def main():
    for slug, url in URLS.items():
        try:
            path, content = fetch_and_snapshot("company_pr", url, slug, ext=".pdf", timeout=120)
            print(f"[company] {slug}: {len(content)} bytes -> {path.name}")
        except Exception as e:
            print(f"[company] {slug}: FAILED {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
