#!/usr/bin/env python3
"""Run research-browser cases via jev-ultrafast scripts/run_goal.py.

Env (required for live runs):
  TYPESAFE_API_KEY, TEXT_MODEL_API_KEY, BU_CDP_URL

Optional:
  JEV_ULTRAFAST_ROOT  (default /workspace/jev-ultrafast)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def _parse_scalar(raw: str):
    raw = raw.strip()
    if not raw:
        return ""
    if raw in ("true", "True", "yes"):
        return True
    if raw in ("false", "False", "no"):
        return False
    if raw.startswith('"') and raw.endswith('"'):
        return json.loads(raw)
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw.lower() in ("null", "~"):
        return None
    return raw


def _load_simple_cases_yaml(text: str) -> dict:
    """Parse extract_cases-style YAML without PyYAML."""
    data: dict = {"cases": []}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("cases:"):
            continue
        if line.startswith("  - ") or (line.startswith("- ") and not line.startswith("---")):
            if current:
                data["cases"].append(current)
            current = {}
            item = line.lstrip()[2:].strip()  # drop "- "
            if ":" in item:
                k, v = item.split(":", 1)
                current[k.strip()] = _parse_scalar(v)
            continue
        if line.startswith("    ") and current is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            current[k.strip()] = _parse_scalar(v)
            continue
        if not line[0].isspace() and ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = _parse_scalar(v)
    if current:
        data["cases"].append(current)
    return data


def load_cases(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    elif yaml is not None:
        data = yaml.safe_load(text)
    else:
        data = _load_simple_cases_yaml(text)
    return list(data.get("cases") or [])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--jev-root",
        type=Path,
        default=Path(os.environ.get("JEV_ULTRAFAST_ROOT", "/workspace/jev-ultrafast")),
    )
    p.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "cases" / "research_browser_v1.yaml",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output dir (default results/run_<timestamp>/). Use results/latest to overwrite.",
    )
    p.add_argument("--id", action="append", dest="ids", help="Run only this case id (repeatable)")
    p.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter used to invoke run_goal.py",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    return p.parse_args()


def resolve_out(arg: Path | None) -> Path:
    if arg is not None:
        return arg if arg.is_absolute() else ROOT / arg
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ROOT / "results" / f"run_{ts}"


def run_one(
    *,
    case: dict,
    jev_root: Path,
    out_dir: Path,
    python: str,
    dry_run: bool,
) -> dict:
    run_goal = jev_root / "scripts" / "run_goal.py"
    json_out = out_dir / f"{case['id']}.json"
    cmd = [
        python,
        str(run_goal),
        "--url",
        case["url"],
        "--goal",
        case["goal"],
        "--json-out",
        str(json_out),
    ]
    if case.get("success_substr"):
        cmd.extend(["--success-substr", case["success_substr"]])

    record: dict = {
        "id": case["id"],
        "tier": case.get("tier"),
        "expect_fail": bool(case.get("expect_fail")),
        "why": case.get("why"),
        "url": case["url"],
        "goal": case["goal"],
        "success_substr": case.get("success_substr"),
        "cmd": cmd,
        "ok": False,
        "exit_code": None,
        "error": None,
        "final_url": None,
        "status": None,
        "elapsed_ms_agent": None,
        "actions": None,
        "wall_s": None,
        "matched": None,
        "history_tail": None,
    }

    if dry_run:
        print("DRY-RUN:", " ".join(cmd))
        record["ok"] = True
        record["status"] = "dry_run"
        return record

    if not run_goal.is_file():
        record["error"] = f"missing run_goal.py at {run_goal}"
        return record

    t0 = time.perf_counter()
    env = os.environ.copy()
    if not env.get("BU_CDP_URL"):
        env.setdefault("BU_CDP_URL", "http://127.0.0.1:9224")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(jev_root),
            env=env,
            capture_output=True,
            text=True,
        )
        record["exit_code"] = proc.returncode
        record["wall_s"] = round(time.perf_counter() - t0, 3)
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end="" if proc.stderr.endswith("\n") else "\n")

        if json_out.is_file():
            try:
                payload = json.loads(json_out.read_text(encoding="utf-8"))
                record["status"] = payload.get("status")
                record["elapsed_ms_agent"] = payload.get("elapsed_ms")
                record["actions"] = payload.get("actions")
                record["final_url"] = payload.get("final_url")
                record["history_tail"] = payload.get("history_tail")
            except json.JSONDecodeError as e:
                record["error"] = f"bad json-out: {e}"
        else:
            # Still write a stub so results/ is complete
            stub = {
                "status": None,
                "elapsed_ms": None,
                "actions": None,
                "final_url": None,
                "history_tail": None,
                "error": (proc.stderr or proc.stdout or "")[-2000:],
                "exit_code": proc.returncode,
            }
            json_out.write_text(json.dumps(stub, indent=2), encoding="utf-8")
            record["error"] = stub["error"] or f"exit {proc.returncode}, no json-out"

        # Hard success: exit 0 from run_goal (status done + optional substr)
        hard_ok = proc.returncode == 0
        record["ok"] = hard_ok
        if case.get("success_substr") and record.get("final_url"):
            record["matched"] = case["success_substr"].lower() in (record["final_url"] or "").lower()
        else:
            record["matched"] = hard_ok

        # Enrich per-case file with suite metadata
        enriched = {
            "id": case["id"],
            "tier": case.get("tier"),
            "expect_fail": bool(case.get("expect_fail")),
            "why": case.get("why"),
            "url": case["url"],
            "goal": case["goal"],
            "ok": record["ok"],
            "final_url": record["final_url"],
            "status": record["status"],
            "elapsed_ms_agent": record["elapsed_ms_agent"],
            "actions": record["actions"],
            "error": record["error"],
            "history_tail": record["history_tail"],
            "matched": record["matched"],
            "wall_s": record["wall_s"],
            "exit_code": record["exit_code"],
        }
        json_out.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        record["wall_s"] = round(time.perf_counter() - t0, 3)
        record["error"] = str(e)
        json_out.write_text(json.dumps({**record, "history_tail": None}, indent=2), encoding="utf-8")

    return record


def main() -> int:
    args = parse_args()
    cases = load_cases(args.cases)
    if args.ids:
        want = set(args.ids)
        cases = [c for c in cases if c["id"] in want]
        missing = want - {c["id"] for c in cases}
        if missing:
            print(f"Unknown --id: {sorted(missing)}", file=sys.stderr)
            return 2
    if not cases:
        print("No cases to run", file=sys.stderr)
        return 2

    out_dir = resolve_out(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"jev-root: {args.jev_root}")
    print(f"cases:    {args.cases} ({len(cases)})")
    print(f"out:      {out_dir}")
    print(
        "env: TYPESAFE_API_KEY=%s TEXT_MODEL_API_KEY=%s BU_CDP_URL=%s"
        % (
            "set" if os.environ.get("TYPESAFE_API_KEY") else "MISSING",
            "set" if os.environ.get("TEXT_MODEL_API_KEY") else "MISSING",
            os.environ.get("BU_CDP_URL", "(default 9224)"),
        )
    )

    results: list[dict] = []
    unexpected_hard_fails = 0
    for case in cases:
        print(f"\n=== {case['id']} ===")
        rec = run_one(
            case=case,
            jev_root=args.jev_root,
            out_dir=out_dir,
            python=args.python,
            dry_run=args.dry_run,
        )
        results.append(rec)
        # Unexpected hard fail: not expect_fail and agent did not succeed
        if not rec.get("expect_fail") and not rec.get("ok") and not args.dry_run:
            unexpected_hard_fails += 1
            print(f"UNEXPECTED HARD FAIL: {case['id']} status={rec.get('status')} err={rec.get('error')}")

    summary = {
        "n": len(results),
        "passed": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok")),
        "expect_fail_correct": sum(
            1 for r in results if r.get("expect_fail") and not r.get("ok")
        ),
        "expect_fail_surprise_pass": sum(
            1 for r in results if r.get("expect_fail") and r.get("ok")
        ),
        "unexpected_hard_fails": unexpected_hard_fails,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jev_root": str(args.jev_root),
        "cases_file": str(args.cases),
        "results": [
            {
                k: r.get(k)
                for k in (
                    "id",
                    "tier",
                    "expect_fail",
                    "why",
                    "url",
                    "goal",
                    "ok",
                    "final_url",
                    "status",
                    "elapsed_ms_agent",
                    "actions",
                    "error",
                    "matched",
                    "wall_s",
                    "exit_code",
                )
            }
            for r in results
        ],
    }
    # Drop bulky history from summary; keep in per-case files
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out_dir / 'summary.json'}")
    print(
        f"passed={summary['passed']} failed={summary['failed']} "
        f"unexpected_hard_fails={unexpected_hard_fails}"
    )

    if unexpected_hard_fails:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
