#!/usr/bin/env python3
"""Regenerate JEV_RESEARCH_FIELD_NOTE_v4.html from qc_rescored.json.

Self-contained — no imports from chat history. Matches the published v4 visual
language (Inter / JetBrains Mono, #0052ff, dark hero, table shell, findings A/B/C).
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "fixtures" / "qc_rescored.json"
DEFAULT_OUTPUT = ROOT / "fixtures" / "JEV_RESEARCH_FIELD_NOTE_v4.html"

# Display labels used in the published note (stable exhibit language).
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

# Timing chart order / short labels (matches published Exhibit 2).
TIMING_ORDER = [
    ("R2_doi_spelta_ot", "DOI → Spelta et al. (JRSS-A)"),
    ("R4_fred_indpro", "FRED → INDPRO"),
    ("R5_edgar_company_search", "EDGAR → Apple filings"),
    ("R8_wikipedia_disambiguation", "Wikipedia → Kalman filter"),
    ("R1_scholar_giannone_nowcast", "Google Scholar → Giannone–Reichlin–S"),
    ("R6_nber_wp_search", "NBER → Stock–Watson"),
    ("R7_crossref_doi_metadata", "Crossref → DOI record"),
    ("R9_expect_fail_pdf_upload_replicate", "PDF upload / convert"),
    ("R10_expect_fail_scholar_cite_popup_maze", "Scholar → PDF download"),
    ("R11_expect_fail_nested_data_widget", "OWID chart → CSV"),
]

# Results table order (passes first, then partial, misses, expected fails).
TABLE_ORDER = [
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

GRADE_PILL = {
    "pass": ("pass", "Pass"),
    "partial": ("partial", "Partial"),
    "fail": ("fail", "Miss"),
    "fail_expected": ("fail_expected", "Expected fail"),
}

GRADE_COLOR = {
    "pass": "#05b169",
    "partial": "#f4b000",
    "fail": "#cf202f",
    "fail_expected": "#7c828a",
}


CSS = r"""/* Tokens inspired by getdesign.md Coinbase DESIGN.md + Astryx table/detail patterns */
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
  --section: 72px;
  --max: 1120px;
}
* { box-sizing: border-box; }
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

.topnav {
  height: 64px;
  background: var(--canvas);
  border-bottom: 1px solid var(--hairline);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  font-weight: 600;
  font-size: 14px;
  letter-spacing: -0.01em;
}
.brand span { color: var(--primary); }
.topnav-meta {
  font-size: 13px;
  color: var(--muted);
  display: flex;
  gap: 16px;
  align-items: center;
}
.pill-cta {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-pill);
  background: var(--primary);
  color: #fff !important;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none !important;
}

.hero {
  background: var(--surface-dark);
  color: var(--on-dark);
  padding: 72px 32px 64px;
}
.hero-inner {
  max-width: var(--max);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 40px;
  align-items: end;
}
@media (max-width: 900px) {
  .hero-inner { grid-template-columns: 1fr; }
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
  background: var(--surface-dark-elevated);
  color: var(--on-dark-soft);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 20px;
}
.hero h1 {
  margin: 0 0 16px;
  font-size: clamp(36px, 5vw, 52px);
  font-weight: 400;
  letter-spacing: -1.3px;
  line-height: 1.05;
  max-width: 14ch;
}
.hero .lede {
  margin: 0;
  font-size: 16px;
  line-height: 1.5;
  color: var(--on-dark-soft);
  max-width: 48ch;
}
.stat-stack {
  background: var(--surface-dark-elevated);
  border-radius: var(--radius-xl);
  padding: 28px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 16px;
}
.stat .n {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 28px;
  font-weight: 500;
  line-height: 1.2;
}
.stat .n.up { color: var(--up); }
.stat .n.down { color: var(--down); }
.stat .n.warn { color: var(--accent-yellow); }
.stat .l {
  margin-top: 4px;
  font-size: 13px;
  color: var(--on-dark-soft);
}

.band {
  max-width: var(--max);
  margin: 0 auto;
  padding: var(--section) 32px;
}
.band.soft { background: var(--surface-soft); max-width: none; padding-left: 0; padding-right: 0; }
.band.soft > .inner { max-width: var(--max); margin: 0 auto; padding: 0 32px; }
.band.white { background: var(--canvas); max-width: none; padding-left: 0; padding-right: 0; }
.band.white > .inner { max-width: var(--max); margin: 0 auto; padding: 0 32px; }

