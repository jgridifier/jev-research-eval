#!/usr/bin/env python3
"""Generate JEV_RESEARCH_NOTEBOOK_v2.html — R1–R11 + stress suites + viz.

Static HTML+CSS+JS viewer (no run button). Embeds:
  - fixtures/qc_rescored.json + cases_with_traces.json (R1–R11)
  - fixtures/stress_qc_rescored.json + stress_cases_with_traces.json (S* / QS*)

Coinbase DESIGN.md tokens; scarce #0052ff.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QC = ROOT / "fixtures" / "qc_rescored.json"
DEFAULT_CASES = ROOT / "fixtures" / "cases_with_traces.json"
DEFAULT_STRESS_QC = ROOT / "fixtures" / "stress_qc_rescored.json"
DEFAULT_STRESS_CASES = ROOT / "fixtures" / "stress_cases_with_traces.json"
DEFAULT_OUTPUT = ROOT / "fixtures" / "JEV_RESEARCH_NOTEBOOK_v2.html"

R_DISPLAY: dict[str, str] = {
    "R1_scholar_giannone_nowcast": "Google Scholar → Giannone–Reichlin–Small",
    "R2_doi_spelta_ot": "DOI → Spelta et al. (JRSS-A)",
    "R3_arxiv_search_sinkhorn": "arXiv → Sinkhorn divergences",
    "R4_fred_indpro": "FRED → INDPRO",
    "R5_edgar_company_search": "EDGAR → Apple filings",
    "R6_nber_wp_search": "NBER → Stock–Watson",
    "R7_crossref_doi_metadata": "Crossref → DOI record",
    "R8_wikipedia_disambiguation": "Wikipedia → Kalman filter",
    "R9_expect_fail_pdf_upload_replicate": "PDF upload / convert",
    "R10_expect_fail_scholar_cite_popup_maze": "Scholar → PDF download",
    "R11_expect_fail_nested_data_widget": "OWID chart → CSV",
}

R_ORDER = [
    "R2_doi_spelta_ot",
    "R4_fred_indpro",
    "R5_edgar_company_search",
    "R8_wikipedia_disambiguation",
    "R1_scholar_giannone_nowcast",
    "R3_arxiv_search_sinkhorn",
    "R6_nber_wp_search",
    "R7_crossref_doi_metadata",
    "R9_expect_fail_pdf_upload_replicate",
    "R10_expect_fail_scholar_cite_popup_maze",
    "R11_expect_fail_nested_data_widget",
]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_list(v: Any) -> list:
    return list(v) if isinstance(v, list) else []


def _pick_history(obj: dict) -> list:
    h = _as_list(obj.get("history"))
    if h:
        return h
    return _as_list(obj.get("history_tail"))


def _counts(cases: list[dict]) -> dict[str, int]:
    out = {"pass": 0, "partial": 0, "fail": 0, "fail_expected": 0}
    for c in cases:
        g = c.get("qc_grade")
        if g in out:
            out[g] += 1
    return out


def _norm_r(r: dict, slim_map: dict[str, dict]) -> dict:
    cid = r["id"]
    slim = slim_map.get(cid) or {}
    h = _pick_history(r)
    sh = _pick_history(slim)
    if len(sh) > len(h):
        h = sh
    return {
        "id": cid,
        "suite": "research_browser_v1",
        "section": "baseline",
        "display": R_DISPLAY.get(cid, cid),
        "tier": r.get("tier") or slim.get("tier"),
        "expect_fail": bool(r.get("expect_fail", slim.get("expect_fail"))),
        "why": r.get("why") or slim.get("why") or "",
        "url": r.get("url") or slim.get("url") or "",
        "goal": r.get("goal") or slim.get("goal") or "",
        "ok": r.get("ok") if r.get("ok") is not None else slim.get("ok"),
        "final_url": r.get("final_url") or slim.get("final_url"),
        "status": r.get("status") or slim.get("status"),
        "elapsed_ms_agent": r.get("elapsed_ms_agent")
        if r.get("elapsed_ms_agent") is not None
        else slim.get("elapsed_ms_agent"),
        "actions": r.get("actions")
        if r.get("actions") is not None
        else (slim.get("actions") if slim.get("actions") is not None else len(h)),
        "error": r.get("error") if r.get("error") is not None else slim.get("error"),
        "matched": r.get("matched") if r.get("matched") is not None else slim.get("matched"),
        "wall_s": r.get("wall_s") if r.get("wall_s") is not None else slim.get("wall_s"),
        "qc_grade": r.get("qc_grade") or slim.get("qc_grade"),
        "qc_note": r.get("qc_note") or slim.get("qc_note") or "",
        "budget_hit": bool(r.get("budget_hit") or slim.get("budget_hit")),
        "history": h,
        "history_tail": h[-5:] if h else [],
    }


def _norm_stress(c: dict) -> dict:
    h = _pick_history(c)
    suite = c.get("suite") or ""
    section = "stress_human" if suite.startswith("stress_human") else "stress_quant"
    return {
        "id": c["id"],
        "suite": suite,
        "section": section,
        "display": c.get("display") or c["id"],
        "tier": c.get("tier"),
        "expect_fail": bool(c.get("expect_fail")),
        "why": c.get("why") or "",
        "url": c.get("url") or "",
        "goal": c.get("goal") or "",
        "ok": c.get("ok"),
        "final_url": c.get("final_url"),
        "status": c.get("status"),
        "elapsed_ms_agent": c.get("elapsed_ms_agent"),
        "actions": c.get("actions") if c.get("actions") is not None else len(h),
        "error": c.get("error"),
        "matched": c.get("matched"),
        "wall_s": c.get("wall_s"),
        "qc_grade": c.get("qc_grade"),
        "qc_note": c.get("qc_note") or "",
        "budget_hit": bool(c.get("budget_hit")),
        "history": h,
        "history_tail": h[-5:] if h else [],
    }


def build_payload(
    qc: dict,
    cases_path: Path,
    stress_qc: dict,
    stress_cases_path: Path,
) -> dict:
    slim_map: dict[str, dict] = {}
    if cases_path.is_file():
        for c in (_load(cases_path).get("cases") or []):
            if c.get("id"):
                slim_map[c["id"]] = c

    by_id = {r["id"]: r for r in (qc.get("results") or [])}
    baseline: list[dict] = []
    for cid in R_ORDER:
        if cid in by_id:
            baseline.append(_norm_r(by_id.pop(cid), slim_map))
    for cid, r in sorted(by_id.items()):
        baseline.append(_norm_r(r, slim_map))

    stress_slim: dict[str, dict] = {}
    if stress_cases_path.is_file():
        for c in (_load(stress_cases_path).get("cases") or []):
            if c.get("id"):
                stress_slim[c["id"]] = c

    stress_raw = list(stress_qc.get("results") or [])
    # Prefer stress_qc (has CoS grades + full history); overlay slim if richer
    stress_cases: list[dict] = []
    seen: set[str] = set()
    for r in stress_raw:
        cid = r["id"]
        seen.add(cid)
        merged = dict(r)
        slim = stress_slim.get(cid)
        if slim:
            sh = _pick_history(slim)
            rh = _pick_history(merged)
            if len(sh) > len(rh):
                merged["history"] = sh
            for k, v in slim.items():
                if k in ("history", "history_tail"):
                    continue
                if merged.get(k) is None and v is not None:
                    merged[k] = v
        stress_cases.append(_norm_stress(merged))
    for cid, slim in stress_slim.items():
        if cid not in seen:
            stress_cases.append(_norm_stress(slim))

    human = [c for c in stress_cases if c["section"] == "stress_human"]
    quant = [c for c in stress_cases if c["section"] == "stress_quant"]

    def suite_block(label: str, cases: list[dict]) -> dict:
        return {
            "label": label,
            "counts": _counts(cases),
            "n": len(cases),
            "budget_hits": sum(1 for c in cases if c.get("budget_hit")),
            "action_counts": [
                {"id": c["id"], "display": c["display"], "actions": c.get("actions") or 0, "qc_grade": c.get("qc_grade")}
                for c in cases
            ],
        }

    finding = stress_qc.get("executive_finding") or (
        "Multi-hop human workflows mostly fail on CAPTCHA/budget; "
        "Stripe SSA is the bright spot for ops review."
    )

    return {
        "title": "Jev Ultrafast — Research Notebook v2",
        "subtitle": "Baseline R1–R11 plus human & quant stress suites with full traces",
        "session_date": "17 Sep 2026",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "executive_finding": finding,
        "methodology": (
            "Baseline suite: eleven goal-driven browser cases (R1–R11) with human QC. "
            "Stress suites: multi-hop human workflows (S1–S10) and quant/ops paths "
            "(QS1–QS8+QS7b) graded under a CoS lock. Auto run records status, actions, "
            "final URL, and full history; QC grades destination quality independently. "
            "This page is a static viewer — no run button. Regenerate with "
            "scripts/generate_notebook_v2.py."
        ),
        "scorecard_baseline": {
            "qc_pass": qc.get("qc_pass", _counts(baseline)["pass"]),
            "qc_partial": qc.get("qc_partial", _counts(baseline)["partial"]),
            "qc_fail": qc.get("qc_fail", _counts(baseline)["fail"]),
            "qc_fail_expected": qc.get("qc_fail_expected", _counts(baseline)["fail_expected"]),
        },
        "scorecard_stress": {
            "qc_pass": stress_qc.get("qc_pass", _counts(stress_cases)["pass"]),
            "qc_partial": stress_qc.get("qc_partial", _counts(stress_cases)["partial"]),
            "qc_fail": stress_qc.get("qc_fail", _counts(stress_cases)["fail"]),
            "qc_fail_expected": stress_qc.get(
                "qc_fail_expected", _counts(stress_cases)["fail_expected"]
            ),
        },
        "suites": {
            "baseline": suite_block("Baseline R1–R11", baseline),
            "stress_human": suite_block("Human stress S1–S10", human),
            "stress_quant": suite_block("Quant stress QS*", quant),
        },
        "cases": baseline + stress_cases,
    }


CSS = r"""
:root {
  --primary: #0052ff;
  --primary-active: #003ecc;
  --ink: #0a0b0d;
  --body: #5b616e;
  --muted: #7c828a;
  --muted-soft: #a8acb3;
  --hairline: #dee1e6;
  --hairline-soft: #eef0f3;
  --canvas: #ffffff;
  --surface-soft: #f7f7f7;
  --surface-strong: #eef0f3;
  --surface-dark: #0a0b0d;
  --surface-dark-elevated: #16181c;
  --on-dark: #ffffff;
  --on-dark-soft: #a8acb3;
  --up: #05b169;
  --down: #cf202f;
  --accent-yellow: #f4b000;
  --radius-xl: 24px;
  --radius-md: 12px;
  --radius-pill: 100px;
  --shadow: 0 4px 12px rgba(0,0,0,0.04);
  --max: 1120px;
  --tier-lit: #0052ff;
  --tier-model: #7c3aed;
  --tier-ops: #0d9488;
  --tier-nber: #c2410c;
  --tier-other: #7c828a;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, -apple-system, system-ui, sans-serif;
  font-size: 16px; font-weight: 400; line-height: 1.5;
  color: var(--ink); background: var(--surface-soft);
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }
code, .mono { font-family: "JetBrains Mono", ui-monospace, monospace; }

