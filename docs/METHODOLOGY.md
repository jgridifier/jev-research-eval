# Methodology — research browser evaluation (v1)

Session date: **17 Sep 2026**. Runner: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) @ `452c1ad2dd628008f1d5608f28158d76e49e6cc0`.

## What we measure

Goal-driven **browser navigation** for research workflows: literature landing,
macro data portals, SEC filings, encyclopedia disambiguation, plus intentional
stress cases outside Jev’s MVP.

We do **not** score analytical judgment (citation integrity, leakage, forecast
evaluation). That stays in a separate “brain” suite after the page lands.

## Case tiers

| Tier | Intent |
|------|--------|
| `paper_search` | Reach a specific paper / article / abstract page |
| `data_portal` | Land on a known series or filings list |
| `paper_compare` | Bibliographic metadata lookup (e.g. Crossref) |
| `expect_fail` | Predicted wall (upload, PDF maze, complex widget) |

Each case in `cases/research_browser_v1.yaml` has: `id`, `tier`, `expect_fail`,
`why`, `url`, `goal`, optional `success_substr`.

## Auto vs human QC

1. **Auto run** (`scripts/run_suite.py`) calls `jev-ultrafast/scripts/run_goal.py`
   and records status, elapsed ms, actions, final URL, short history tail.
2. **Auto “ok”** means `run_goal` exit 0 (agent `done` + optional URL substring).
   Listing pages that merely contain keywords can be over-credited.
3. **Human QC** grades each case independently of auto-ok:
   - `pass` — destination clearly achieved
   - `partial` — useful progress but incomplete (e.g. Scholar results without cite landing)
   - `fail` — unexpected miss
   - `fail_expected` — stress case failed as predicted (`expect_fail: true`)
4. Merge with `scripts/apply_qc.py` → `fixtures/qc_rescored.json`.
5. Report with `scripts/generate_report_v4.py`.

## Expected-fail rationale

| Case | Why expected to fail |
|------|----------------------|
| R9 PDF upload / convert | File uploads out of Jev MVP |
| R10 Scholar → PDF download | Cite/paywall/interstitial maze |
| R11 OWID chart → CSV | Nested JS widget + download menu |

A surprise **pass** on an expect-fail case is noteworthy (product regression /
capability gain), not a QC error.

## Exit / scoring rules for re-runs

- Suite writes **all** case JSON + `summary.json` even when some fail.
- Process exit **non-zero** if any **non–expect_fail** case fails hard
  (`ok: false`). Expected fails do not fail the suite exit code.
- Never treat model `DONE` alone as proof — verify URL / on-page evidence
  (and optional `success_substr`).

## Environment

Required for live runs: `TYPESAFE_API_KEY`, `TEXT_MODEL_API_KEY`, `BU_CDP_URL`
(Chrome CDP). See root `README.md` and `REPRODUCE.md`. Secrets never committed.

## Report regeneration (offline)

QC grades + timings in `fixtures/qc_rescored.json` are enough to regenerate the
HTML field note without a browser or API keys:

```bash
python scripts/generate_report_v4.py \
  --input fixtures/qc_rescored.json \
  --output /tmp/jev_note_regen.html
```