h2 {
  margin: 0 0 12px;
  font-size: 36px;
  font-weight: 400;
  letter-spacing: -0.5px;
  line-height: 1.11;
}
h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.33;
}
.section-lede {
  margin: 0 0 32px;
  color: var(--body);
  max-width: 60ch;
}

.key-finding {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  padding: 28px 32px;
  margin: 0 0 28px;
  box-shadow: var(--shadow);
}
.key-finding .label {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 8px;
}
.key-finding p {
  margin: 0;
  font-size: 18px;
  font-weight: 400;
  letter-spacing: -0.2px;
  line-height: 1.4;
  max-width: 50ch;
}

.viz-card {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  padding: 28px;
  margin: 0 0 20px;
}
.viz-card .caption {
  margin-top: 14px;
  font-size: 13px;
  color: var(--muted);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--body);
}
.legend i {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-right: 6px;
  vertical-align: middle;
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
@media (max-width: 900px) {
  .grid-3 { grid-template-columns: 1fr; }
}
.feature-card {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  padding: 28px;
}
.badge-pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 14px;
}
.feature-card p {
  margin: 0;
  color: var(--body);
  font-size: 14px;
}
.feature-card .impl {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--hairline-soft);
  color: var(--ink);
}
.feature-card .impl span {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 4px;
}

/* Astryx-inspired data table page */
.table-shell {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  overflow: hidden;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--hairline);
}
.table-toolbar .title { font-weight: 600; font-size: 16px; }
.table-toolbar .hint { font-size: 13px; color: var(--muted); }
table.data {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
table.data th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  padding: 12px 16px;
  border-bottom: 1px solid var(--hairline);
  background: var(--surface-soft);
}
table.data td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--hairline-soft);
  vertical-align: top;
}
table.data tr:last-child td { border-bottom: none; }
table.data .primary { font-weight: 600; color: var(--ink); }
table.data .secondary { font-size: 12px; color: var(--muted); margin-top: 2px; }
table.data .note { color: var(--body); font-size: 13px; }
table.data .mono { font-family: "JetBrains Mono", ui-monospace, monospace; font-weight: 500; font-size: 13px; }
table.data .num { text-align: right; font-variant-numeric: tabular-nums; }
.pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  background: var(--surface-strong);
}
.pill.pass { color: var(--up); background: rgba(5,177,105,.12); }
.pill.partial { color: #9a7b2f; background: rgba(244,176,0,.16); }
.pill.fail { color: var(--down); background: rgba(207,32,47,.1); }
.pill.fail_expected { color: var(--muted); }

.apps td:nth-child(2) { font-weight: 600; }
.fit-strong { color: var(--up); }
.fit-partial { color: #9a7b2f; }
.fit-weak { color: var(--down); }

.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 800px) { .two { grid-template-columns: 1fr; } }
.panel {
  background: var(--canvas);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-xl);
  padding: 28px;
}
.panel ul { margin: 8px 0 0; padding-left: 18px; color: var(--body); }
.panel li { margin-bottom: 6px; }

.cta-dark {
  background: var(--surface-dark);
  color: var(--on-dark);
  max-width: none;
  padding: 72px 32px;
}
.cta-dark .inner { max-width: var(--max); margin: 0 auto; }
.cta-dark h2 { color: var(--on-dark); }
.cta-dark p { color: var(--on-dark-soft); max-width: 56ch; }
.cta-dark ol { color: var(--on-dark); padding-left: 18px; }
.cta-dark li { margin-bottom: 10px; color: var(--on-dark-soft); }
.cta-dark li strong { color: var(--on-dark); }

