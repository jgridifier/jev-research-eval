#!/usr/bin/env python3
"""Generate JEV_RESEARCH_NOTEBOOK_v1.html — interactive drill-down research notebook.

Static HTML+CSS+JS (no build). Case data is embedded as JSON in
<script type="application/json" id="notebook-data">.

Prefer richer per-case histories when available:
  1) --traces-dir (default results/run_notebook_traces/) full history dumps
  2) fixtures/cases_with_traces.json
  3) history / history_tail on the QC input itself

Does not run the agent — offline viewer over existing QC + traces.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "fixtures" / "qc_rescored.json"
DEFAULT_CASES = ROOT / "fixtures" / "cases_with_traces.json"
DEFAULT_TRACES = ROOT / "results" / "run_notebook_traces"
DEFAULT_OUTPUT = ROOT / "fixtures" / "JEV_RESEARCH_NOTEBOOK_v1.html"

DISPLAY: dict[str, str] = {
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

CASE_ORDER = [
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


def _as_list(v: Any) -> list:
    return list(v) if isinstance(v, list) else []


def _pick_history(obj: dict) -> list:
    """Prefer full history over history_tail."""
    h = _as_list(obj.get("history"))
    if h:
        return h
    return _as_list(obj.get("history_tail"))


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_traces_dir(traces_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not traces_dir.is_dir():
        return out
    for f in traces_dir.glob("R*.json"):
        try:
            payload = _load_json(f)
        except Exception:
            continue
        cid = payload.get("id") or f.stem
        out[cid] = payload
    return out


def _normalize_case(cid: str, r: dict, live_map: dict[str, dict]) -> dict:
    h = _pick_history(r)
    live = live_map.get(cid)
    live_h = _pick_history(live) if live else []
    prior_src = r.get("trace_source")
    if isinstance(prior_src, str) and prior_src.startswith("rerun_"):
        src = prior_src
    elif live_h and h == live_h:
        src = "live_full"
    elif h:
        src = "history"
    else:
        src = "empty"
    return {
        "id": r.get("id", cid),
        "display": DISPLAY.get(cid, cid),
        "tier": r.get("tier"),
        "expect_fail": bool(r.get("expect_fail")),
        "why": r.get("why") or "",
        "url": r.get("url") or "",
        "goal": r.get("goal") or "",
        "ok": r.get("ok"),
        "final_url": r.get("final_url"),
        "status": r.get("status"),
        "elapsed_ms_agent": r.get("elapsed_ms_agent"),
        "actions": r.get("actions") if r.get("actions") is not None else len(h),
        "error": r.get("error"),
        "matched": r.get("matched"),
        "wall_s": r.get("wall_s"),
        "qc_grade": r.get("qc_grade"),
        "qc_note": r.get("qc_note") or "",
        "history": h,
        "history_tail": h[-5:] if h else [],
        "trace_source": src,
    }


def build_notebook_payload(
    qc: dict,
    *,
    cases_path: Path | None,
    traces_dir: Path | None,
) -> dict:
    by_id: dict[str, dict] = {}
    for r in qc.get("results") or []:
        by_id[r["id"]] = dict(r)

    # Overlay slim fixtures/cases_with_traces.json — history only (QC dials win)
    if cases_path and cases_path.is_file():
        slim = _load_json(cases_path)
        for c in slim.get("cases") or []:
            cid = c.get("id")
            if not cid:
                continue
            base = by_id.setdefault(cid, {"id": cid})
            old_h = _pick_history(base)
            new_h = _pick_history(c)
            if len(new_h) > len(old_h) or (new_h and not old_h):
                base["history"] = new_h
                base["history_tail"] = new_h[-5:]
            elif "history" not in base:
                base["history"] = old_h
                base["history_tail"] = old_h[-5:] if old_h else []
            # Fill missing non-history fields only
            for k, v in c.items():
                if k in ("history", "history_tail"):
                    continue
                if base.get(k) is None and v is not None:
                    base[k] = v

    live_map = load_traces_dir(traces_dir) if traces_dir else {}

    # Overlay live full-history dumps — upgrade traces when richer; keep QC dials
    # unless we adopt the live run as the primary trace source.
    for cid, payload in live_map.items():
        base = by_id.setdefault(cid, {"id": cid})
        live_h = _pick_history(payload)
        old_h = _pick_history(base)
        adopt_live = len(live_h) > len(old_h) or (bool(live_h) and not old_h)
        if adopt_live:
            base["history"] = live_h
            base["history_tail"] = live_h[-5:]
            for k in (
                "status",
                "final_url",
                "elapsed_ms",
                "elapsed_ms_agent",
                "actions",
                "error",
                "ok",
                "matched",
                "wall_s",
            ):
                if payload.get(k) is not None:
                    if k == "elapsed_ms":
                        base["elapsed_ms_agent"] = payload[k]
                    else:
                        base[k] = payload[k]
        elif "history" not in base:
            base["history"] = old_h
            base["history_tail"] = old_h[-5:] if old_h else []

    cases: list[dict] = []
    for cid in CASE_ORDER:
        if cid not in by_id:
            continue
        cases.append(_normalize_case(cid, by_id.pop(cid), live_map))
    for cid, r in sorted(by_id.items()):
        cases.append(_normalize_case(cid, r, live_map))

    scorecard = {
        "qc_pass": qc.get("qc_pass", sum(1 for c in cases if c.get("qc_grade") == "pass")),
        "qc_partial": qc.get("qc_partial", sum(1 for c in cases if c.get("qc_grade") == "partial")),
        "qc_fail": qc.get("qc_fail", sum(1 for c in cases if c.get("qc_grade") == "fail")),
        "qc_fail_expected": qc.get(
            "qc_fail_expected", sum(1 for c in cases if c.get("qc_grade") == "fail_expected")
        ),
    }

    return {
        "title": "Jev Ultrafast — Research Notebook",
        "subtitle": "Research-browser eval · interactive experiment drill-down",
        "session_date": "17 Sep 2026",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M").strip(),
        "methodology": (
            "Eleven goal-driven browser cases (R1–R11) against literature, macro, "
            "SEC, and encyclopedia surfaces, plus three intentional expect-fail stress tests. "
            "Auto run records status, elapsed ms, actions, final URL, and action history; "
            "human QC grades destination quality independently (pass / partial / fail / fail_expected). "
            "This notebook is a static viewer — click a case to inspect dials and the per-step "
            "trace of what Jev actually did. Traces prefer full history dumps from "
            "results/run_notebook_traces/ (via scripts/run_goal_full.py), then "
            "fixtures/cases_with_traces.json, then history / history_tail on the QC file. "
            "The page never launches the agent; regenerate offline with "
            "scripts/generate_notebook_v1.py."
        ),
        "scorecard": scorecard,
        "cases": cases,
    }


def write_cases_fixture(payload: dict, path: Path) -> None:
    slim = {
        "session": "2026-09-17",
        "title": "Jev Ultrafast research-browser eval",
        "scorecard": payload["scorecard"],
        "cases": [
            {
                "id": c["id"],
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
                "history": c["history"],
                "history_tail": (c["history"] or [])[-5:],
                "trace_source": c.get("trace_source"),
            }
            for c in payload["cases"]
        ],
    }
    path.write_text(json.dumps(slim, indent=2) + "\n", encoding="utf-8")


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
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Inter, -apple-system, system-ui, sans-serif;
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
  color: var(--ink);
  background: var(--surface-soft);
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }
code, .mono { font-family: "JetBrains Mono", ui-monospace, monospace; }

.topnav {
  height: 64px;
  background: var(--canvas);
  border-bottom: 1px solid var(--hairline);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; position: sticky; top: 0; z-index: 20;
}
.topnav .brand { font-weight: 600; font-size: 14px; letter-spacing: -0.01em; }
.topnav .brand span { color: var(--primary); }
.topnav nav { display: flex; gap: 20px; font-size: 14px; font-weight: 500; }
.topnav nav a { color: var(--ink); }
.topnav nav a:hover { color: var(--primary); text-decoration: none; }

.hero {
  background: var(--surface-dark);
  color: var(--on-dark);
  padding: 72px 24px 64px;
}
.hero-inner { max-width: var(--max); margin: 0 auto; }
.hero .eyebrow {
  display: inline-block;
  background: var(--surface-dark-elevated);
  color: var(--on-dark-soft);
  font-size: 12px; font-weight: 600;
  padding: 4px 12px; border-radius: var(--radius-pill);
  margin-bottom: 20px; letter-spacing: 0.04em; text-transform: uppercase;
}
.hero h1 {
  font-size: clamp(36px, 6vw, 56px);
  font-weight: 400; line-height: 1.05; letter-spacing: -1.4px;
  margin: 0 0 16px;
}
.hero .lede { color: var(--on-dark-soft); font-size: 17px; max-width: 640px; margin: 0 0 28px; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 12px; }
.hero-chip {
  background: var(--surface-dark-elevated);
  border-radius: var(--radius-pill);
  padding: 8px 14px; font-size: 13px; color: var(--on-dark-soft);
}
.hero-chip strong { color: var(--on-dark); font-family: "JetBrains Mono", monospace; font-weight: 500; }

.wrap { max-width: var(--max); margin: 0 auto; padding: 0 24px; }
.section { padding: 56px 0; }
.section.soft { background: var(--canvas); }
.section h2 {
  font-size: 28px; font-weight: 400; letter-spacing: -0.4px;
  margin: 0 0 8px;
}
.section .sub { color: var(--body); margin: 0 0 28px; max-width: 720px; }

.scoregrid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
}
@media (max-width: 800px) { .scoregrid { grid-template-columns: repeat(2, 1fr); } }
.scorecard {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  padding: 24px;
}
.scorecard .label { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.scorecard .value { font-family: "JetBrains Mono", monospace; font-size: 36px; font-weight: 500; margin-top: 8px; letter-spacing: -1px; }
.scorecard.pass .value { color: var(--up); }
.scorecard.partial .value { color: var(--accent-yellow); }
.scorecard.fail .value { color: var(--down); }
.scorecard.expected .value { color: var(--muted); }

.method {
  background: var(--surface-soft);
  border-radius: var(--radius-xl);
  padding: 24px 28px;
  color: var(--body);
  border: 1px solid var(--hairline-soft);
}

.toc {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;
}
.toc-card {
  display: block;
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: 16px;
  padding: 18px 20px;
  color: inherit; text-decoration: none;
  transition: border-color .15s, box-shadow .15s;
}
.toc-card:hover { border-color: var(--primary); box-shadow: var(--shadow); text-decoration: none; }
.toc-card .row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
.toc-card .id { font-family: "JetBrains Mono", monospace; font-size: 12px; color: var(--muted); font-weight: 500; }
.toc-card .title { font-size: 15px; font-weight: 600; line-height: 1.3; }
.toc-card .meta { font-size: 13px; color: var(--muted); margin-top: 8px; display: flex; gap: 10px; flex-wrap: wrap; }

.pill {
  display: inline-flex; align-items: center;
  font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
  padding: 3px 10px; border-radius: var(--radius-pill);
  background: var(--surface-strong); color: var(--ink);
  white-space: nowrap;
}
.pill.pass { background: rgba(5,177,105,.12); color: var(--up); }
.pill.partial { background: rgba(244,176,0,.16); color: #a07800; }
.pill.fail { background: rgba(207,32,47,.12); color: var(--down); }
.pill.fail_expected { background: var(--surface-strong); color: var(--muted); }
.pill.expect { background: rgba(0,82,255,.08); color: var(--primary); }

.case {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  margin-bottom: 28px;
  overflow: hidden;
  scroll-margin-top: 80px;
}
.case-head {
  padding: 28px 32px 20px;
  border-bottom: 1px solid var(--hairline-soft);
  display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  align-items: flex-start;
}
.case-head h3 { margin: 0 0 6px; font-size: 22px; font-weight: 400; letter-spacing: -0.3px; }
.case-head .idline { font-family: "JetBrains Mono", monospace; font-size: 12px; color: var(--muted); }
.case-body { padding: 24px 32px 32px; }
.case-body h4 {
  font-size: 13px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--muted); margin: 24px 0 10px;
}
.case-body h4:first-child { margin-top: 0; }
.why { color: var(--body); margin: 0; }
.protocol {
  background: var(--surface-soft);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  font-size: 14px;
}
.protocol .lab { font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.protocol .val { word-break: break-all; margin-bottom: 12px; }
.protocol .val:last-child { margin-bottom: 0; }
.protocol .goal { white-space: pre-wrap; color: var(--ink); }

.dials {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px;
}
.dial {
  background: var(--surface-soft);
  border-radius: 12px;
  padding: 14px 16px;
}
.dial .lab { font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.dial .val { font-family: "JetBrains Mono", monospace; font-size: 16px; font-weight: 500; margin-top: 4px; word-break: break-word; }

.note {
  border-left: 3px solid var(--primary);
  padding: 10px 0 10px 16px;
  color: var(--body); font-size: 15px;
}

.trace-empty {
  background: var(--surface-soft);
  border-radius: var(--radius-md);
  padding: 28px 20px;
  text-align: center; color: var(--muted); font-size: 14px;
}
.trace-empty strong { display: block; color: var(--ink); font-weight: 600; margin-bottom: 4px; }

.timeline { list-style: none; margin: 0; padding: 0; }
.step {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid var(--hairline-soft);
}
.step:last-child { border-bottom: 0; }
.step-num {
  width: 40px; height: 40px;
  border-radius: 999px;
  background: var(--surface-strong);
  display: flex; align-items: center; justify-content: center;
  font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 500;
  color: var(--ink);
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
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 6px 14px;
  font-size: 13px; color: var(--body);
}
.step-grid .k { color: var(--muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.step-grid .v { font-family: "JetBrains Mono", monospace; font-size: 12px; word-break: break-all; }
.step-text {
  margin-top: 8px;
  background: var(--surface-dark);
  color: var(--on-dark);
  border-radius: 10px;
  padding: 10px 12px;
  font-family: "JetBrains Mono", monospace; font-size: 12px;
}
.step-text .label { color: var(--on-dark-soft); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; font-family: Inter, sans-serif; }

.backtop {
  display: inline-block; margin-top: 12px; font-size: 13px; font-weight: 600;
}

.footer {
  padding: 48px 24px 64px;
  color: var(--muted); font-size: 13px; text-align: center;
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
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function fmtMs(v) {
    if (v == null || v === "") return "—";
    const n = Number(v);
    if (Number.isNaN(n)) return esc(v);
    if (n >= 1000) return (n / 1000).toFixed(2) + "s";
    return Math.round(n) + "ms";
  }
  function fmtNum(v, suffix) {
    if (v == null || v === "") return "—";
    return esc(v) + (suffix || "");
  }
  function gradeClass(g) {
    if (!g) return "";
    return String(g);
  }
  function gradeLabel(g) {
    const map = { pass: "Pass", partial: "Partial", fail: "Miss", fail_expected: "Expected fail" };
    return map[g] || (g || "—");
  }

  // Hero meta
  $("#hero-date").textContent = data.session_date || "";
  $("#hero-gen").textContent = data.generated_at || "";
  const sc = data.scorecard || {};
  $("#sc-pass").textContent = sc.qc_pass ?? "—";
  $("#sc-partial").textContent = sc.qc_partial ?? "—";
  $("#sc-fail").textContent = sc.qc_fail ?? "—";
  $("#sc-expected").textContent = sc.qc_fail_expected ?? "—";
  $("#method-blurb").textContent = data.methodology || "";

  const cases = data.cases || [];
  const toc = $("#toc");
  const casesRoot = $("#cases");

  cases.forEach((c) => {
    const nSteps = (c.history || []).length;
    const card = document.createElement("a");
    card.className = "toc-card";
    card.href = "#case-" + c.id;
    card.innerHTML =
      '<div class="row"><span class="id">' + esc(c.id) + '</span>' +
      '<span class="pill ' + gradeClass(c.qc_grade) + '">' + esc(gradeLabel(c.qc_grade)) + "</span></div>" +
      '<div class="title">' + esc(c.display || c.id) + "</div>" +
      '<div class="meta"><span>' + (c.expect_fail ? '<span class="pill expect">expect fail</span> ' : "") +
      esc(c.tier || "") + "</span><span>" + nSteps + " trace step" + (nSteps === 1 ? "" : "s") +
      "</span><span>" + fmtMs(c.elapsed_ms_agent) + "</span></div>";
    toc.appendChild(card);
  });

  function renderStep(s, idx) {
    const stepNo = s.step != null ? s.step : idx + 1;
    const op = s.operation || s.kind || "";
    const conf = s.confidence != null ? Number(s.confidence).toFixed(2) : null;
    const prob = s.probability != null ? Number(s.probability).toFixed(2) : null;
    const usage = s.usage || {};
    const tokens =
      usage.input_tokens != null
        ? usage.input_tokens + "→" + (usage.output_tokens ?? "?")
        : null;
    let textBlock = "";
    if (s.text != null && s.text !== "") {
      textBlock =
        '<div class="step-text"><div class="label">Text typed</div>' +
        esc(s.text) +
        "</div>";
    }
    return (
      '<li class="step">' +
      '<div class="step-num">' +
      esc(stepNo) +
      "</div>" +
      '<div class="step-body">' +
      '<div class="action">' +
      esc(s.action || "(unnamed)") +
      (op ? ' <span class="op">' + esc(op) + "</span>" : "") +
      (s.kind && s.kind !== op ? ' <span class="op">' + esc(s.kind) + "</span>" : "") +
      "</div>" +
      '<div class="step-grid">' +
      '<div><div class="k">Confidence</div><div class="v">' +
      (conf != null ? conf : "—") +
      "</div></div>" +
      '<div><div class="k">Probability</div><div class="v">' +
      (prob != null ? prob : "—") +
      "</div></div>" +
      '<div><div class="k">Latency</div><div class="v">' +
      fmtMs(s.latency_ms) +
      "</div></div>" +
      '<div><div class="k">Elapsed</div><div class="v">' +
      fmtMs(s.elapsed_ms) +
      "</div></div>" +
      '<div><div class="k">Tokens</div><div class="v">' +
      (tokens != null ? esc(tokens) : "—") +
      "</div></div>" +
      '<div><div class="k">URL after</div><div class="v">' +
      (s.url ? esc(s.url) : "—") +
      "</div></div>" +
      "</div>" +
      textBlock +
      "</div></li>"
    );
  }

  cases.forEach((c) => {
    const hist = c.history || [];
    const emptyReason =
      c.id.indexOf("R2_") === 0
        ? "Zero-action land — DOI resolved with no agent steps."
        : c.id.indexOf("R3_") === 0
          ? "No usable trace captured (often budget / early abort)."
          : "No history / history_tail steps in the source dump.";

    let traceHtml;
    if (!hist.length) {
      traceHtml =
        '<div class="trace-empty"><strong>Empty trace</strong>' +
        esc(emptyReason) +
        (c.error ? "<br><span class='mono'>" + esc(c.error) + "</span>" : "") +
        "</div>";
    } else {
      traceHtml =
        '<ol class="timeline">' +
        hist.map((s, i) => renderStep(s, i)).join("") +
        "</ol>";
    }

    const art = document.createElement("article");
    art.className = "case";
    art.id = "case-" + c.id;
    art.innerHTML =
      '<div class="case-head">' +
      "<div><div class='idline'>" +
      esc(c.id) +
      (c.tier ? " · " + esc(c.tier) : "") +
      (c.expect_fail ? " · expect_fail" : "") +
      "</div><h3>" +
      esc(c.display || c.id) +
      "</h3></div>" +
      '<div><span class="pill ' +
      gradeClass(c.qc_grade) +
      '">' +
      esc(gradeLabel(c.qc_grade)) +
      "</span></div></div>" +
      '<div class="case-body">' +
      "<h4>Hypothesis / why</h4><p class='why'>" +
      esc(c.why || "—") +
      "</p>" +
      "<h4>Protocol</h4><div class='protocol'>" +
      "<div class='lab'>Start URL</div><div class='val mono'>" +
      esc(c.url || "—") +
      "</div>" +
      "<div class='lab'>Goal (verbatim)</div><div class='val goal'>" +
      esc(c.goal || "—") +
      "</div></div>" +
      "<h4>Outcome dials</h4><div class='dials'>" +
      dial("QC grade", gradeLabel(c.qc_grade)) +
      dial("Agent status", c.status || "—") +
      dial("Elapsed", fmtMs(c.elapsed_ms_agent)) +
      dial("Actions", c.actions != null ? String(c.actions) : String(hist.length)) +
      dial("Wall", c.wall_s != null ? Number(c.wall_s).toFixed(1) + "s" : "—") +
      dial("Expect fail", c.expect_fail ? "true" : "false") +
      dial("Matched", c.matched == null ? "—" : String(c.matched)) +
      dial("Trace steps", String(hist.length)) +
      "</div>" +
      "<h4>Final URL</h4><div class='protocol'><div class='val mono'>" +
      (c.final_url ? esc(c.final_url) : "—") +
      "</div></div>" +
      "<h4>QC judgment</h4><div class='note'>" +
      esc(c.qc_note || "—") +
      (c.error ? "<div style='margin-top:8px' class='mono'>" + esc(c.error) + "</div>" : "") +
      "</div>" +
      "<h4>Trace report</h4>" +
      traceHtml +
      '<a class="backtop" href="#toc-anchor">↑ Back to experiments</a>' +
      "</div>";
    casesRoot.appendChild(art);
  });

  function dial(lab, val) {
    return (
      '<div class="dial"><div class="lab">' +
      esc(lab) +
      '</div><div class="val">' +
      (typeof val === "string" && val.indexOf("<") >= 0 ? val : esc(val)) +
      "</div></div>"
    );
  }

  // Re-fix dial helper used above before definition — redefine properly
  // (dial is hoisted as function declaration via rewrite below)
})();
"""