.topnav {
  height: 64px; background: var(--canvas);
  border-bottom: 1px solid var(--hairline);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; position: sticky; top: 0; z-index: 20;
}
.topnav .brand { font-weight: 600; font-size: 14px; letter-spacing: -0.01em; }
.topnav .brand span { color: var(--primary); }
.topnav nav { display: flex; gap: 16px; font-size: 13px; font-weight: 500; flex-wrap: wrap; }
.topnav nav a { color: var(--ink); }
.topnav nav a:hover { color: var(--primary); text-decoration: none; }

.hero {
  background: var(--surface-dark); color: var(--on-dark);
  padding: 72px 24px 64px;
}
.hero-inner { max-width: var(--max); margin: 0 auto; }
.hero .eyebrow {
  display: inline-block; background: var(--surface-dark-elevated);
  color: var(--on-dark-soft); font-size: 12px; font-weight: 600;
  padding: 4px 12px; border-radius: var(--radius-pill);
  margin-bottom: 20px; letter-spacing: 0.04em; text-transform: uppercase;
}
.hero h1 {
  font-size: clamp(32px, 5.5vw, 52px); font-weight: 400;
  line-height: 1.05; letter-spacing: -1.2px; margin: 0 0 16px;
}
.hero .lede { color: var(--on-dark-soft); font-size: 17px; max-width: 680px; margin: 0 0 28px; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 12px; }
.hero-chip {
  background: var(--surface-dark-elevated); border-radius: var(--radius-pill);
  padding: 8px 14px; font-size: 13px; color: var(--on-dark-soft);
}
.hero-chip strong { color: var(--on-dark); font-family: "JetBrains Mono", monospace; font-weight: 500; }

