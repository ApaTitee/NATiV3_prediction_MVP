"""LLM 管线：R1 抽取 / R2 证据结构化 / R3 红队 / R4 审校。

纪律（执行手册 §5）：
- LLM 不产出绑定模型的数值先验；数值层（src/model/*）只读 evidence.csv，不读本目录任何产物；
- R2 的数值建议仅作为敏感性参考，报告中标注 "LLM 建议"；
- 所有输出为结构化 JSON；R4 引用校验由 verify_citations.py 程序化复核。
"""
import json
import os
import re

from dotenv import load_dotenv

from src.fetch.common import ROOT, utcnow
from src.llm.client import call

ART = ROOT / "artifacts"
OUT = ART / "llm"

SYS = (
    "You are a meticulous biostatistics/clinical-trials analyst assistant. "
    "Answer ONLY with valid JSON matching the requested schema. "
    "Every factual statement must carry a verbatim quote copied character-for-character from the provided source texts. "
    "If information is absent, say null — never invent numbers."
)


def _read(p) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _ctx_texts() -> dict[str, str]:
    ex = ART / "extracted"
    keys = ["pr_2026-09-02_lplv", "pr_2025-04-01_end_randomization",
            "pr_2026-10-06_aasld2026_abstracts", "pr_2026-03-30_fy2025_results",
            "deck_2026-06-03_jefferies", "pr_2020-06-15_native_topline"]
    return {k: _read(ex / f"{k}.txt")[:12000] for k in keys if (ex / f"{k}.txt").exists()}


def r1_extract(model: str, run_tag: str) -> dict:
    ctx = _ctx_texts()
    user = (
        "SOURCE TEXTS (company press releases / decks, ClinicalTrials.gov summary):\n"
        + "\n\n".join(f"===== {k} =====\n{v}" for k, v in ctx.items())
        + "\n\nTASK: Extract the NATiV3 (NCT04849728) trial design card as JSON with schema:\n"
        "{primary_endpoint: {definition_verbatim, type, timeframe}, arms: [], main_cohort_n, "
        "exploratory_cohort_n, randomization_ratio, stratification_factors: [], power_statement: {value, verbatim}, "
        "glp1_policy: {verbatim}, dropout_statement: {value, verbatim}, timeline: {lplv, topline}, "
        "statistical_methods_mentioned: []}\n"
        "Rules: every non-null field must include a 'verbatim' sub-field copied from the sources; "
        "if alpha/multiplicity/imputation/estimand are NOT stated, set them to null explicitly."
    )
    rec = call("R1", model, SYS, user, f"{run_tag}_r1")
    return json.loads(_json_block(rec["response"]))


def r2_evidence(model: str, run_tag: str) -> dict:
    evidence = _read(ART / "evidence.csv")
    card = _read(ART / "design_card.json")
    user = (
        "You are given an evidence ledger (CSV) and a verified design card (JSON) for the NATiV3 trial. "
        "The NUMERIC model is built solely from the ledger by deterministic code — your job is qualitative structuring ONLY.\n\n"
        f"===== design_card.json =====\n{card}\n\n===== evidence.csv =====\n{evidence}\n\n"
        "TASK — output JSON with schema:\n"
        "{pro_evidence: [{claim_id, argument, mechanism_link}],\n"
        " con_evidence: [{claim_id, argument, mechanism_link}],\n"
        " evidence_to_parameter_mapping: [{claim_id, parameter, qualitative_direction}],\n"
        " gaps: [{topic, why_it_matters, suggested_source}],\n"
        " llm_prior_suggestion: {delta_1200_pp_range, rationale}  # advisory only, will NOT enter the model\n}\n"
        "Rules: reference claim_ids only; no new numbers beyond the ledger; flag any ledger entry you believe is mis-tiered."
    )
    rec = call("R2", model, SYS, user, f"{run_tag}_r2")
    return json.loads(_json_block(rec["response"]))