# Fix JS: dial is used before the function declaration in the IIFE.
# Rewrite JS with dial defined first.
JS = r"""
(function () {
  const el = document.getElementById("notebook-data");
  if (!el) return;
  const data = JSON.parse(el.textContent);
  const $ = (sel, root) => (root || document).querySelector(sel);

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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
    return (
      '<div class="dial"><div class="lab">' + esc(lab) +
      '</div><div class="val">' + esc(val) + "</div></div>"
    );
  }

  $("#hero-date").textContent = data.session_date || "";
  $("#hero-gen").textContent = data.generated_at || "";
  const sc = data.scorecard || {};
  $("#sc-pass").textContent = sc.qc_pass ?? "—";
  $("#sc-partial").textContent = sc.qc_partial ?? "—";
  $("#sc-fail").textContent = sc.qc_fail ?? "—";
  $("#sc-expected").textContent = sc.qc_fail_expected ?? "—";
  $("#method-blurb").textContent = data.methodology || "";

  const cases = data.cases || [];
  const toc = $("#toc");
  const casesRoot = $("#cases");

  cases.forEach((c) => {
    const nSteps = (c.history || []).length;
    const card = document.createElement("a");
    card.className = "toc-card";
    card.href = "#case-" + c.id;
    card.innerHTML =
      '<div class="row"><span class="id">' + esc(c.id) + '</span>' +
      '<span class="pill ' + gradeClass(c.qc_grade) + '">' + esc(gradeLabel(c.qc_grade)) + "</span></div>" +
      '<div class="title">' + esc(c.display || c.id) + "</div>" +
      '<div class="meta"><span>' + (c.expect_fail ? '<span class="pill expect">expect fail</span> ' : "") +
      esc(c.tier || "") + "</span><span>" + nSteps + " Trace step" + (nSteps === 1 ? "" : "s") +
      "</span><span>" + fmtMs(c.elapsed_ms_agent) + "</span></div>";
    toc.appendChild(card);
  });

  function renderStep(s, idx) {
    const stepNo = s.step != null ? s.step : idx + 1;
    const op = s.operation || s.kind || "";
    const conf = s.confidence != null ? Number(s.confidence).toFixed(2) : null;
    const prob = s.probability != null ? Number(s.probability).toFixed(2) : null;
    const usage = s.usage || {};
    const tokens =
      usage.input_tokens != null
        ? usage.input_tokens + "→" + (usage.output_tokens ?? "?")
        : null;
    let textBlock = "";
    if (s.text != null && s.text !== "") {
      textBlock =
        '<div class="step-text"><div class="label">Text typed</div>' +
        esc(s.text) +
        "</div>";
    }
    return (
      '<li class="step">' +
      '<div class="step-num">' + esc(stepNo) + "</div>" +
      '<div class="step-body">' +
      '<div class="action">' + esc(s.action || "(unnamed)") +
      (op ? ' <span class="op">' + esc(op) + "</span>" : "") +
      (s.kind && s.kind !== op ? ' <span class="op">' + esc(s.kind) + "</span>" : "") +
      "</div>" +
      '<div class="step-grid">' +
      '<div><div class="k">Confidence</div><div class="v">' + (conf != null ? conf : "—") + "</div></div>" +
      '<div><div class="k">Probability</div><div class="v">' + (prob != null ? prob : "—") + "</div></div>" +
      '<div><div class="k">Latency</div><div class="v">' + fmtMs(s.latency_ms) + "</div></div>" +
      '<div><div class="k">Elapsed</div><div class="v">' + fmtMs(s.elapsed_ms) + "</div></div>" +
      '<div><div class="k">Tokens</div><div class="v">' + (tokens != null ? esc(tokens) : "—") + "</div></div>" +
      '<div><div class="k">URL after</div><div class="v">' + (s.url ? esc(s.url) : "—") + "</div></div>" +
      "</div>" + textBlock + "</div></li>"
    );
  }

  cases.forEach((c) => {
    const hist = c.history || [];
    let emptyReason = "No history / history_tail steps in the source dump.";
    if (c.id.indexOf("R2_") === 0) emptyReason = "Zero-action land — DOI resolved with no agent steps.";
    else if (c.id.indexOf("R3_") === 0) emptyReason = "No usable trace (budget / early abort on this dump).";
    else if (c.id.indexOf("R6_") === 0) emptyReason = "Blocked with zero recorded actions.";

    let traceHtml;
    if (!hist.length) {
      traceHtml =
        '<div class="trace-empty"><strong>Empty Trace</strong>' +
        esc(emptyReason) +
        (c.error ? "<br><span class='mono'>" + esc(c.error) + "</span>" : "") +
        "</div>";
    } else {
      traceHtml = '<ol class="timeline">' + hist.map(renderStep).join("") + "</ol>";
    }

    const art = document.createElement("article");
    art.className = "case";
    art.id = "case-" + c.id;
    art.innerHTML =
      '<div class="case-head"><div><div class="idline">' +
      esc(c.id) +
      (c.tier ? " · " + esc(c.tier) : "") +
      (c.expect_fail ? " · expect_fail" : "") +
      '</div><h3>' + esc(c.display || c.id) + "</h3></div>" +
      '<div><span class="pill ' + gradeClass(c.qc_grade) + '">' +
      esc(gradeLabel(c.qc_grade)) + "</span></div></div>" +
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
      dial("Expect fail", c.expect_fail ? "true" : "false") +
      dial("Matched", c.matched == null ? "—" : String(c.matched)) +
      dial("Trace steps", String(hist.length)) +
      "</div>" +
      "<h4>Final URL</h4><div class='protocol'><div class='val mono'>" +
      (c.final_url ? esc(c.final_url) : "—") + "</div></div>" +
      "<h4>QC judgment</h4><div class='note'>" + esc(c.qc_note || "—") +
      (c.error ? "<div style='margin-top:8px' class='mono'>" + esc(c.error) + "</div>" : "") +
      "</div>" +
      "<h4>Trace report</h4>" + traceHtml +
      '<a class="backtop" href="#toc-anchor">↑ Back to experiments</a></div>';
    casesRoot.appendChild(art);
  });
})();
"""


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{payload.get("title", "Jev Research Notebook")}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
{CSS}
</style>
</head>
<body>
<header class="topnav">
  <div class="brand">Astryx · <span>Jev Research Notebook</span></div>
  <nav>
    <a href="#scorecard">Scorecard</a>
    <a href="#toc-anchor">Experiments</a>
    <a href="#cases">Traces</a>
  </nav>