.finding {
  margin-top: 28px; padding: 20px 22px;
  background: var(--surface-dark-elevated);
  border-left: 3px solid var(--primary);
  border-radius: 0 12px 12px 0;
}
.finding .lab {
  font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--primary); margin-bottom: 6px;
}
.finding p { margin: 0; color: var(--on-dark); font-size: 16px; line-height: 1.45; max-width: 820px; }

.wrap { max-width: var(--max); margin: 0 auto; padding: 0 24px; }
.section { padding: 56px 0; }
.section.soft { background: var(--canvas); }
.section h2 {
  font-size: 28px; font-weight: 400; letter-spacing: -0.4px; margin: 0 0 8px;
}
.section .sub { color: var(--body); margin: 0 0 28px; max-width: 760px; }

.scoregrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 800px) { .scoregrid { grid-template-columns: repeat(2, 1fr); } }
.scorecard {
  background: var(--canvas); border: 1px solid var(--hairline);
  border-radius: var(--radius-xl); padding: 24px;
}
.scorecard .label {
  font-size: 12px; font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.scorecard .value {
  font-family: "JetBrains Mono", monospace; font-size: 36px;
  font-weight: 500; margin-top: 8px; letter-spacing: -1px;
}
.scorecard.pass .value { color: var(--up); }
.scorecard.partial .value { color: var(--accent-yellow); }
.scorecard.fail .value { color: var(--down); }
.scorecard.expected .value { color: var(--muted); }

.viz-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px;
}
@media (max-width: 860px) { .viz-grid { grid-template-columns: 1fr; } }
.viz-card {
  background: var(--canvas); border: 1px solid var(--hairline);
  border-radius: var(--radius-xl); padding: 22px 24px;
}
.viz-card h3 {
  margin: 0 0 16px; font-size: 15px; font-weight: 600; letter-spacing: -0.01em;
}
.mix-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.mix-row .name { width: 120px; font-size: 13px; font-weight: 600; flex-shrink: 0; }
.mix-bar {
  flex: 1; height: 18px; border-radius: 9px; overflow: hidden;
  background: var(--surface-strong); display: flex;
}
.mix-seg { height: 100%; min-width: 0; }
.mix-seg.pass { background: var(--up); }
.mix-seg.partial { background: var(--accent-yellow); }
.mix-seg.fail { background: var(--down); }
.mix-seg.fail_expected { background: var(--muted-soft); }
.mix-legend {
  display: flex; flex-wrap: wrap; gap: 14px; margin-top: 14px;
  font-size: 12px; color: var(--muted);
}
.mix-legend i {
  display: inline-block; width: 10px; height: 10px; border-radius: 3px;
  margin-right: 6px; vertical-align: middle;
}
.mix-legend i.pass { background: var(--up); }
.mix-legend i.partial { background: var(--accent-yellow); }
.mix-legend i.fail { background: var(--down); }
.mix-legend i.fail_expected { background: var(--muted-soft); }

