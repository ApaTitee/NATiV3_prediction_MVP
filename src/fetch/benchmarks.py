"""关键文献定点抓取：EPMC 摘要 + PMC 全文 XML（可核验段落引用用）。"""
from src.fetch.common import fetch_and_snapshot

# (slug, url) —— 全部 Europe PMC / NCBI 官方端点
URLS = {
    # NATIVE Ph2b, NEJM 2021
    "native_nejm2021_abstract": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:34670042&format=json&resultType=core",
    # MAESTRO-NASH 主结果（NEJM 2024, Harrison）——用题名检索定位
    "maestro_nash_main": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22Resmetirom%20for%20nonalcoholic%20steatohepatitis%20with%20liver%20fibrosis%22&format=json&resultType=core",
    # ESSENCE 主结果（NEJM 2025, Sanyal）
    "essence_main": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE_ABS:%22Phase%203%20Trial%20of%20Semaglutide%22%20AND%20TITLE_ABS:%22steatohepatitis%22&format=json&resultType=core",
    # 安慰剂率 meta 2026
    "placebo_rates_meta_2026": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:41076041&format=json&resultType=core",
    # MAESTRO vs ESSENCE 对比（OA 全文）
    "maestro_vs_essence_fulltext": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12879040/fullTextXML",
    # RESOLVE-IT elafibranor Ph3 结果
    "resolve_it_results": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE_ABS:%22elafibranor%22%20AND%20(TITLE_ABS:%22RESOLVE-IT%22%20OR%20(TITLE_ABS:%22phase%203%22%20AND%20TITLE_ABS:%22randomized%22))&format=json&resultType=core",
}


def main():
    for slug, url in URLS.items():
        ext = ".xml" if "fullTextXML" in url else ".json"
        try:
            path, content = fetch_and_snapshot("pubmed", url, slug, ext=ext, timeout=90)
            print(f"[bench] {slug}: {len(content)} bytes -> {path.name}")
        except Exception as e:
            print(f"[bench] {slug}: FAILED {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