</header>

<section class="hero">
  <div class="hero-inner">
    <div class="eyebrow">Research notebook · static viewer</div>
    <h1>{payload.get("title", "Jev Ultrafast — Research Notebook")}</h1>
    <p class="lede">{payload.get("subtitle", "")}. Click any experiment to open dials and the ordered Trace of what the agent did.</p>
    <div class="hero-meta">
      <div class="hero-chip">Session <strong id="hero-date"></strong></div>
      <div class="hero-chip">Generated <strong id="hero-gen"></strong></div>
      <div class="hero-chip">Cases <strong>{len(payload.get("cases") or [])}</strong></div>
    </div>
  </div>
</section>

<section class="section" id="scorecard">
  <div class="wrap">
    <h2>Scorecard</h2>
    <p class="sub">Human QC over the research-browser suite. Expected fails are scored separately from unexpected misses.</p>
    <div class="scoregrid">
      <div class="scorecard pass"><div class="label">Pass</div><div class="value" id="sc-pass">—</div></div>
      <div class="scorecard partial"><div class="label">Partial</div><div class="value" id="sc-partial">—</div></div>
      <div class="scorecard fail"><div class="label">Miss</div><div class="value" id="sc-fail">—</div></div>
      <div class="scorecard expected"><div class="label">Expected fail</div><div class="value" id="sc-expected">—</div></div>
    </div>
  </div>