.abar-row {
  display: grid; grid-template-columns: 150px 1fr 36px; gap: 10px;
  align-items: center; margin-bottom: 8px; font-size: 12px;
}
.abar-row .lab {
  font-family: "JetBrains Mono", monospace; color: var(--muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.abar-track {
  height: 10px; background: var(--surface-strong); border-radius: 5px; overflow: hidden;
}
.abar-fill {
  height: 100%; border-radius: 5px; background: var(--body);
  max-width: 100%;
}
.abar-fill.pass { background: var(--up); }
.abar-fill.partial { background: var(--accent-yellow); }
.abar-fill.fail { background: var(--down); }
.abar-fill.fail_expected { background: var(--muted-soft); }
.abar-n { font-family: "JetBrains Mono", monospace; text-align: right; color: var(--ink); }

.method {
  background: var(--surface-soft); border-radius: var(--radius-xl);
  padding: 24px 28px; color: var(--body); border: 1px solid var(--hairline-soft);
}

.toc {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;
}
.toc-card {
  display: block; background: var(--canvas); border: 1px solid var(--hairline);
  border-radius: 16px; padding: 18px 20px; color: inherit; text-decoration: none;
  transition: border-color .15s, box-shadow .15s;
}
.toc-card:hover { border-color: var(--primary); box-shadow: var(--shadow); text-decoration: none; }
.toc-card .row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
.toc-card .id { font-family: "JetBrains Mono", monospace; font-size: 12px; color: var(--muted); font-weight: 500; }
.toc-card .title { font-size: 15px; font-weight: 600; line-height: 1.3; }
.toc-card .meta { font-size: 13px; color: var(--muted); margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

.pill {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
  padding: 3px 10px; border-radius: var(--radius-pill);
  background: var(--surface-strong); color: var(--ink); white-space: nowrap;
}
.pill.pass { background: rgba(5,177,105,.12); color: var(--up); }
.pill.partial { background: rgba(244,176,0,.16); color: #a07800; }
.pill.fail { background: rgba(207,32,47,.12); color: var(--down); }
.pill.fail_expected { background: var(--surface-strong); color: var(--muted); }
.pill.expect { background: rgba(0,82,255,.08); color: var(--primary); }
.pill.budget {
  background: rgba(207,32,47,.10); color: var(--down);
  border: 1px solid rgba(207,32,47,.25);
}
.tier-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 600; padding: 3px 10px;
  border-radius: var(--radius-pill); background: var(--surface-strong); color: var(--ink);
}
.tier-chip .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--tier-other);
}
.tier-chip.lit_survey .dot, .tier-chip.writing_paper_survey .dot,
.tier-chip.paper_search .dot { background: var(--tier-lit); }
.tier-chip.model_fix .dot, .tier-chip.model_analysis .dot,
.tier-chip.model_building_workflow .dot, .tier-chip.sarimax_papers_and_code .dot { background: var(--tier-model); }
.tier-chip.ops_policy_review .dot, .tier-chip.terms_policy_ops_review .dot { background: var(--tier-ops); }
.tier-chip.nber_research .dot, .tier-chip.nber_realistic .dot { background: var(--tier-nber); }

.density {
  display: flex; flex-wrap: wrap; gap: 3px; margin-top: 10px;
}
.density .chip {
  width: 10px; height: 10px; border-radius: 2px;
  background: var(--muted-soft);
}
.density .chip.fill { background: var(--body); }
.density .chip.click { background: var(--primary); }
.density .chip.scroll { background: var(--tier-ops); }
.density .chip.nav { background: var(--tier-model); }

.case {
  background: var(--canvas); border: 1px solid var(--hairline);
  border-radius: var(--radius-xl); margin-bottom: 28px;
  overflow: hidden; scroll-margin-top: 80px;
}
.case-head {
  padding: 28px 32px 20px; border-bottom: 1px solid var(--hairline-soft);
  display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  align-items: flex-start;
}
.case-head h3 { margin: 0 0 6px; font-size: 22px; font-weight: 400; letter-spacing: -0.3px; }
.case-head .idline { font-family: "JetBrains Mono", monospace; font-size: 12px; color: var(--muted); }
.case-head .badges { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: flex-end; }
.case-body { padding: 24px 32px 32px; }
.case-body h4 {
  font-size: 13px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--muted); margin: 24px 0 10px;
}
.case-body h4:first-child { margin-top: 0; }
.why { color: var(--body); margin: 0; }
.protocol {
  background: var(--surface-soft); border-radius: var(--radius-md);
  padding: 16px 18px; font-size: 14px;
}
.protocol .lab {
  font-size: 11px; font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
}
.protocol .val { word-break: break-all; margin-bottom: 12px; }
.protocol .val:last-child { margin-bottom: 0; }
.protocol .goal { white-space: pre-wrap; color: var(--ink); }

