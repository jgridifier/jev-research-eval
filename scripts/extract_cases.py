#!/usr/bin/env python3
"""Rebuild cases/research_browser_v1.yaml from fixtures/qc_rescored.json (or --input).

Does NOT include history_tail, tokens, or other runtime noise — only case definitions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "fixtures" / "qc_rescored.json"
DEFAULT_OUT = ROOT / "cases" / "research_browser_v1.yaml"

# Optional success URL substrings used by run_suite / run_goal when present.
# Kept here so re-extract from QC JSON preserves them if YAML already had them.
KNOWN_SUCCESS_SUBSTR: dict[str, str] = {
    "R2_doi_spelta_ot": "jrsssa",
    "R4_fred_indpro": "INDPRO",
    "R5_edgar_company_search": "CIK=320193",
    "R8_wikipedia_disambiguation": "Kalman_filter",
}

CASE_KEYS = ("id", "tier", "expect_fail", "why", "url", "goal")


def dump_yaml(data: dict) -> str:
    """Minimal YAML dumper (no PyYAML required) for our simple case schema."""
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)

    lines: list[str] = []
    lines.append(f"suite: {data['suite']}")
    lines.append(f"version: {data['version']}")
    lines.append(f"description: {json.dumps(data['description'])}")
    lines.append("cases:")
    for case in data["cases"]:
        lines.append(f"  - id: {case['id']}")
        lines.append(f"    tier: {case['tier']}")
        lines.append(f"    expect_fail: {'true' if case['expect_fail'] else 'false'}")
        lines.append(f"    why: {json.dumps(case['why'], ensure_ascii=False)}")
        lines.append(f"    url: {json.dumps(case['url'])}")
        lines.append(f"    goal: {json.dumps(case['goal'], ensure_ascii=False)}")
        if case.get("success_substr"):
            lines.append(f"    success_substr: {json.dumps(case['success_substr'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def extract(qc: dict) -> dict:
    cases = []
    for r in qc.get("results", []):
        case = {k: r[k] for k in CASE_KEYS if k in r}
        sid = case.get("id", "")
        if sid in KNOWN_SUCCESS_SUBSTR:
            case["success_substr"] = KNOWN_SUCCESS_SUBSTR[sid]
        # Never carry history / tokens
        cases.append(case)
    return {
        "suite": "research_browser",
        "version": "v1",
        "description": (
            "Eleven live research-navigation cases for Jev Ultrafast "
            "(literature, macro data, filings + expected-fail stress)."
        ),
        "cases": cases,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    qc = json.loads(args.input.read_text(encoding="utf-8"))
    data = extract(qc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dump_yaml(data), encoding="utf-8")
    print(f"Wrote {len(data['cases'])} cases → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