</section>

<section class="section soft">
  <div class="wrap">
    <h2>Methodology</h2>
    <p class="sub">How this notebook was produced — offline over QC + history dumps; no run-from-page.</p>
    <div class="method" id="method-blurb"></div>
  </div>
</section>

<section class="section" id="toc-anchor">
  <div class="wrap">
    <h2>Experiments</h2>
    <p class="sub">Every case is clickable. Hash links work from GitHub raw/blob and file://.</p>
    <div class="toc" id="toc"></div>
  </div>
</section>

<section class="section soft" id="cases-section">
  <div class="wrap">
    <h2>Per-experiment Trace reports</h2>
    <p class="sub">Hypothesis, protocol, outcome dials, QC note, then the ordered action timeline.
    Each Trace step shows action label, operation/kind, typed text (if any), confidence/probability,
    model latency, URL after the step, and token usage when present.</p>
    <div class="method" style="margin-bottom:28px">
      <strong style="color:var(--ink)">Trace legend.</strong>
      Step numbers follow the agent history order. Empty Trace panels mean zero recorded actions
      (e.g. R2 DOI zero-action land) or a missing dump (budget abort / blocked before act).
      Live re-runs via <span class="mono">run_goal_full.py</span> write complete <span class="mono">history</span>
      arrays; the published QC snapshot may only carry <span class="mono">history_tail</span> (~last 5).
    </div>
    <div id="cases"></div>
  </div>