.dials {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px;
}
.dial { background: var(--surface-soft); border-radius: 12px; padding: 14px 16px; }
.dial .lab {
  font-size: 11px; font-weight: 600; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.dial .val {
  font-family: "JetBrains Mono", monospace; font-size: 16px;
  font-weight: 500; margin-top: 4px; word-break: break-word;
}

.note {
  border-left: 3px solid var(--primary); padding: 10px 0 10px 16px;
  color: var(--body); font-size: 15px;
}

.trace-empty {
  background: var(--surface-soft); border-radius: var(--radius-md);
  padding: 28px 20px; text-align: center; color: var(--muted); font-size: 14px;
}
.trace-empty strong { display: block; color: var(--ink); font-weight: 600; margin-bottom: 4px; }

.timeline { list-style: none; margin: 0; padding: 0; }
.step {
  display: grid; grid-template-columns: 56px 1fr; gap: 12px;
  padding: 16px 0; border-bottom: 1px solid var(--hairline-soft);
}
.step:last-child { border-bottom: 0; }
.step-num {
  width: 40px; height: 40px; border-radius: 999px;
  background: var(--surface-strong);
  display: flex; align-items: center; justify-content: center;
  font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 500;
}
.step-body .action {
  font-weight: 600; font-size: 15px; margin-bottom: 6px;
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
.step-body .op {
  font-size: 11px; font-weight: 600; background: var(--surface-strong);
  padding: 2px 8px; border-radius: var(--radius-pill); color: var(--body);
  font-family: "JetBrains Mono", monospace;
}
.step-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 6px 14px; font-size: 13px; color: var(--body);
}
.step-grid .k {
  color: var(--muted); font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.03em;
}
.step-grid .v { font-family: "JetBrains Mono", monospace; font-size: 12px; word-break: break-all; }
.step-text {
  margin-top: 8px; background: var(--surface-dark); color: var(--on-dark);
  border-radius: 10px; padding: 10px 12px;
  font-family: "JetBrains Mono", monospace; font-size: 12px;
}
.step-text .label {
  color: var(--on-dark-soft); font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
  font-family: Inter, sans-serif;
}

.backtop { display: inline-block; margin-top: 12px; font-size: 13px; font-weight: 600; }
.section-tag {
  display: inline-block; font-size: 12px; font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
  color: var(--primary); margin-bottom: 8px;
}
.footer {
  padding: 48px 24px 64px; color: var(--muted); font-size: 13px; text-align: center;
}
.footer a { color: var(--body); }
@media (max-width: 640px) {
  .case-head, .case-body { padding-left: 20px; padding-right: 20px; }
  .step { grid-template-columns: 40px 1fr; }
}
"""

JS = r"""
(function () {
  const el = document.getElementById("notebook-data");
  if (!el) return;
  const data = JSON.parse(el.textContent);
  const $ = (sel, root) => (root || document).querySelector(sel);

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtMs(v) {
    if (v == null || v === "") return "—";
    const n = Number(v);
    if (Number.isNaN(n)) return esc(v);
    if (n >= 1000) return (n / 1000).toFixed(2) + "s";
    return Math.round(n) + "ms";
  }
  function gradeClass(g) { return g ? String(g) : ""; }
  function gradeLabel(g) {
    const map = { pass: "Pass", partial: "Partial", fail: "Miss", fail_expected: "Expected fail" };
    return map[g] || (g || "—");
  }
  function dial(lab, val) {
    return '<div class="dial"><div class="lab">' + esc(lab) +
      '</div><div class="val">' + esc(val) + "</div></div>";
  }
  function tierClass(t) {
    if (!t) return "other";
    const s = String(t);
    if (/lit|paper_search|writing_paper|scholar|arxiv/i.test(s)) return "lit_survey";
    if (/model|sarimax|fix|analysis|building/i.test(s)) return "model_fix";
    if (/ops|terms|policy|tos|edgar/i.test(s)) return "ops_policy";
    if (/nber/i.test(s)) return "nber";
    return s.replace(/[^a-z0-9_]+/gi, "_");
  }
  function densityHtml(hist) {
    if (!hist || !hist.length) return '<div class="density"><span class="chip" title="empty"></span></div>';
    const maxShow = 80;
    const steps = hist.slice(0, maxShow);
    let html = '<div class="density" title="' + hist.length + ' steps">';
    steps.forEach((s) => {
      const op = String(s.operation || s.kind || "").toUpperCase();
      let cls = "chip";
      if (op.indexOf("CLICK") >= 0) cls += " click";
      else if (op.indexOf("SCROLL") >= 0) cls += " scroll";
      else if (op.indexOf("GOTO") >= 0 || op.indexOf("NAV") >= 0) cls += " nav";
      else if (op.indexOf("TYPE") >= 0 || op.indexOf("FILL") >= 0) cls += " fill";
      html += '<span class="' + cls + '"></span>';
    });
    if (hist.length > maxShow) html += '<span class="chip" style="width:auto;padding:0 4px;font-size:9px">+' + (hist.length - maxShow) + "</span>";
    html += "</div>";
    return html;
  }

  $("#hero-date").textContent = data.session_date || "";
  $("#hero-gen").textContent = data.generated_at || "";
  $("#finding-text").textContent = data.executive_finding || "";
  $("#method-blurb").textContent = data.methodology || "";

  function fillScore(prefix, sc) {
    sc = sc || {};
    const map = { pass: "pass", partial: "partial", fail: "fail", expected: "fail_expected" };
    Object.keys(map).forEach((k) => {
      const node = $("#" + prefix + "-" + k);
      if (node) node.textContent = sc["qc_" + (k === "expected" ? "fail_expected" : k)] ?? "—";
    });
  }
  fillScore("scb", data.scorecard_baseline);
  fillScore("scs", data.scorecard_stress);

  // Outcome mix bars
  const mixRoot = $("#mix-bars");
  const suites = data.suites || {};
  Object.keys(suites).forEach((key) => {
    const s = suites[key];
    const c = s.counts || {};
    const n = Math.max(1, s.n || 1);
    const parts = ["pass", "partial", "fail", "fail_expected"];
    let segs = parts.map((p) => {
      const v = c[p] || 0;
      if (!v) return "";
      return '<div class="mix-seg ' + p + '" style="width:' + ((v / n) * 100).toFixed(2) + '%" title="' + p + ': ' + v + '"></div>';
    }).join("");
    const row = document.createElement("div");
    row.className = "mix-row";
    row.innerHTML = '<div class="name">' + esc(s.label || key) + '</div><div class="mix-bar">' + segs + "</div>";
    mixRoot.appendChild(row);
  });

  // Action-count bars (stress suites preferred; include all if small)
  const abar = $("#action-bars");
  const stressActions = []
    .concat((suites.stress_human && suites.stress_human.action_counts) || [])
    .concat((suites.stress_quant && suites.stress_quant.action_counts) || []);
  const maxA = Math.max(1, ...stressActions.map((x) => x.actions || 0), 1);
  stressActions.forEach((x) => {
    const pct = Math.round(((x.actions || 0) / maxA) * 100);
    const row = document.createElement("div");
    row.className = "abar-row";
    row.innerHTML =
      '<div class="lab" title="' + esc(x.id) + '">' + esc(x.id.split("_")[0]) + "</div>" +
      '<div class="abar-track"><div class="abar-fill ' + gradeClass(x.qc_grade) + '" style="width:' + pct + '%"></div></div>' +
      '<div class="abar-n">' + esc(x.actions) + "</div>";
    abar.appendChild(row);
  });

  function renderToc(cases, tocEl) {
    cases.forEach((c) => {
      const nSteps = (c.history || []).length;
      const card = document.createElement("a");
      card.className = "toc-card";
      card.href = "#case-" + c.id;
      card.innerHTML =
        '<div class="row"><span class="id">' + esc(c.id) + "</span>" +
        '<span class="pill ' + gradeClass(c.qc_grade) + '">' + esc(gradeLabel(c.qc_grade)) + "</span></div>" +
        '<div class="title">' + esc(c.display || c.id) + "</div>" +
        '<div class="meta">' +
        (c.budget_hit ? '<span class="pill budget">budget hit</span>' : "") +
        (c.expect_fail ? '<span class="pill expect">expect fail</span>' : "") +
        '<span class="tier-chip ' + esc(tierClass(c.tier)) + '"><span class="dot"></span>' + esc(c.tier || "—") + "</span>" +
        "<span>" + nSteps + " steps</span>" +
        "<span>" + fmtMs(c.elapsed_ms_agent) + "</span></div>" +
        densityHtml(c.history);
      tocEl.appendChild(card);
    });
  }

  const all = data.cases || [];
  const baseline = all.filter((c) => c.section === "baseline");
  const human = all.filter((c) => c.section === "stress_human");
  const quant = all.filter((c) => c.section === "stress_quant");
  renderToc(baseline, $("#toc-baseline-list"));
  renderToc(human, $("#toc-human"));
  renderToc(quant, $("#toc-quant"));

  function renderStep(s, idx) {
    const stepNo = s.step != null ? s.step : idx + 1;
    const op = s.operation || s.kind || "";
    const conf = s.confidence != null ? Number(s.confidence).toFixed(2) : null;
    const prob = s.probability != null ? Number(s.probability).toFixed(2) : null;
    const usage = s.usage || {};
    const tokens = usage.input_tokens != null
      ? usage.input_tokens + "→" + (usage.output_tokens ?? "?") : null;
    let textBlock = "";
    if (s.text != null && s.text !== "") {
      textBlock = '<div class="step-text"><div class="label">Text typed</div>' + esc(s.text) + "</div>";
    }
    return (
      '<li class="step"><div class="step-num">' + esc(stepNo) + "</div>" +
      '<div class="step-body"><div class="action">' + esc(s.action || "(unnamed)") +
      (op ? ' <span class="op">' + esc(op) + "</span>" : "") +
      (s.kind && s.kind !== op ? ' <span class="op">' + esc(s.kind) + "</span>" : "") +
      "</div><div class='step-grid'>" +
      '<div><div class="k">Confidence</div><div class="v">' + (conf != null ? conf : "—") + "</div></div>" +
      '<div><div class="k">Probability</div><div class="v">' + (prob != null ? prob : "—") + "</div></div>" +
      '<div><div class="k">Latency</div><div class="v">' + fmtMs(s.latency_ms) + "</div></div>" +
      '<div><div class="k">Elapsed</div><div class="v">' + fmtMs(s.elapsed_ms) + "</div></div>" +
      '<div><div class="k">Tokens</div><div class="v">' + (tokens != null ? esc(tokens) : "—") + "</div></div>" +
      '<div><div class="k">URL after</div><div class="v">' + (s.url ? esc(s.url) : "—") + "</div></div>" +
      "</div>" + textBlock + "</div></li>"
    );
  }

  function renderCase(c, root) {
    const hist = c.history || [];
    let emptyReason = "No history steps in the source dump.";
    if (!hist.length && String(c.id).indexOf("R2_") === 0)
      emptyReason = "Zero-action land — DOI resolved with no agent steps.";
    let traceHtml;
    if (!hist.length) {
      traceHtml = '<div class="trace-empty"><strong>Empty Trace</strong>' + esc(emptyReason) +
        (c.error ? "<br><span class='mono'>" + esc(c.error) + "</span>" : "") + "</div>";
    } else {
      traceHtml = '<ol class="timeline">' + hist.map(renderStep).join("") + "</ol>";
    }
    const art = document.createElement("article");
    art.className = "case";
    art.id = "case-" + c.id;
    art.innerHTML =
      '<div class="case-head"><div><div class="idline">' + esc(c.id) +
      (c.suite ? " · " + esc(c.suite) : "") +
      (c.expect_fail ? " · expect_fail" : "") +
      '</div><h3>' + esc(c.display || c.id) + "</h3>" +
      densityHtml(hist) +
      '</div><div class="badges">' +
      (c.budget_hit ? '<span class="pill budget">budget hit</span>' : "") +
      '<span class="tier-chip ' + esc(tierClass(c.tier)) + '"><span class="dot"></span>' + esc(c.tier || "—") + "</span>" +
      '<span class="pill ' + gradeClass(c.qc_grade) + '">' + esc(gradeLabel(c.qc_grade)) + "</span>" +
      "</div></div>" +
      '<div class="case-body">' +
      "<h4>Hypothesis / why</h4><p class='why'>" + esc(c.why || "—") + "</p>" +
      "<h4>Protocol</h4><div class='protocol'>" +
      "<div class='lab'>Start URL</div><div class='val mono'>" + esc(c.url || "—") + "</div>" +
      "<div class='lab'>Goal (verbatim)</div><div class='val goal'>" + esc(c.goal || "—") + "</div></div>" +
      "<h4>Outcome dials</h4><div class='dials'>" +
      dial("QC grade", gradeLabel(c.qc_grade)) +
      dial("Agent status", c.status || "—") +
      dial("Elapsed", fmtMs(c.elapsed_ms_agent)) +
      dial("Actions", c.actions != null ? String(c.actions) : String(hist.length)) +
      dial("Wall", c.wall_s != null ? Number(c.wall_s).toFixed(1) + "s" : "—") +
      dial("Budget hit", c.budget_hit ? "true" : "false") +
      dial("Expect fail", c.expect_fail ? "true" : "false") +
      dial("Trace steps", String(hist.length)) +
      "</div>" +
      "<h4>Final URL</h4><div class='protocol'><div class='val mono'>" +
      (c.final_url ? esc(c.final_url) : "—") + "</div></div>" +
      "<h4>QC judgment</h4><div class='note'>" + esc(c.qc_note || "—") +
      (c.error ? "<div style='margin-top:8px' class='mono'>" + esc(c.error) + "</div>" : "") +
      "</div>" +
      "<h4>Trace report</h4>" + traceHtml +
      '<a class="backtop" href="#stress-toc">↑ Back to stress TOC</a></div>';
    root.appendChild(art);
  }

  const casesRoot = $("#cases");
  // Baseline first, then stress human, then quant — with section headers injected via markers
  function sectionHeader(title, id) {
    const d = document.createElement("div");
    d.id = id;
    d.style.margin = "8px 0 24px";
    d.innerHTML = '<div class="section-tag">Section</div><h2 style="margin:0;font-size:24px;font-weight:400">' + esc(title) + "</h2>";
    casesRoot.appendChild(d);
  }
  sectionHeader("Baseline R1–R11", "sec-baseline");
  baseline.forEach((c) => renderCase(c, casesRoot));
  sectionHeader("Human stress S1–S10", "sec-human");
  human.forEach((c) => renderCase(c, casesRoot));
  sectionHeader("Quant stress QS*", "sec-quant");
  quant.forEach((c) => renderCase(c, casesRoot));
})();
"""


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    n = len(payload.get("cases") or [])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{payload.get("title", "Jev Research Notebook v2")}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
{CSS}
</style>
</head>
<body>
<header class="topnav">
  <div class="brand">Astryx · <span>Jev Research Notebook v2</span></div>
  <nav>
    <a href="#finding">Finding</a>
    <a href="#viz">Viz</a>
    <a href="#toc-baseline">R1–R11</a>
    <a href="#stress-toc">Stress</a>
    <a href="#cases-section">Traces</a>
  </nav>
</header>

<section class="hero" id="finding">
  <div class="hero-inner">
    <div class="eyebrow">Research notebook v2 · static viewer</div>
    <h1>{payload.get("title", "Jev Ultrafast — Research Notebook v2")}</h1>
    <p class="lede">{payload.get("subtitle", "")}. Click any experiment for dials, budget badges, tier chips, density strip, and the ordered Trace.</p>
    <div class="hero-meta">
      <div class="hero-chip">Session <strong id="hero-date"></strong></div>
      <div class="hero-chip">Generated <strong id="hero-gen"></strong></div>
      <div class="hero-chip">Cases <strong>{n}</strong></div>
    </div>
    <div class="finding">
      <div class="lab">Executive finding</div>
      <p id="finding-text"></p>
    </div>
  </div>
</section>

<section class="section" id="scorecard">
  <div class="wrap">
    <h2>Scorecards</h2>
    <p class="sub">Baseline QC (R1–R11) alongside CoS-locked stress grades. Expected fails are scored separately.</p>
    <h3 style="font-size:15px;font-weight:600;margin:0 0 12px;color:var(--muted)">Baseline R1–R11</h3>
    <div class="scoregrid" style="margin-bottom:28px">
      <div class="scorecard pass"><div class="label">Pass</div><div class="value" id="scb-pass">—</div></div>
      <div class="scorecard partial"><div class="label">Partial</div><div class="value" id="scb-partial">—</div></div>
      <div class="scorecard fail"><div class="label">Miss</div><div class="value" id="scb-fail">—</div></div>
      <div class="scorecard expected"><div class="label">Expected fail</div><div class="value" id="scb-expected">—</div></div>
    </div>
    <h3 style="font-size:15px;font-weight:600;margin:0 0 12px;color:var(--muted)">Stress (human + quant)</h3>
    <div class="scoregrid">
      <div class="scorecard pass"><div class="label">Pass</div><div class="value" id="scs-pass">—</div></div>
      <div class="scorecard partial"><div class="label">Partial</div><div class="value" id="scs-partial">—</div></div>
      <div class="scorecard fail"><div class="label">Miss</div><div class="value" id="scs-fail">—</div></div>
      <div class="scorecard expected"><div class="label">Expected fail</div><div class="value" id="scs-expected">—</div></div>
    </div>
  </div>
</section>

<section class="section soft" id="viz">
  <div class="wrap">
    <h2>Suite visualization</h2>
    <p class="sub">Outcome mix per suite and action-count bars for stress cases. Scarce Coinbase blue on density click chips only.</p>
    <div class="viz-grid">
      <div class="viz-card">
        <h3>Outcome mix</h3>
        <div id="mix-bars"></div>
        <div class="mix-legend">
          <span><i class="pass"></i>Pass</span>
          <span><i class="partial"></i>Partial</span>
          <span><i class="fail"></i>Miss</span>
          <span><i class="fail_expected"></i>Expected fail</span>
        </div>
      </div>
      <div class="viz-card">
        <h3>Stress action counts</h3>
        <div id="action-bars"></div>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <h2>Methodology</h2>
    <p class="sub">Offline over QC + history dumps; the page never launches the agent.</p>
    <div class="method" id="method-blurb"></div>
  </div>
</section>

<section class="section soft" id="toc-baseline">
  <div class="wrap">
    <div class="section-tag">Baseline</div>
    <h2>Experiments R1–R11</h2>
    <p class="sub">Original research-browser suite. Click through for Trace reports.</p>
    <div class="toc" id="toc-baseline-list"></div>
  </div>
</section>

<section class="section" id="stress-toc">
  <div class="wrap">
    <div class="section-tag">Stress test</div>
    <h2>Human workflows S1–S10</h2>
    <p class="sub">Multi-hop lit / model / ops / NBER stress. Budget-hit badges mark demo ceilings.</p>
    <div class="toc" id="toc-human"></div>
    <div style="height:40px"></div>
    <div class="section-tag">Stress test</div>
    <h2>Quant suite QS1–QS8+QS7b</h2>
    <p class="sub">Writing-paper, SARIMAX, OT, ragged-edge, NBER, and corporate ToS paths.</p>
    <div class="toc" id="toc-quant"></div>
  </div>
</section>

<section class="section soft" id="cases-section">
  <div class="wrap">
    <h2>Per-experiment Trace reports</h2>
    <p class="sub">Hypothesis, protocol, dials, QC note, density strip, then the ordered action timeline.</p>
    <div class="method" style="margin-bottom:28px">
      <strong style="color:var(--ink)">Trace legend.</strong>
      Density chips: <span class="mono">blue</span> = click, teal = scroll, purple-ish = nav, dark = type/fill.
      Budget-hit badges mean model-call or 60-action demo ceiling. Tier chips color lit / model / ops / nber.
    </div>
    <div id="cases"></div>
  </div>
</section>

<footer class="footer">
  Static research notebook v2 for Jared’s Jev Ultrafast eval. Not affiliated with Coinbase, Meta, or Goldman Sachs.
  Design tokens educational only. Not investment advice.
</footer>

<script type="application/json" id="notebook-data">{data_json}</script>
<script>
{JS}
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--qc", type=Path, default=DEFAULT_QC)
    p.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    p.add_argument("--stress-qc", type=Path, default=DEFAULT_STRESS_QC)
    p.add_argument("--stress-cases", type=Path, default=DEFAULT_STRESS_CASES)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    qc = _load(args.qc if args.qc.is_absolute() else ROOT / args.qc)
    stress_qc = _load(
        args.stress_qc if args.stress_qc.is_absolute() else ROOT / args.stress_qc
    )
    cases = args.cases if args.cases.is_absolute() else ROOT / args.cases
    stress_cases = (
        args.stress_cases if args.stress_cases.is_absolute() else ROOT / args.stress_cases
    )
    payload = build_payload(qc, cases, stress_qc, stress_cases)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(payload)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes, {len(payload['cases'])} cases)")
    print(f"Baseline scorecard: {payload['scorecard_baseline']}")
    print(f"Stress scorecard: {payload['scorecard_stress']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
