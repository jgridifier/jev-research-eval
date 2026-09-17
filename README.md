# jev-research-eval

Reproducible **evaluation harness** for Jared’s Jev Ultrafast research-browser
session (17 Sep 2026): 11 baseline cases (R1–R11), human + quant **stress suites**
(S1–S10, QS1–QS8+QS7b), CoS-locked QC grades, the v4 HTML field note, and research
notebooks (v1 baseline / **v2** baseline+stress) with per-step Trace reports.

This is **not** a fork of Jev. It drives an upstream checkout of
[browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) and
regenerates the report from `fixtures/qc_rescored.json`.

**Pinned upstream commit:** `452c1ad2dd628008f1d5608f28158d76e49e6cc0`  
(`452c1ad Reduce browser round trips and record a 7-second Flights demo`)

## Layout

```
jev-research-eval/
  README.md                 # this file
  REPRODUCE.md              # full end-to-end checklist
  LICENSE                   # MIT (harness only; not a jev fork)
  .gitignore
  cases/
    research_browser_v1.yaml
    stress_human_workflows_v1.yaml      # S1–S10 human multi-hop stress
    stress_quant_v2.yaml                # QS1–QS8+QS7b quant/ops stress
  fixtures/
    qc_rescored.json                    # baseline R1–R11 QC (+ history)
    cases_with_traces.json              # slim R* traces for notebook
    stress_qc_rescored.json             # CoS-locked stress QC + full history
    stress_cases_with_traces.json       # slim S*/QS* traces for notebook v2
    JEV_RESEARCH_FIELD_NOTE_v4.html     # published field-note snapshot
    JEV_RESEARCH_NOTEBOOK_v1.html       # baseline drill-down notebook
    JEV_RESEARCH_NOTEBOOK_v2.html       # baseline + stress suites + viz
  design/
    DESIGN.md               # Coinbase-inspired tokens (educational)
    DESIGN_SOURCES.md
  scripts/
    extract_cases.py        # YAML ← qc_rescored.json
    run_suite.py            # live suite via run_goal_full.py (full history)
    run_goal_full.py        # Agent wrapper — writes complete history[]
    apply_qc.py             # merge auto results + grades → qc_rescored.json
    build_stress_fixtures.py # stress QC lock + slim traces ← results/
    generate_report_v4.py   # field-note HTML ← qc_rescored.json
    generate_notebook_v1.py # notebook v1 ← baseline QC + traces
    generate_notebook_v2.py # notebook v2 ← baseline + stress + viz
  results/                  # runtime outputs (gitignored run_*/); e.g.
                            #   run_notebook_traces/, run_stress_human_v1/,
                            #   run_stress_quant_v2/
  docs/METHODOLOGY.md
```

## Quick start

### A. Regenerate the field note (offline)

No browser or API keys:

```bash
python scripts/generate_report_v4.py \
  --input fixtures/qc_rescored.json \
  --output /tmp/jev_note_regen.html
```

Expect file size > 20KB and the heading *Where a research browser helps*.

### A2. Regenerate the research notebook (offline)

Static interactive HTML — click each experiment for dials + Trace timeline.
Prefers richer histories from `results/run_notebook_traces/` when present,
then `fixtures/cases_with_traces.json`, then `history` / `history_tail` on the QC file.
**Does not run the agent from the page.**

```bash
python scripts/generate_notebook_v1.py \
  --input fixtures/qc_rescored.json \
  --output fixtures/JEV_RESEARCH_NOTEBOOK_v1.html
```

Expect file size > 40KB, a case id such as `R2_doi_spelta_ot`, and the word *Trace*.

### A3. Regenerate the stress notebook (v2, offline)

Includes baseline R1–R11 **plus** human stress (`results/run_stress_human_v1/`,
S1–S10) and quant stress (`results/run_stress_quant_v2/`, QS1–QS8+QS7b), with
outcome-mix bars, action-count charts, budget-hit badges, and full traces.
Prefers `fixtures/stress_qc_rescored.json` + `fixtures/stress_cases_with_traces.json`
(CoS-locked grades). **Does not run the agent from the page.**

```bash
python scripts/build_stress_fixtures.py   # optional: rebuild from results/
python scripts/generate_notebook_v2.py   --output fixtures/JEV_RESEARCH_NOTEBOOK_v2.html
```

Open [`fixtures/JEV_RESEARCH_NOTEBOOK_v2.html`](./fixtures/JEV_RESEARCH_NOTEBOOK_v2.html).

### B. Re-run the live suite (full history for notebook traces)

1. Clone/checkout jev-ultrafast at the pin above; `uv sync`.
2. Chrome with CDP (`BU_CDP_URL`, often `http://127.0.0.1:9224`).
3. Export secrets (never commit):

   - `TYPESAFE_API_KEY`
   - `TEXT_MODEL_API_KEY`
   - `BU_CDP_URL`

4. Run:

```bash
export JEV_ULTRAFAST_ROOT=/path/to/jev-ultrafast
python scripts/run_suite.py \
  --jev-root "$JEV_ULTRAFAST_ROOT" \
  --cases cases/research_browser_v1.yaml \
  --out results/latest
```

Single case: `--id R2_doi_spelta_ot`.

5. Human QC → `apply_qc.py` → `generate_report_v4.py` / `generate_notebook_v1.py` / `generate_notebook_v2.py`.
   Stress suites: `run_suite.py --cases cases/stress_human_workflows_v1.yaml`
   or `cases/stress_quant_v2.yaml`, then `build_stress_fixtures.py`.

For notebook traces, `run_suite.py` calls `scripts/run_goal_full.py` (complete `history`, not only a tail).
Example out dir used for the notebook merge: `results/run_notebook_traces/`.

Step-by-step: **[REPRODUCE.md](./REPRODUCE.md)**. Grading rules: **[docs/METHODOLOGY.md](./docs/METHODOLOGY.md)**.

## Environment

| Variable | Role |
|----------|------|
| `TYPESAFE_API_KEY` | Jev / Typesafe model |
| `TEXT_MODEL_API_KEY` | Text helper (e.g. OpenRouter) |
| `BU_CDP_URL` | Chrome DevTools endpoint |
| `JEV_ULTRAFAST_ROOT` | Override default `/workspace/jev-ultrafast` |

Optional: `TEXT_MODEL_BASE_URL`, `TEXT_MODEL`, `TYPESAFE_MODEL` (see upstream `.env` examples).

`run_suite.py` exits non-zero if any **non–expect_fail** case fails hard, but
still writes every case JSON + `summary.json`.

## Dependencies

- Python 3.10+ (stdlib for report generation).
- Optional: `pyyaml` for loading `cases/*.yaml` (`pip install pyyaml`).
- Upstream: `uv`, Chrome, API keys — only for live suite re-runs.

## Upstream

- https://github.com/browser-use/jev-ultrafast @ `452c1ad2dd628008f1d5608f28158d76e49e6cc0`
- Upstream single-goal runner: `scripts/run_goal.py` (history_tail only)
- Package full-history runner: `scripts/run_goal_full.py` (complete `history` for notebook Traces)

## Disclaimer

Not affiliated with Coinbase, Meta/Astryx, Goldman Sachs, or browser-use beyond
use of public open-source software. **Not investment advice.** Design tokens in
`design/` are for educational UI consistency only.
