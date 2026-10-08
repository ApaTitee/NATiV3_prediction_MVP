"""D1: ClinicalTrials.gov API v2 — NCT04849728 全量记录。"""
from src.fetch.common import fetch_and_snapshot

STUDY_URL = "https://clinicaltrials.gov/api/v2/studies/NCT04849728"


def main():
    path, content = fetch_and_snapshot("ctgov", STUDY_URL, "NCT04849728_full")
    print(f"[ctgov] snapshot -> {path} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
