"""
FraudLens     Benchmark Runner
==============================
Runs all 20 benchmark cases from case_pack.csv through the agent pipeline
and writes answer JSON files to cases/ directory.

Usage:
    python scripts/run_benchmarks.py
    python scripts/run_benchmarks.py --case HHG-017    # Run single case
    python scripts/run_benchmarks.py --limit 5          # Run first 5 cases

Output:
    cases/<case_id>.json     One file per benchmark case
    cases/_benchmark_summary.json     Aggregate metrics

Metrics tracked per case:
    - tool_calls count
    - tokens used (if available)
    - latency_s
    - fraud_probability
    - final_verdict
    - schema validation pass/fail
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

CASES_DIR  = Path("./cases")
DATA_DIR   = Path("./data")
SAMPLE_DIR = Path("./dataset_sample")

# Search for case_pack.csv in data/ first, then dataset_sample/
_CASE_PACK_CANDIDATES = [DATA_DIR / "case_pack.csv", SAMPLE_DIR / "case_pack.csv"]
CASE_PACK = next((p for p in _CASE_PACK_CANDIDATES if p.exists()), _CASE_PACK_CANDIDATES[0])


async def run_case(case_row: dict) -> dict:
    """Run a single benchmark case through the agent pipeline."""
    from agent.orchestrator import Orchestrator

    orch = Orchestrator(cases_dir=str(CASES_DIR))

    # Handle multiple possible column name conventions in case_pack.csv
    case_id    = (
        case_row.get("case_id") or
        case_row.get("HHG_case_id") or
        case_row.get("Case_ID") or
        ""
    )
    txn_id     = (
        str(case_row.get("flagged_txn_id") or "").strip() or
        str(case_row.get("txn_id") or "").strip() or
        str(case_row.get("TransactionID") or "").strip() or
        str(case_row.get("transaction_id") or "").strip() or
        ""
    )
    card_id    = (
        case_row.get("card_id") or
        case_row.get("Card_ID") or
        None
    )
    trigger    = (
        case_row.get("trigger_type") or
        case_row.get("Trigger") or
        "risk_score"
    )
    risk_score_raw = (
        case_row.get("risk_score") or
        case_row.get("initial_risk_score") or
        0.5
    )
    risk_score = float(risk_score_raw)

    logger.info(f"Running benchmark case: {case_id} | txn={txn_id}")
    start = time.perf_counter()

    events = []
    try:
        async for event in orch.investigate(
            txn_id=txn_id,
            trigger_type=trigger,
            card_id=card_id,
            trigger_risk_score=risk_score,
            case_id=case_id,
        ):
            events.append(event)
    except Exception as e:
        logger.error(f"Case {case_id} failed: {e}")
        return {
            "case_id": case_id,
            "success": False,
            "error": str(e),
            "latency_s": time.perf_counter() - start,
        }

    latency = time.perf_counter() - start

    # Load the written case file
    case_file = CASES_DIR / f"{case_id}.json"
    case_data = {}
    if case_file.exists():
        with open(case_file) as f:
            case_data = json.load(f)

    result = {
        "case_id": case_id,
        "success": True,
        "latency_s": round(latency, 2),
        "events": len(events),
        "final_verdict": case_data.get("final_verdict", "unknown"),
        "fraud_probability": case_data.get("final_fraud_probability", 0.0),
        "pattern": case_data.get("pattern", "unknown"),
        "sar_filed": case_data.get("sar", {}).get("file", False),
        "tool_calls": len(case_data.get("tool_calls", [])),
    }
    logger.success(
        f"Case {case_id} complete | verdict={result['final_verdict']} | "
        f"prob={result['fraud_probability']:.0%} | latency={result['latency_s']}s"
    )
    return result


def validate_case_json(case_id: str) -> dict:
    """Validate a case JSON file against the required answer format schema."""
    case_file = CASES_DIR / f"{case_id}.json"
    issues = []

    if not case_file.exists():
        return {"case_id": case_id, "valid": False, "issues": ["File not found"]}

    with open(case_file) as f:
        data = json.load(f)

    required_fields = [
        "case_id", "txn_id", "trigger_type", "status",
        "final_fraud_probability", "final_risk_level",
        "pattern", "final_verdict", "final_actions",
        "evidence", "timeline", "sar",
    ]
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing field: {field}")

    # Check SAR consistency
    sar_filed = data.get("sar", {}).get("file", False)
    final_actions = [a.get("action") for a in data.get("final_actions", [])]
    if sar_filed and "FILE_REPORT" not in final_actions:
        issues.append("SAR filed but FILE_REPORT not in final_actions")
    if not sar_filed and "FILE_REPORT" in final_actions:
        issues.append("FILE_REPORT in actions but SAR not marked as filed")

    return {
        "case_id": case_id,
        "valid": len(issues) == 0,
        "issues": issues,
    }


async def run_benchmarks(case_filter: str = None, limit: int = None) -> None:
    """Run all benchmark cases and produce summary report."""

    CASES_DIR.mkdir(parents=True, exist_ok=True)

    if not CASE_PACK.exists():
        logger.error(f"case_pack.csv not found. Searched: {_CASE_PACK_CANDIDATES}")
        logger.info("Copy case_pack.csv to ./data/ or ./dataset_sample/ first")
        return

    df = pd.read_csv(CASE_PACK)
    logger.info(f"Loaded {len(df)} benchmark cases from {CASE_PACK}")

    if case_filter:
        df = df[df.apply(
            lambda r: case_filter in str(r.get("case_id", "")) or case_filter in str(r.get("TransactionID", "")),
            axis=1
        )]
        logger.info(f"Filtered to {len(df)} cases matching '{case_filter}'")

    if limit:
        df = df.head(limit)
        logger.info(f"Limited to first {limit} cases")

    results = []
    for _, row in df.iterrows():
        result = await run_case(row.to_dict())
        results.append(result)

    # Validate all outputs
    logger.info("Validating output JSON files...")
    validations = []
    for result in results:
        v = validate_case_json(result["case_id"])
        validations.append(v)
        if not v["valid"]:
            logger.warning(f"  {result['case_id']}: INVALID     {v['issues']}")
        else:
            logger.success(f"  {result['case_id']}: VALID")

    # Summary
    total = len(results)
    successful = sum(1 for r in results if r.get("success"))
    valid_json = sum(1 for v in validations if v["valid"])
    fraud_verdicts = sum(1 for r in results if r.get("final_verdict") == "fraud")
    avg_latency = sum(r.get("latency_s", 0) for r in results) / total if total > 0 else 0

    summary = {
        "total_cases": total,
        "successful": successful,
        "failed": total - successful,
        "valid_json_outputs": valid_json,
        "fraud_verdicts": fraud_verdicts,
        "cleared_verdicts": total - fraud_verdicts,
        "avg_latency_s": round(avg_latency, 2),
        "results": results,
        "validations": validations,
    }

    summary_path = CASES_DIR / "_benchmark_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)
    logger.info(f"BENCHMARK RESULTS")
    logger.info(f"  Total:      {total}")
    logger.info(f"  Successful: {successful}/{total}")
    logger.info(f"  Valid JSON: {valid_json}/{total}")
    logger.info(f"  Fraud:      {fraud_verdicts} | Cleared: {total - fraud_verdicts}")
    logger.info(f"  Avg Latency:{avg_latency:.2f}s")
    logger.info(f"  Summary:    {summary_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FraudLens benchmark cases")
    parser.add_argument("--case", type=str, help="Run specific case ID or transaction ID")
    parser.add_argument("--limit", type=int, help="Run only first N cases")
    args = parser.parse_args()

    asyncio.run(run_benchmarks(case_filter=args.case, limit=args.limit))