.footer {
  background: var(--canvas);
  border-top: 1px solid var(--hairline);
  padding: 48px 32px 64px;
}
.footer-inner {
  max-width: var(--max);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 32px;
}
@media (max-width: 800px) { .footer-inner { grid-template-columns: 1fr; } }
.footer h4 { margin: 0 0 10px; font-size: 14px; font-weight: 600; }
.footer p, .footer li { font-size: 13px; color: var(--body); margin: 0 0 8px; }
.legal {
  max-width: var(--max);
  margin: 24px auto 0;
  padding-top: 20px;
  border-top: 1px solid var(--hairline-soft);
  font-size: 12px;
  color: var(--muted);
}
"""


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fmt_int(n: object) -> str:
    if n is None:
        return "—"
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def by_id(results: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in results}


def outcome_bar_svg(n_pass: int, n_partial: int, n_fail: int, n_exp: int) -> str:
    total = max(n_pass + n_partial + n_fail + n_exp, 1)
    width = 560.0
    segs = [
        (n_pass, "#05b169"),
        (n_partial, "#f4b000"),
        (n_fail, "#cf202f"),
        (n_exp, "#7c828a"),
    ]
    parts = []
    x = 0.0
    for count, color in segs:
        w = width * count / total
        if count:
            parts.append(
                f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="28" rx="14" fill="{color}"/>'
                f'<text x="{x + w / 2:.1f}" y="18" text-anchor="middle" fill="#fff" '
                f'font-size="12" font-family="Inter,system-ui,sans-serif" font-weight="600">{count}</text>'
            )
        x += w
    return (
        f'<svg viewBox="0 0 560 28" width="100%" height="36" role="img" '
        f'aria-label="Outcome mix">{"".join(parts)}</svg>'
    )


def timing_svg(index: dict[str, dict]) -> str:
    rows = []
    max_ms = 1
    for rid, _label in TIMING_ORDER:
        r = index.get(rid) or {}
        ms = r.get("elapsed_ms_agent")
        if isinstance(ms, (int, float)) and ms > max_ms:
            max_ms = float(ms)

    bar_max = 320.0
    y = 8
    for rid, label in TIMING_ORDER:
        r = index.get(rid) or {}
        grade = r.get("qc_grade") or "fail"
        color = GRADE_COLOR.get(grade, "#7c828a")
        opacity = "0.5" if grade == "fail_expected" else "1"
        ms = r.get("elapsed_ms_agent")
        if ms is None:
            w = 0
            label_ms = "—"
        else:
            w = max(8, int(round(bar_max * float(ms) / max_ms)))
            label_ms = fmt_int(ms)
        text_x = 260 + w + 12
        rows.append(
            f'<text x="0" y="{y + 14}" fill="#5b616e" font-size="13" '
            f'font-family="Inter,system-ui,sans-serif">{esc(label)}</text>\n'
            f'<rect x="260" y="{y}" width="{w}" height="20" rx="10" fill="{color}" opacity="{opacity}"/>\n'
            f'<text x="{text_x}" y="{y + 14}" fill="#0a0b0d" font-size="13" '
            f'font-family="\'JetBrains Mono\',ui-monospace,monospace" font-weight="500">{label_ms}</text>'
        )
        y += 36
    height = y + 4
    return f'<svg viewBox="0 0 640 {height}" width="100%" height="{height + 20}">\n    ' + "\n    \n".join(rows) + "\n    </svg>"


def table_rows(index: dict[str, dict]) -> str:
    chunks = []
    for rid in TABLE_ORDER:
        r = index.get(rid)
        if not r:
            continue
        grade = r.get("qc_grade") or "fail"
        pill_cls, pill_label = GRADE_PILL.get(grade, ("fail", grade))
        label = DISPLAY.get(rid, rid)
        tier = r.get("tier") or ""
        note = r.get("qc_note") or ""
        chunks.append(
            f"""<tr>
      <td><div class="primary">{esc(label)}</div><div class="secondary">{esc(tier)}</div></td>
      <td><span class="pill {pill_cls}">{esc(pill_label)}</span></td>
      <td class="mono num">{fmt_int(r.get("elapsed_ms_agent"))}</td>
      <td class="mono num">{fmt_int(r.get("actions"))}</td>
      <td class="note">{esc(note)}</td>
    </tr>"""
        )
    return "".join(chunks)


def render(qc: dict, *, date_label: str = "17 Sep 2026") -> str:
    n_pass = int(qc.get("qc_pass") or 0)
    n_partial = int(qc.get("qc_partial") or 0)
    n_fail = int(qc.get("qc_fail") or 0)
    n_exp = int(qc.get("qc_fail_expected") or 0)
    results = qc.get("results") or []
    index = by_id(results)
    n = len(results) or (n_pass + n_partial + n_fail + n_exp)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Jev Ultrafast — Research Navigation Evaluation</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet"/>
<style>
{CSS}
</style>
</head>
<body>
  <nav class="topnav">
    <div class="brand">Research Eval <span>·</span> Jev Ultrafast</div>
    <div class="topnav-meta">
      <span>{esc(date_label)}</span>
      <span>QC · Chief of Staff</span>
      <a class="pill-cta" href="#results">View results</a>
    </div>
  </nav>

  <header class="hero">
    <div class="hero-inner">
      <div>
        <div class="eyebrow">Technology evaluation · Not investment research</div>
        <h1>Where a research browser helps — and where it stops</h1>
        <p class="lede">Goal-driven navigation for literature, macro data, and filings — scored with independent verification, plus stress cases a careful researcher would expect to fail.</p>
      </div>
      <div class="stat-stack" aria-label="Session scorecard">
        <div class="stat"><div class="n up">{n_pass}</div><div class="l">QC passes</div></div>
        <div class="stat"><div class="n warn">{n_partial}</div><div class="l">Partials</div></div>
        <div class="stat"><div class="n down">{n_fail}</div><div class="l">Unexpected misses</div></div>
        <div class="stat"><div class="n">{n_exp}</div><div class="l">Expected fails hit</div></div>
      </div>
    </div>
  </header>

  <section class="band white"><div class="inner">
    <h2>Executive takeaway</h2>
    <p class="section-lede">Eleven live research-navigation cases on a Grok Bot machine. Auto-scores that celebrated blocked listing pages were reversed under human QC.</p>
    <div class="key-finding">
      <div class="label">Key finding</div>
      <p>Jev is already a strong <em>hands</em> layer when the destination is structured and known. It is not yet a reliable general literature-discovery or download agent. Analytical judgment stays with the researcher — or Quant’s brain suite — after the page lands.</p>
    </div>
    <div class="viz-card">
      {outcome_bar_svg(n_pass, n_partial, n_fail, n_exp)}
      <div class="legend">
        <span><i style="background:#05b169"></i>Pass</span>
        <span><i style="background:#f4b000"></i>Partial</span>
        <span><i style="background:#cf202f"></i>Miss</span>
        <span><i style="background:#7c828a"></i>Expected fail</span>
      </div>
      <div class="caption">Exhibit 1 · Outcome mix after QC (n={n})</div>
    </div>
  </div></section>

  <section class="band soft"><div class="inner">
    <h2>Findings</h2>
    <p class="section-lede">Each finding leads a card; the implication sits under a hairline — Astryx-style detail blocks, Coinbase card radius.</p>
    <div class="grid-3">
    <article class="feature-card">
      <div class="badge-pill">Finding A</div>
      <h3>Known identifiers win</h3>
      <p>DOI, FRED series, EDGAR CIK, and exact encyclopedia titles land cleanly — often in well under five seconds.</p>
      <p class="impl"><span>Implication</span>Prefer Jev when the destination is already named.</p>
    </article>
    <article class="feature-card">
      <div class="badge-pill">Finding B</div>
      <h3>Open discovery still stalls</h3>
      <p>Scholar reaches results then blocks; arXiv hit a model-call budget; NBER and Crossref stalled on listing/home pages.</p>
      <p class="impl"><span>Implication</span>Do not trust Jev alone for literature discovery → cite landing.</p>
    </article>
    <article class="feature-card">
      <div class="badge-pill">Finding C</div>
      <h3>Predicted walls calibrated</h3>
      <p>Upload, Scholar→PDF, and chart CSV export failed as expected — matching MVP limits and earlier Flights/Amazon/Cloudflare results.</p>
      <p class="impl"><span>Implication</span>Route downloads and unsupported modalities elsewhere.</p>
    </article></div>
  </div></section>

  <section class="band white"><div class="inner">
    <h2>Evidence · timing</h2>
    <p class="section-lede">Agent-reported elapsed milliseconds. Semantic green/amber/red are text and bar fills only — never button chrome.</p>
    <div class="viz-card">
      {timing_svg(index)}
      <div class="caption">Exhibit 2 · Agent elapsed time (ms). Expected fails drawn at reduced opacity.</div>
    </div>
  </div></section>

  <section class="band soft" id="results"><div class="inner">
    <h2>Results table</h2>
    <p class="section-lede">Convention-first data table: primary label, status pill, tabular mono metrics, QC note.</p>
    <div class="table-shell">
      <div class="table-toolbar">
        <div class="title">Research browser cases</div>
        <div class="hint">Graded by Chief of Staff</div>
      </div>
      <table class="data">
        <thead>
          <tr>
            <th>Case</th>
            <th>Grade</th>
            <th style="text-align:right">Agent ms</th>
            <th style="text-align:right">Actions</th>
            <th>QC note</th>
          </tr>
        </thead>
        <tbody>{table_rows(index)}</tbody>
      </table>
    </div>
    <p class="caption" style="font-size:13px;color:var(--muted);margin-top:12px">Exhibit 3 · Case-level outcomes</p>
  </div></section>

  <section class="band white"><div class="inner">
    <h2>Application map</h2>
    <div class="table-shell">
      <table class="data apps">
        <thead><tr><th>Research job</th><th>Fit</th><th>Recommendation</th></tr></thead>
        <tbody>
<tr><td>Open known DOI / publisher page</td><td class='fit-strong'>Strong</td><td>Prefer Jev</td></tr><tr><td>FRED / clean macro portals</td><td class='fit-strong'>Strong</td><td>Prefer Jev</td></tr><tr><td>EDGAR company → filings</td><td class='fit-strong'>Strong</td><td>Prefer Jev</td></tr><tr><td>Encyclopedia disambiguation</td><td class='fit-strong'>Strong</td><td>Prefer Jev</td></tr><tr><td>Scholar query → results</td><td class='fit-partial'>Partial</td><td>Jev + verify / open cite</td></tr><tr><td>arXiv / NBER / Crossref discovery</td><td class='fit-weak'>Weak (session)</td><td>Fallback or direct URL</td></tr><tr><td>PDF download / upload</td><td class='fit-weak'>Out of scope</td><td>Do not use Jev</td></tr><tr><td>Chart UI → CSV export</td><td class='fit-weak'>Wall</td><td>API or manual</td></tr><tr><td>Cite / leakage / forecast eval</td><td class=''>Brain layer</td><td>Quant suite after landing</td></tr>
        </tbody>
      </table>
    </div>
    <p style="font-size:13px;color:var(--muted);margin-top:12px">Exhibit 4 · Practical fit for quant / stats workflows</p>
  </div></section>

  <section class="band soft"><div class="inner">
    <h2>Operating model</h2>
    <div class="two">
      <div class="panel">
        <h3>Layer 1 · Hands (Jev)</h3>
        <ul>
          <li>Open known DOI, FRED series, EDGAR CIK, clean articles</li>
          <li>Verify URL / on-page evidence — never trust DONE alone</li>
          <li>On <span class="mono">blocked</span>, hand off to computer-use or human</li>
        </ul>
      </div>
      <div class="panel">
        <h3>Layer 2 · Brain (Quant suite)</h3>
        <ul>
          <li>Citation integrity, leakage, nowcast information sets</li>
          <li>Hard-fail fabricated DOIs</li>
          <li>File: <code>research_evals/analytical_tool_eval_suite_v1.md</code></li>
        </ul>
      </div>
    </div>

  </div></section>

  <section class="cta-dark">
    <div class="inner">
      <h2>Recommendations</h2>
      <p>Guidance over enforcement — defaults that help, escape hatches that don’t fight you.</p>
      <ol>
        <li><strong>Default Jev</strong> for known-URL / portal goals; fall back on blocked, auth, or native GUI.</li>
        <li><strong>Prefer DOI and direct series links</strong> over open-ended Scholar loops until discovery→landing is stable.</li>
        <li><strong>Always verify</strong> final URL/text before citing or scoring.</li>
        <li><strong>Keep Quant’s analytical suite</strong> as the post-navigation quality bar.</li>
      </ol>
    </div>
  </section>

  <footer class="footer">
    <div class="footer-inner">
      <div>
        <h4>Design system notes</h4>
        <p>Visual language follows <a href="https://github.com/VoltAgent/awesome-claude-design">VoltAgent/awesome-claude-design</a> via the Coinbase <code>DESIGN.md</code> (institutional white canvas, scarce blue accent, weight-400 display via Inter substitutes, pill CTAs, 24px cards).</p>
        <p>Layout patterns borrow Astryx conventions from <a href="https://github.com/facebook/astryx">facebook/astryx</a>: table-page shell, detail cards, semantic up/down as text color only, strong documented structure for humans and agents.</p>
      </div>
      <div>
        <h4>Artifacts</h4>
        <p>Upstream: <a href="https://github.com/browser-use/jev-ultrafast">browser-use/jev-ultrafast</a></p>
        <p>Case JSON / QC: <code>fixtures/qc_rescored.json</code></p>
        <p>Harness: <code>jev-research-eval</code> (this package)</p>
      </div>
    </div>
    <div class="legal">
      This note evaluates browser-automation tooling for internal research workflows. It is not investment advice and not affiliated with Coinbase, Meta/Astryx, or Goldman Sachs. Timings are session-specific ({esc(date_label)}). DESIGN.md inspiration for educational UI consistency only.
    </div>
  </footer>
</body>
</html>
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--date", default="17 Sep 2026")
    args = p.parse_args()
    qc = json.loads(args.input.read_text(encoding="utf-8"))
    html_out = render(qc, date_label=args.date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_out, encoding="utf-8")
    print(f"Wrote {args.output} ({len(html_out.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
