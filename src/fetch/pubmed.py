"""D2: PubMed (E-utilities) + Europe PMC — 类内文献与基准检索。

检索清单（每条 esearch JSON + Europe PMC JSON 均快照）：
  Q1 lanifibranor 全部文献（NATIVE Ph2b、机制、biomarker）
  Q2 resmetirom MAESTRO-NASH
  Q3 semaglutide ESSENCE MASH
  Q4 elafibranor RESOLVE-IT
  Q5 NASH/MASH 安慰剂组织学应答 meta
  Q6 lanifibranor 2026 年文献（泄漏扫描的一部分）
"""
import json
import urllib.parse

from src.fetch.common import fetch_and_snapshot

QUERIES = {
    "Q1_lanifibranor": 'TITLE_ABS:"lanifibranor"',
    "Q2_resmetirom_maestro": 'TITLE_ABS:"resmetirom" AND (TITLE_ABS:"MAESTRO" OR TITLE_ABS:"NASH")',
    "Q3_semaglutide_essence": 'TITLE_ABS:"semaglutide" AND (TITLE_ABS:"ESSENCE" OR (TITLE_ABS:"NASH" AND TITLE_ABS:"phase 3"))',
    "Q4_elafibranor_resolve": 'TITLE_ABS:"elafibranor" AND (TITLE_ABS:"RESOLVE" OR TITLE_ABS:"NASH")',
    "Q5_placebo_meta": 'TITLE_ABS:"placebo" AND (TITLE_ABS:"NASH" OR TITLE_ABS:"MASH") AND PUB_TYPE:"Meta-Analysis" AND (TITLE_ABS:"histological" OR TITLE_ABS:"resolution" OR TITLE_ABS:"fibrosis" OR TITLE_ABS:"response")',
    "Q6_lanifibranor_2026": 'TITLE_ABS:"lanifibranor" AND FIRST_PDATE:[2026-01-01 TO 2026-12-31]',
}

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def main():
    for slug, q in QUERIES.items():
        enc = urllib.parse.quote(q)
        url2 = f"{EPMC}?query={enc}&format=json&pageSize=50&resultType=core"
        p2, c2 = fetch_and_snapshot("pubmed", url2, f"{slug}_epmc")
        hits = json.loads(c2).get("hitCount", 0)
        print(f"[epmc ] {slug}: {hits} hits -> {p2.name}")


if __name__ == "__main__":
    main()
