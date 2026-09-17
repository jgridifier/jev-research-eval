# Reproduce — full suite + report

End-to-end checklist so a clean machine can re-run the 17 Sep 2026 research-browser
evaluation and regenerate the v4 HTML note **without tribal knowledge**.

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

Outputs: `results/latest/<id>.json` + `results/latest/summary.json`.

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

## 7. Regenerate the v4 HTML report

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
| Live run JSON | `run_suite.py` + CDP + secrets |
| QC grades file | human edit + `apply_qc.py` |
| HTML field note | `generate_report_v4.py` from QC JSON |

Fixtures in-repo (`qc_rescored.json`, published HTML) let you regenerate the
report immediately; live re-runs need Chrome + API keys.
