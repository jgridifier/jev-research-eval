#!/usr/bin/env python3
"""Build fixtures/stress_qc_rescored.json + stress_cases_with_traces.json from CoS lock."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# CoS QC lock — do not soften
COS: dict[str, tuple[str, str]] = {
    # human
    "S1_lit_survey_nowcasting_factors": (
        "fail",
        "Scholar search then blocked; no paper opened.",
    ),
    "S2_sarimax_exog_forecast_fix": (
        "fail",
        "Google CAPTCHA (/sorry/) blocked the SARIMAX exog forecast search.",
    ),
    "S3_sarimax_code_implementation": (
        "fail",
        "GitHub search loop; no SARIMAX+exog code reached.",
    ),
    "S4_nber_inflation_nowcast_wp": (
        "fail",
        "NBER papers listing blocked immediately with zero actions.",
    ),
    "S5_arxiv_state_space_survey": (
        "fail",
        "Model-call budget hit mid-search on arXiv; no abstract opened.",
    ),
    "S6_ops_aws_dpa_subprocessors": (
        "partial",
        "AWS compliance wander hit 60-action budget near DPA/programs.",
    ),
    "S7_ops_stripe_services_agreement_liability": (
        "pass",
        "Stripe Services Agreement landed with deep scroll — ops T&Cs bright spot.",
    ),
    "S8_edgar_10k_risk_factors_skim": (
        "partial",
        "Apple 10-K EDGAR list reached; budget before Risk Factors body.",
    ),
    "S9_expect_fail_multi_pdf_download_pack": (
        "fail_expected",
        "PDF pack expect-fail: Scholar search blocked before any download.",
    ),
    "S10_fred_compare_two_series_workflow": (
        "partial",
        "INDPRO only; Edit Graph loop / 60-action budget before second series.",
    ),
    # quant
    "QS1_multi_site_lit_survey": (
        "fail",
        "Model-call budget on arXiv before multi-site lit survey progressed.",
    ),
    "QS2_sarimax_papers_and_github": (
        "partial",
        "statsmodels user-guide reached; budget before GitHub+paper.",
    ),
    "QS3_ot_sinkhorn_implementation_hunt": (
        "partial",
        "POT MIT tab reached; Sinkhorn docs/Spelta incomplete.",
    ),
    "QS4_ragged_edge_nowcast_workflow": (
        "partial",
        "FRED GDP (+INDPRO path); no Philly Fed / eval cite.",
    ),
    "QS5_nber_realtime_gdp_path": (
        "fail",
        "Model-call budget on NBER before realtime GDP WP opened.",
    ),
    "QS6_nber_recession_vs_nowcast_disambiguation": (
        "partial",
        "Business-cycle FAQ only; no nowcast contrast page.",
    ),
    "QS7_ops_policy_compare_clauses": (
        "partial",
        "arXiv→CC BY only; NIH/POT clause compare incomplete.",
    ),
    "QS7b_corporate_tos_stripe_aws": (
        "partial",
        "Stripe SSA half completed; AWS half of corporate compare missing.",
    ),
    "QS8_cloud_tos_expect_friction": (
        "fail_expected",
        "SSRN homepage scroll; no ToS / anti-scraping clause (expect-fail).",
    ),
}

HUMAN_ORDER = [
    "S1_lit_survey_nowcasting_factors",
    "S2_sarimax_exog_forecast_fix",
    "S3_sarimax_code_implementation",
    "S4_nber_inflation_nowcast_wp",
    "S5_arxiv_state_space_survey",
    "S6_ops_aws_dpa_subprocessors",
    "S7_ops_stripe_services_agreement_liability",
    "S8_edgar_10k_risk_factors_skim",
    "S9_expect_fail_multi_pdf_download_pack",
    "S10_fred_compare_two_series_workflow",
]

QUANT_ORDER = [
    "QS1_multi_site_lit_survey",
    "QS2_sarimax_papers_and_github",
    "QS3_ot_sinkhorn_implementation_hunt",
    "QS4_ragged_edge_nowcast_workflow",
    "QS5_nber_realtime_gdp_path",
    "QS6_nber_recession_vs_nowcast_disambiguation",
    "QS7_ops_policy_compare_clauses",
    "QS7b_corporate_tos_stripe_aws",
    "QS8_cloud_tos_expect_friction",
]

DISPLAY = {
    "S1_lit_survey_nowcasting_factors": "Lit survey · nowcasting factors",
    "S2_sarimax_exog_forecast_fix": "SARIMAX exog forecast fix",
    "S3_sarimax_code_implementation": "SARIMAX+exog code on GitHub",
    "S4_nber_inflation_nowcast_wp": "NBER inflation nowcast WP",
    "S5_arxiv_state_space_survey": "arXiv state-space survey",
    "S6_ops_aws_dpa_subprocessors": "AWS DPA / subprocessors",
    "S7_ops_stripe_services_agreement_liability": "Stripe SSA liability",
    "S8_edgar_10k_risk_factors_skim": "EDGAR Apple 10-K Risk Factors",
    "S9_expect_fail_multi_pdf_download_pack": "Multi-PDF download pack",
    "S10_fred_compare_two_series_workflow": "FRED compare two series",
    "QS1_multi_site_lit_survey": "Multi-site lit survey",
    "QS2_sarimax_papers_and_github": "SARIMAX papers + GitHub",
    "QS3_ot_sinkhorn_implementation_hunt": "OT Sinkhorn implementation",
    "QS4_ragged_edge_nowcast_workflow": "Ragged-edge nowcast workflow",
    "QS5_nber_realtime_gdp_path": "NBER realtime GDP path",
    "QS6_nber_recession_vs_nowcast_disambiguation": "Recession vs nowcast FAQ",
    "QS7_ops_policy_compare_clauses": "Ops policy clause compare",
    "QS7b_corporate_tos_stripe_aws": "Corporate ToS Stripe+AWS",
    "QS8_cloud_tos_expect_friction": "SSRN cloud ToS friction",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _budget_hit(obj: dict, grade_note: str) -> bool:
    err = str(obj.get("error") or "")
    if "budget" in err.lower():
        return True
    if "budget" in grade_note.lower():
        return True
    return False


def _history(obj: dict) -> list:
    h = obj.get("history")
    if isinstance(h, list) and h:
        return h
    t = obj.get("history_tail")
    return list(t) if isinstance(t, list) else []


def load_suite(results_dir: Path, order: list[str], suite: str) -> list[dict]:
    by_stem: dict[str, Path] = {}
    for f in results_dir.glob("*.json"):
        if f.name in ("summary.json", "qc_draft.json"):
            continue
        by_stem[f.stem] = f
        # also map by id inside file
    cases: list[dict] = []
    for cid in order:
        path = by_stem.get(cid)
        if not path:
            # fuzzy: startswith
            matches = [p for stem, p in by_stem.items() if stem == cid or stem.startswith(cid)]
            if not matches:
                raise FileNotFoundError(f"Missing result for {cid} in {results_dir}")
            path = matches[0]
        obj = _load(path)
        grade, note = COS[cid]
        hist = _history(obj)
        bh = _budget_hit(obj, note)
        cases.append(
            {
                "id": cid,
                "suite": suite,
                "display": DISPLAY.get(cid, cid),
                "tier": obj.get("tier"),
                "why": (obj.get("why") or "").strip(),
                "url": obj.get("url") or "",
                "goal": obj.get("goal") or "",
                "expect_fail": bool(obj.get("expect_fail")),
                "ok": obj.get("ok"),
                "status": obj.get("status"),
                "final_url": obj.get("final_url"),
                "actions": obj.get("actions") if obj.get("actions") is not None else len(hist),
                "error": obj.get("error"),
                "matched": obj.get("matched"),
                "elapsed_ms_agent": obj.get("elapsed_ms_agent"),
                "wall_s": obj.get("wall_s"),
                "exit_code": obj.get("exit_code"),
                "history": hist,
                "history_tail": hist[-5:] if hist else [],
                "qc_grade": grade,
                "qc_note": note,
                "budget_hit": bh,
                "trace_source": "stress_run",
            }
        )
    return cases


def count_grades(cases: list[dict]) -> dict[str, int]:
    keys = ("pass", "partial", "fail", "fail_expected")
    out = {k: 0 for k in keys}
    for c in cases:
        g = c.get("qc_grade")
        if g in out:
            out[g] += 1
    return out


def main() -> int:
    human = load_suite(
        ROOT / "results" / "run_stress_human_v1",
        HUMAN_ORDER,
        "stress_human_workflows_v1",
    )
    quant = load_suite(
        ROOT / "results" / "run_stress_quant_v2",
        QUANT_ORDER,
        "stress_quant_v2",
    )
    all_cases = human + quant
    human_counts = count_grades(human)
    quant_counts = count_grades(quant)
    total_counts = count_grades(all_cases)

    qc = {
        "title": "Jev stress-eval QC (CoS lock)",
        "session": "2026-09-17",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "grader": "cos_lock",
        "executive_finding": (
            "Multi-hop human workflows mostly fail on CAPTCHA/budget; "
            "Stripe SSA is the bright spot for ops review."
        ),
        "suites": {
            "stress_human_workflows_v1": {
                "label": "Human stress (S1–S10)",
                "results_dir": "results/run_stress_human_v1",
                "counts": human_counts,
                "n": len(human),
                "budget_hits": sum(1 for c in human if c["budget_hit"]),
            },
            "stress_quant_v2": {
                "label": "Quant stress (QS1–QS8+QS7b)",
                "results_dir": "results/run_stress_quant_v2",
                "counts": quant_counts,
                "n": len(quant),
                "budget_hits": sum(1 for c in quant if c["budget_hit"]),
            },
        },
        "counts": total_counts,
        "qc_pass": total_counts["pass"],
        "qc_partial": total_counts["partial"],
        "qc_fail": total_counts["fail"],
        "qc_fail_expected": total_counts["fail_expected"],
        "results": all_cases,
    }

    slim = {
        "session": "2026-09-17",
        "title": "Jev Ultrafast stress-eval traces",
        "executive_finding": qc["executive_finding"],
        "scorecard": {
            "qc_pass": total_counts["pass"],
            "qc_partial": total_counts["partial"],
            "qc_fail": total_counts["fail"],
            "qc_fail_expected": total_counts["fail_expected"],
            "human": human_counts,
            "quant": quant_counts,
        },
        "cases": [
            {
                "id": c["id"],
                "suite": c["suite"],
                "display": c["display"],
                "tier": c["tier"],
                "expect_fail": c["expect_fail"],
                "why": c["why"],
                "url": c["url"],
                "goal": c["goal"],
                "ok": c["ok"],
                "final_url": c["final_url"],
                "status": c["status"],
                "elapsed_ms_agent": c["elapsed_ms_agent"],
                "actions": c["actions"],
                "error": c["error"],
                "matched": c["matched"],
                "wall_s": c["wall_s"],
                "qc_grade": c["qc_grade"],
                "qc_note": c["qc_note"],
                "budget_hit": c["budget_hit"],
                "history": c["history"],
                "history_tail": c["history_tail"],
                "trace_source": c["trace_source"],
            }
            for c in all_cases
        ],
    }

    out_qc = ROOT / "fixtures" / "stress_qc_rescored.json"
    out_slim = ROOT / "fixtures" / "stress_cases_with_traces.json"
    out_qc.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    out_slim.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_qc} ({out_qc.stat().st_size} bytes)")
    print(f"Wrote {out_slim} ({out_slim.stat().st_size} bytes)")
    print(f"Human counts: {human_counts}")
    print(f"Quant counts: {quant_counts}")
    print(f"Total: {total_counts}  budget_hits={sum(1 for c in all_cases if c['budget_hit'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
