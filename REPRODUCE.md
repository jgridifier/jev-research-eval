# Reproduce — full suite + report

End-to-end checklist so a clean machine can re-run the 17 Sep 2026 research-browser
evaluation and regenerate the v4 HTML note + research notebook **without tribal knowledge**.

## 0. This package

```bash
cd /path/to/jev-research-eval
# optional: pip install pyyaml   # for YAML case loading
```

## 1. Pin and install jev-ultrafast

```bash
git clone https://github.com/browser-use/jev-ultrafast.git
cd jev-ultrafast
git checkout 452c1ad2dd628008f1d5608f28158d76e49e6cc0
uv sync
```

On the Grok Bot box the clone often already lives at `/workspace/jev-ultrafast`
on that commit. Point the harness with:

```bash
export JEV_ULTRAFAST_ROOT=/workspace/jev-ultrafast   # or your clone path
```

## 2. Chrome CDP

Start Chrome with remote debugging (box default port **9224**):

```bash
export BU_CDP_URL=http://127.0.0.1:9224
cd "$JEV_ULTRAFAST_ROOT"
uv run browser-harness --doctor   # chrome + daemon + connections
```

## 3. Secrets (env only — never commit)

```bash
export TYPESAFE_API_KEY=…          # Typesafe / Jev
export TEXT_MODEL_API_KEY=…        # OpenRouter (or configured text model)
# Optional text-model knobs (match session .env):
# export TEXT_MODEL_BASE_URL=https://openrouter.ai/api/v1
# export TEXT_MODEL=inception/mercury-2.5
# export TYPESAFE_MODEL=jev-latest
```

Prefer `uv run --env-file .env …` inside jev-ultrafast; keep `.env` gitignored.

## 4. Dry-run the harness wiring

```bash
cd /path/to/jev-research-eval
python scripts/run_suite.py --dry-run --id R2_doi_spelta_ot
```

## 5. Run the suite

All 11 cases:

```bash
python scripts/run_suite.py \
  --jev-root "$JEV_ULTRAFAST_ROOT" \
  --cases cases/research_browser_v1.yaml \
  --out results/latest
```

One case:

```bash
python scripts/run_suite.py --id R4_fred_indpro --out results/latest
```

Outputs: `results/latest/<id>.json` (includes full `history` + `history_tail`) + `results/latest/summary.json`.

`run_suite.py` invokes `scripts/run_goal_full.py` so notebook Traces can use the complete action list
(upstream `jev-ultrafast/scripts/run_goal.py` only keeps a 5-step tail).

Exit code is non-zero if any **unexpected** (non `expect_fail`) case fails hard;
all results are still written.

## 6. Human QC → merge grades

Edit grades (YAML or reuse prior QC file), then:

```bash
python scripts/apply_qc.py \
  --results results/latest \
  --grades fixtures/qc_rescored.json \
  --out fixtures/qc_rescored.json
```

For a fresh human pass, create e.g. `grades.yaml`:

```yaml
grades:
  - id: R2_doi_spelta_ot
    qc_grade: pass
    qc_note: "DOI resolved to article page."
  # …
```

See `docs/METHODOLOGY.md` for grade definitions.

## 7. Regenerate the v4 HTML field note

Offline — no CDP / API keys required if QC JSON is present:

```bash
python scripts/generate_report_v4.py \
  --input fixtures/qc_rescored.json \
  --output fixtures/JEV_RESEARCH_FIELD_NOTE_v4.html
```

Sanity check:

```bash
python -c "from pathlib import Path; t=Path('fixtures/JEV_RESEARCH_FIELD_NOTE_v4.html').read_text(); assert len(t)>20000 and 'Where a research browser helps' in t"
```

Published snapshot also kept under `fixtures/JEV_RESEARCH_FIELD_NOTE_v4.html`.

## 7b. Regenerate the interactive research notebook

Static viewer (HTML+CSS+JS). Embeds case JSON in `#notebook-data`. Click a case
(`#case-R2_doi_spelta_ot`, …) for hypothesis, protocol, outcome dials, QC note,
and an ordered **Trace report** of each history step.

Trace preference order when regenerating:

1. `results/run_notebook_traces/*.json` full `history` (live CLI dumps)
2. `fixtures/cases_with_traces.json`
3. `history` / `history_tail` on `fixtures/qc_rescored.json`

```bash
# After a full-history suite (optional but richer traces):
python scripts/run_suite.py \
  --jev-root "$JEV_ULTRAFAST_ROOT" \
  --cases cases/research_browser_v1.yaml \
  --out results/run_notebook_traces

python scripts/generate_notebook_v1.py \
  --input fixtures/qc_rescored.json \
  --traces-dir results/run_notebook_traces \
  --output fixtures/JEV_RESEARCH_NOTEBOOK_v1.html
```

Offline-only (fixtures already present):

```bash
python scripts/generate_notebook_v1.py
```

Sanity check:

```bash
python -c "from pathlib import Path; t=Path('fixtures/JEV_RESEARCH_NOTEBOOK_v1.html').read_text(); assert len(t)>40000 and 'R2_doi_spelta_ot' in t and 'Trace' in t"
```

The notebook **never** launches Agent/CDP from the browser — it only inspects dumps.

## 8. Optional — rebuild case YAML from QC

```bash
python scripts/extract_cases.py \
  --input fixtures/qc_rescored.json \
  --out cases/research_browser_v1.yaml
```

## What “fully reproducible” means here

| Artifact | How to rebuild |
|----------|----------------|
| Case definitions | `extract_cases.py` or edit YAML |
| Live run JSON (full history) | `run_suite.py` → `run_goal_full.py` + CDP + secrets |
| QC grades file | human edit + `apply_qc.py` |
| HTML field note | `generate_report_v4.py` from QC JSON |
| Research notebook | `generate_notebook_v1.py` from QC + optional `results/run_notebook_traces/` |

Fixtures in-repo (`qc_rescored.json`, `cases_with_traces.json`, published HTML)
let you regenerate the field note and notebook immediately; live re-runs need
Chrome + API keys and produce fuller Trace timelines when history is dumped in full.
