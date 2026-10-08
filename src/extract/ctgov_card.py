"""解析 CTG 快照 -> artifacts/design_card_raw.json（机械抽取，供人工核对）。"""
import json
from pathlib import Path

from src.fetch.common import ROOT


def main():
    p = sorted((ROOT / "data/snapshots/ctgov").glob("*NCT04849728_full.json"))[-1]
    s = json.loads(p.read_bytes())
    ps = s["protocolSection"]
    idm = ps["identificationModule"]
    status = ps["statusModule"]
    design = ps["designModule"]
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})
    elig = ps.get("eligibilityModule", {})

    card = {
        "_snapshot": str(p.relative_to(ROOT)),
        "nctId": idm.get("nctId"),
        "briefTitle": idm.get("briefTitle"),
        "overallStatus": status.get("overallStatus"),
        "startDate": status.get("startDateStruct"),
        "primaryCompletionDate": status.get("primaryCompletionDateStruct"),
        "completionDate": status.get("completionDateStruct"),
        "lastUpdatePostDate": status.get("lastUpdatePostDateStruct"),
        "hasResultsSection": "resultsSection" in s,
        "phases": design.get("phases"),
        "enrollmentInfo": design.get("enrollmentInfo"),
        "allocation": design.get("designInfo", {}).get("allocation"),
        "masking": design.get("designInfo", {}).get("maskingInfo"),
        "primaryOutcomes": outcomes.get("primaryOutcomes", []),
        "secondaryOutcomes": [o.get("measure") for o in outcomes.get("secondaryOutcomes", [])],
        "arms": [
            {"label": a.get("label"), "type": a.get("type"),
             "description": (a.get("description") or "")[:300]}
            for a in arms.get("armGroups", [])
        ],
        "eligibilityCriteria_head": (elig.get("eligibilityCriteria") or "")[:3000],
        "sex": elig.get("sex"), "minimumAge": elig.get("minimumAge"),
    }
    out = ROOT / "artifacts" / "design_card_raw.json"
    out.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: card[k] for k in
                      ["overallStatus", "lastUpdatePostDate", "hasResultsSection",
                       "primaryCompletionDate", "enrollmentInfo", "allocation"]},
                     indent=2, ensure_ascii=False))
    print("\n--- PRIMARY OUTCOMES (verbatim) ---")
    for o in card["primaryOutcomes"]:
        print("*", o.get("measure"), "|", o.get("timeFrame"))
        print("  ", (o.get("description") or "").replace("\n", " ")[:600])
    print("\n--- SECONDARY (first 15) ---")
    for t in card["secondaryOutcomes"][:15]:
        print("-", t)
    print("\n--- ARMS ---")
    for a in card["arms"]:
        print("-", a["label"], "|", a["type"])


if __name__ == "__main__":
    main()
