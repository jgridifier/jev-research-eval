#!/usr/bin/env python3
"""Merge auto suite results with human QC grades → qc_rescored.json.

Grades file (YAML or JSON) format:
  grades:
    - id: R1_scholar_giannone_nowcast
      qc_grade: partial   # pass | partial | fail | fail_expected
      qc_note: "..."

Or a full qc_rescored.json can be used as --grades to re-stamp notes onto a new run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def load_any(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise SystemExit("pip install pyyaml to load grades YAML")
        return yaml.safe_load(text) or {}
    return json.loads(text)


def index_grades(grades_doc: dict) -> dict[str, dict]:
    """Accept either {grades: [...]} or qc_rescored {results: [...]}."""
    out: dict[str, dict] = {}
    if "grades" in grades_doc:
        for g in grades_doc["grades"]:
            out[g["id"]] = g
    elif "results" in grades_doc:
        for r in grades_doc["results"]:
            if "qc_grade" in r or "qc_note" in r:
                out[r["id"]] = {
                    "id": r["id"],
                    "qc_grade": r.get("qc_grade"),
                    "qc_note": r.get("qc_note"),
                }
    else:
        raise SystemExit("grades file needs 'grades' list or qc 'results' with qc_grade")
    return out


def tally(results: list[dict]) -> dict:
    counts = {"qc_pass": 0, "qc_partial": 0, "qc_fail": 0, "qc_fail_expected": 0}
    for r in results:
        g = r.get("qc_grade")
        if g == "pass":
            counts["qc_pass"] += 1
        elif g == "partial":
            counts["qc_partial"] += 1
        elif g == "fail_expected":
            counts["qc_fail_expected"] += 1
        elif g == "fail":
            counts["qc_fail"] += 1
    return counts


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--results",
        type=Path,
        required=True,
        help="Path to suite summary.json OR a directory containing summary.json / *.json",
    )
    p.add_argument(
        "--grades",
        type=Path,
        default=ROOT / "fixtures" / "qc_rescored.json",
        help="Human grades YAML/JSON or prior qc_rescored.json",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "fixtures" / "qc_rescored.json",
    )
    args = p.parse_args()

    results_path = args.results
    if results_path.is_dir():
        summary_path = results_path / "summary.json"
        if not summary_path.is_file():
            raise SystemExit(f"No summary.json in {results_path}")
        auto = load_any(summary_path)
    else:
        auto = load_any(results_path)

    auto_results = auto.get("results") or []
    # Prefer per-case files when merging from a run dir (full history_tail)
    if results_path.is_dir():
        enriched = []
        for r in auto_results:
            case_file = results_path / f"{r['id']}.json"
            if case_file.is_file():
                enriched.append(load_any(case_file))
            else:
                enriched.append(r)
        auto_results = enriched

    grades = index_grades(load_any(args.grades))
    merged = []
    missing = []
    for r in auto_results:
        rid = r["id"]
        row = dict(r)
        g = grades.get(rid)
        if not g:
            missing.append(rid)
            # Heuristic default if expect_fail
            if row.get("expect_fail"):
                row.setdefault("qc_grade", "fail_expected")
                row.setdefault("qc_note", "Expected fail (no human note yet)")
            else:
                row.setdefault("qc_grade", "fail" if not row.get("ok") else "pass")
                row.setdefault("qc_note", "Auto grade — needs human QC")
        else:
            row["qc_grade"] = g.get("qc_grade", row.get("qc_grade"))
            row["qc_note"] = g.get("qc_note", row.get("qc_note"))
        # Strip nothing required — keep history_tail if present for fixtures
        merged.append(row)

    if missing:
        print(f"Warning: no grades for {missing} — used heuristics")

    out_doc = {**tally(merged), "results": merged}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.out}  pass={out_doc['qc_pass']} partial={out_doc['qc_partial']} "
        f"fail={out_doc['qc_fail']} fail_expected={out_doc['qc_fail_expected']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