def r3_redteam(model: str, run_tag: str) -> dict:
    card = _read(ART / "design_card.json")
    matrix = _read(ART / "model" / "assumption_matrix.csv")
    verdict = _read(ART / "model" / "verdict.json")
    evidence = _read(ART / "evidence.csv")
    user = (
        "You are the RED TEAM for a clinical-readout prediction. Attack the analysis. Do not be polite.\n\n"
        f"===== design_card =====\n{card}\n\n===== verdict =====\n{verdict}\n\n"
        f"===== assumption_matrix =====\n{matrix}\n\n===== evidence.csv =====\n{evidence}\n\n"
        "TASK — output JSON:\n"
        "{endpoint_misreading_risks: [{risk, severity, evidence}],\n"
        " missing_assumption_cells: [{cell, why_plausible, expected_direction_on_P}],\n"
        " prior_attacks: [{parameter, attack, suggested_fix}],\n"
        " leakage_vectors_not_covered: [{vector, likelihood}],\n"
        " strongest_bear_case: string,\n"
        " strongest_bull_case: string,\n"
        " verdict_challenge: {agree: boolean, reasoning}\n}\n"
        "Rules: every attack must cite a claim_id or a specific modeling choice; no generic statements."
    )
    rec = call("R3", model, SYS, user, f"{run_tag}_r3")
    return json.loads(_json_block(rec["response"]))


def r4_audit(model: str, run_tag: str) -> dict:
    report = _read(ROOT / "report" / "REPORT.md")
    evidence = _read(ART / "evidence.csv")
    user = (
        "Audit this prediction report against its evidence ledger.\n\n"
        f"===== REPORT.md =====\n{report[:22000]}\n\n===== evidence.csv =====\n{evidence}\n\n"
        "TASK — output JSON (keep each list to at most 5 highest-severity items; be concise; "
        "the response MUST be complete valid JSON):\n"
        "{numbers_without_source: [{value, location, severity}],\n"
        " claims_contradicting_ledger: [{claim, ledger_entry}],\n"
        " quotes_failing_verbatim_check: [{quote, should_be}],\n"
        " logic_gaps: [string],\n"
        " overall: {pass: boolean, summary}\n}\n"
        "Rules: flag ANY number in the report that cannot be traced to the ledger or to a model artifact; "
        "check the verdict logic against the frozen decision rule."
    )
    rec = call("R4", model, SYS, user, f"{run_tag}_r4", max_tokens=6000)
    return json.loads(_json_block(rec["response"]))


def _json_block(text: str) -> str:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON in response: {text[:300]}")
    return m.group(0)


def main():
    load_dotenv(ROOT / ".env")
    if not os.environ.get("LLM_API_KEY"):
        raise SystemExit("LLM_API_KEY missing — fill .env first (see .env.example)")
    fast = os.environ.get("LLM_MODEL_FAST", "deepseek-chat")
    strong = os.environ.get("LLM_MODEL_STRONG", "deepseek-chat")
    tag = utcnow().replace(":", "").replace("-", "")

    results = {
        "R1": r1_extract(fast, tag),
        "R2": r2_evidence(fast, tag),
        "R3": r3_redteam(strong, tag),
    }
    for k, v in results.items():
        (OUT / f"{tag}_{k.lower()}_parsed.json").write_text(
            json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    print("R1–R3 done. R4 runs after REPORT.md exists (make r4).")


def r4_only():
    load_dotenv(ROOT / ".env")
    strong = os.environ.get("LLM_MODEL_STRONG", "deepseek-chat")
    tag = utcnow().replace(":", "").replace("-", "")
    v = r4_audit(strong, tag)
    (OUT / f"{tag}_r4_parsed.json").write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    print("R4 done:", json.dumps(v.get("overall", {}), ensure_ascii=False))


if __name__ == "__main__":
    import sys
    r4_only() if len(sys.argv) > 1 and sys.argv[1] == "r4" else main()
