"""
FraudLens — Benchmark Re-Runner (Phase 4.1)
============================================
Re-runs all 20 HHG benchmark cases through the LIVE FraudLens investigation pipeline
using the real TigerGraph backend. Replaces previous case JSON files with fresh results.

Run: python scripts/run_benchmarks.py
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
# Ensure repo root is on sys.path so agent/tools/backend modules are importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

CASES_DIR = REPO_ROOT / "cases"
SAMPLE_DIR = REPO_ROOT / "dataset_sample"
DATA_DIR = REPO_ROOT / "data"

CASE_PACK = SAMPLE_DIR / "case_pack.csv" if (SAMPLE_DIR / "case_pack.csv").exists() else DATA_DIR / "case_pack.csv"


def validate_case_json(data: dict) -> dict:
    """Validate a case JSON against the hackathon benchmark schema."""
    issues = []
    required_top = ["case", "sar", "next_best_action", "audit_trail", "benchmark"]
    for field in required_top:
        if field not in data:
            issues.append(f"Missing top-level section: {field}")

    if "case" in data:
        case = data["case"]
        for cf in ["status", "verdict", "fraud_probability", "pattern", "exposure_usd", "evidence"]:
            if cf not in case:
                issues.append(f"Missing case field: {cf}")

    if "sar" in data:
        sar = data["sar"]
        for sf in ["file", "reason"]:
            if sf not in sar:
                issues.append(f"Missing sar field: {sf}")

    if "next_best_action" in data:
        nba = data["next_best_action"]
        for nf in ["primary_action", "actions", "escalation_level"]:
            if nf not in nba:
                issues.append(f"Missing next_best_action field: {nf}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_case_json_from_path(path: Path | str) -> dict:
    """Validate a case JSON file from a path."""
    p = Path(path)
    if not p.exists():
        return {"valid": False, "issues": [f"File does not exist: {p}"]}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return validate_case_json(data)
    except Exception as e:
        return {"valid": False, "issues": [f"JSON parse error: {e}"]}



async def run_single_case(
    case_id: str,
    txn_id: str,
    card_id: str,
    customer_id: str,
    trigger_type: str,
    trigger_risk_score: float | None,
) -> dict:
    """Run a single investigation case through the live pipeline."""
    from agent.orchestrator import Orchestrator

    orch = Orchestrator(cases_dir=str(CASES_DIR))
    events = []
    final_event = {}

    async for event in orch.investigate(
        txn_id=str(txn_id),
        trigger_type=trigger_type,
        card_id=str(card_id) if card_id and str(card_id) != "nan" else None,
        customer_id=str(customer_id) if customer_id and str(customer_id) != "nan" else None,
        trigger_risk_score=float(trigger_risk_score) if trigger_risk_score and not pd.isna(trigger_risk_score) else None,
        case_id=case_id,
    ):
        events.append(event)
        event_type = event.get("type", "")
        msg = event.get("message", "")[:80]
        print(f"    [{event_type:20s}] {msg}")
        if event_type == "complete":
            final_event = event

    return final_event


async def run_all_benchmarks():
    """Run all 20 HHG benchmark cases."""
    print("=" * 70)
    print("FraudLens — Live Benchmark Run (Phase 4.1)")
    print("=" * 70)

    if not CASE_PACK.exists():
        print(f"ERROR: case_pack.csv not found at {CASE_PACK}")
        sys.exit(1)

    df = pd.read_csv(CASE_PACK)
    print(f"Loaded {len(df)} cases from case_pack.csv")

    results = []
    total_start = time.time()

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        txn_id = str(row["flagged_txn_id"])
        card_id = str(row.get("card_id", ""))
        customer_id = str(row.get("customer_id", ""))
        trigger_type = str(row["trigger_type"])
        risk_score = row.get("risk_score", None)

        print(f"\n{'='*60}")
        print(f"Running {case_id} | txn={txn_id} | card={card_id} | trigger={trigger_type}")
        print(f"{'='*60}")

        t0 = time.time()
        try:
            result = await run_single_case(
                case_id=case_id,
                txn_id=txn_id,
                card_id=card_id,
                customer_id=customer_id,
                trigger_type=trigger_type,
                trigger_risk_score=risk_score,
            )
            elapsed = time.time() - t0
            verdict = result.get("verdict", "unknown")
            prob = result.get("fraud_probability", 0.0)
            print(f"  => {case_id}: verdict={verdict} prob={prob:.2f} [{elapsed:.1f}s]")
            results.append({
                "case_id": case_id,
                "verdict": verdict,
                "fraud_probability": prob,
                "elapsed_s": round(elapsed, 2),
                "success": True,
                "error": None,
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ERROR: {case_id} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "case_id": case_id,
                "verdict": "error",
                "fraud_probability": 0.0,
                "elapsed_s": round(elapsed, 2),
                "success": False,
                "error": str(e),
            })

    total_elapsed = time.time() - total_start
    print(f"\n{'='*70}")
    print(f"BENCHMARK RUN COMPLETE: {len(results)} cases in {total_elapsed:.1f}s")
    fraud_count = sum(1 for r in results if r["verdict"] == "fraud")
    error_count = sum(1 for r in results if not r["success"])
    print(f"  Fraud verdicts: {fraud_count}/{len(results)}")
    print(f"  Errors: {error_count}")
    print(f"  Avg time per case: {total_elapsed/len(results):.1f}s")

    # Save run summary
    run_summary = {
        "run_at": __import__("datetime").datetime.now().isoformat(),
        "total_cases": len(results),
        "fraud_count": fraud_count,
        "error_count": error_count,
        "total_elapsed_s": round(total_elapsed, 1),
        "results": results,
    }
    summary_path = CASES_DIR / "_last_run_summary.json"
    summary_path.write_text(json.dumps(run_summary, indent=2))
    print(f"\nRun summary written to: {summary_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
