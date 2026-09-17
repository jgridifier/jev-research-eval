#!/usr/bin/env python3
"""Run one natural-language browser goal via Jev Ultrafast; save FULL action history.

Mirrors jev-ultrafast/scripts/run_goal.py but writes the complete history list
(not only a tail) for research-notebook traces.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
JEV_ROOT = Path(
    os.environ.get("JEV_ULTRAFAST_ROOT", "/workspace/jev-ultrafast")
).resolve()
sys.path.insert(0, str(JEV_ROOT))


def _load_dotenv(path: Path) -> None:
    """Load KEY=VAL from .env into os.environ if not already set."""
    if not path.is_file():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(path, override=False)
        return
    except ImportError:
        pass
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv(JEV_ROOT / ".env")

from jev_ultrafast import Agent  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(
        description="Jev Ultrafast single-goal runner (full history)"
    )
    p.add_argument("--url", required=True)
    p.add_argument("--goal", required=True, action="append")
    p.add_argument("--json-out", type=Path, help="Write final state summary JSON")
    p.add_argument("--success-substr", help="Optional URL substring required for exit 0")
    args = p.parse_args()

    if not os.environ.get("TYPESAFE_API_KEY") or not os.environ.get("TEXT_MODEL_API_KEY"):
        print(
            "Missing TYPESAFE_API_KEY or TEXT_MODEL_API_KEY in env / .env",
            file=sys.stderr,
        )
        return 2
    if not os.environ.get("BU_CDP_URL"):
        os.environ.setdefault("BU_CDP_URL", "http://127.0.0.1:9224")

    last = None
    try:
        with Agent(args.url, args.goal) as agent:
            for state in agent.run():
                last = state
                print(
                    f"{state['elapsed_ms']:>5} ms  {len(state['history'])} actions  {state['status']}",
                    flush=True,
                )
    except Exception as e:  # noqa: BLE001
        # Still write partial JSON so the suite can continue
        hist = (last.get("history") if last else None) or []
        final_url = (last or {}).get("page", {}).get("url") if last else None
        summary = {
            "status": (last or {}).get("status"),
            "elapsed_ms": (last or {}).get("elapsed_ms"),
            "actions": len(hist),
            "final_url": final_url,
            "history": hist,
            "history_tail": hist[-5:],
            "error": f"{type(e).__name__}: {e}",
        }
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if last is None:
        return 1
    hist = last.get("history") or []
    final_url = last.get("page", {}).get("url")
    print(final_url or "")
    summary = {
        "status": last.get("status"),
        "elapsed_ms": last.get("elapsed_ms"),
        "actions": len(hist),
        "final_url": final_url,
        "history": hist,
        "history_tail": hist[-5:],
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if last.get("status") == "blocked":
        return 3
    if args.success_substr and (
        not final_url or args.success_substr.lower() not in final_url.lower()
    ):
        return 4
    return 0 if last.get("status") == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