</section>

<footer class="footer">
  Static research notebook for Jared’s Jev Ultrafast eval. Not affiliated with Coinbase, Meta, or Goldman Sachs.
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
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="QC JSON (default fixtures/qc_rescored.json)")
    p.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Optional slim cases_with_traces.json to merge",
    )
    p.add_argument(
        "--traces-dir",
        type=Path,
        default=DEFAULT_TRACES,
        help="Dir of per-case full-history JSON (default results/run_notebook_traces)",
    )
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument(
        "--write-cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Rewrite fixtures/cases_with_traces.json from merged payload (empty string to skip)",
    )
    p.add_argument("--no-write-cases", action="store_true")
    p.add_argument("--no-traces-dir", action="store_true", help="Ignore live traces dir")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    inp = args.input if args.input.is_absolute() else ROOT / args.input
    qc = _load_json(inp)
    cases_path = None if not args.cases else (args.cases if args.cases.is_absolute() else ROOT / args.cases)
    traces_dir = None
    if not args.no_traces_dir and args.traces_dir:
        traces_dir = args.traces_dir if args.traces_dir.is_absolute() else ROOT / args.traces_dir

    payload = build_notebook_payload(qc, cases_path=cases_path, traces_dir=traces_dir)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(payload)
    out.write_text(html, encoding="utf-8")

    if not args.no_write_cases and args.write_cases:
        wp = args.write_cases if args.write_cases.is_absolute() else ROOT / args.write_cases
        if str(args.write_cases).strip():
            write_cases_fixture(payload, wp)
            print(f"Wrote {wp} ({len(payload['cases'])} cases)")

    empty = [c["id"] for c in payload["cases"] if not c["history"]]
    print(f"Wrote {out} ({len(html)} bytes, {len(payload['cases'])} cases)")
    print(f"Empty traces: {empty or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
