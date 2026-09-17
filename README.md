# jev-research-eval

Reproducible **evaluation harness** for Jared’s Jev Ultrafast research-browser
session (17 Sep 2026): 11 cases (R1–R11), human QC grades, and the v4 HTML field note.

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
  cases/research_browser_v1.yaml
  fixtures/
    qc_rescored.json                    # canonical QC grades + timings
    JEV_RESEARCH_FIELD_NOTE_v4.html     # published snapshot
  design/
    DESIGN.md               # Coinbase-inspired tokens (educational)
    DESIGN_SOURCES.md
  scripts/
    extract_cases.py        # YAML ← qc_rescored.json
    run_suite.py            # live suite via jev run_goal.py
    apply_qc.py             # merge auto results + grades → qc_rescored.json
    generate_report_v4.py   # HTML ← qc_rescored.json
  results/                  # runtime outputs (.gitkeep only in git)
  docs/METHODOLOGY.md
```

## Quick start

### A. Regenerate the report (offline)

No browser or API keys:

```bash
python scripts/generate_report_v4.py \
  --input fixtures/qc_rescored.json \
  --output /tmp/jev_note_regen.html
```

Expect file size > 20KB and the heading *Where a research browser helps*.

### B. Re-run the live suite

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

5. Human QC → `apply_qc.py` → `generate_report_v4.py`.

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
- Single-goal runner: `scripts/run_goal.py`

## Disclaimer

Not affiliated with Coinbase, Meta/Astryx, Goldman Sachs, or browser-use beyond
use of public open-source software. **Not investment advice.** Design tokens in
`design/` are for educational UI consistency only.
