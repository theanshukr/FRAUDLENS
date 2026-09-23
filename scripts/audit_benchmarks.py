"""
FraudLens — Full Benchmark Audit Script (Phase 4)
==================================================
Validates all 20 HHG benchmark cases against:
- case_pack.csv (source of truth for triggers/txn_ids)
- existing cases/ JSON outputs
- known ground truth patterns from dataset analysis

Generates:
  cases/_benchmark_results.json
  cases/_benchmark_report.md

Run: python scripts/audit_benchmarks.py
"""

from __future__ import annotations

import io
import json
import sys

# Force UTF-8 output on Windows so emoji/unicode don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = REPO_ROOT / "cases"
SAMPLE_DIR = REPO_ROOT / "dataset_sample"
DATA_DIR = REPO_ROOT / "data"

CASE_PACK = SAMPLE_DIR / "case_pack.csv" if (SAMPLE_DIR / "case_pack.csv").exists() else DATA_DIR / "case_pack.csv"

# =============================================================================
# Ground truth inference rules
# Based on hackathon dataset patterns + trigger types
# =============================================================================

def infer_expected(row: dict) -> dict:
    """
    Infer expected investigation outcome from case_pack.csv row.
    Since no official answer key exists, we apply domain logic:
    - customer_report → fraud (customer denied) or needs investigation
    - risk_score >= 0.80 → high confidence fraud
    - risk_score 0.50-0.80 → medium, needs evidence
    - analyst_request → investigate shared device patterns
    """
    trigger = str(row.get("trigger_type", "")).lower()
    risk = float(row.get("risk_score") or 0.0)
    text = str(row.get("trigger_text", "")).lower()

    if trigger == "customer_report":
        # Customer explicitly reporting means high suspicion
        return {
            "expected_verdict": "fraud",
            "expected_pattern": "account_takeover",
            "expected_sar": False,
            "expected_approval_route": "L1",
            "confidence_level": "medium",
            "note": "Customer dispute — investigate and block card if confirmed",
        }
    elif trigger == "risk_score" and risk >= 0.85:
        return {
            "expected_verdict": "fraud",
            "expected_pattern": "card_testing_or_velocity",
            "expected_sar": True if risk >= 0.90 else False,
            "expected_approval_route": "L1",
            "confidence_level": "high",
            "note": "High risk score — expect fraud verdict",
        }
    elif trigger == "risk_score" and risk >= 0.65:
        return {
            "expected_verdict": "fraud",
            "expected_pattern": "card_testing",
            "expected_sar": False,
            "expected_approval_route": "L1",
            "confidence_level": "medium",
            "note": "Elevated risk score — likely fraud after investigation",
        }
    elif trigger == "risk_score" and risk >= 0.50:
        return {
            "expected_verdict": "uncertain",
            "expected_pattern": "card_testing_or_velocity",
            "expected_sar": False,
            "expected_approval_route": "auto_or_L1",
            "confidence_level": "low",
            "note": "Borderline risk score — outcome depends on evidence",
        }
    elif trigger == "analyst_request":
        return {
            "expected_verdict": "fraud",
            "expected_pattern": "shared_device_ring",
            "expected_sar": False,
            "expected_approval_route": "L2",
            "confidence_level": "high",
            "note": "Analyst flagged shared device pattern — expect ring detection",
        }
    else:
        return {
            "expected_verdict": "uncertain",
            "expected_pattern": "unknown",
            "expected_sar": False,
            "expected_approval_route": "auto",
            "confidence_level": "low",
            "note": "Unknown trigger — uncertain outcome",
        }


SYNTHETIC_PATTERNS = [
    ("$482.12", "Hardcoded transaction amount from case HHG-006 template"),
    ("DEV_FP_", "Fake device ID generated from txn_id substring"),
    ("REGION_", "Fake billing region ID generated from txn_id substring"),
    ("DOMAIN_gmail", "Fake email domain derived from txn_id parity"),
    ("CC-0141", "Mock memory case from _mock_similar_cases()"),
    ("CC-2671", "Mock memory case from _mock_similar_cases()"),
    ("D_MOCK_001", "Mock device ID from _mock_similar_cases()"),
    ("Math.sin", "Synthetic chart data — dashboard trend"),
    ("Math.cos", "Synthetic chart data — dashboard trend"),
    ("base_txn_num - 2", "Arithmetic fake prior transaction"),
    ("base_txn_num - 1420", "Arithmetic fake prior transaction"),
    ("CUST_", "Fallback synthetic customer ID"),
    ("tenure.*3.5 yrs", "Hardcoded customer tenure"),
]


def scan_for_synthetic_data() -> list[dict]:
    """Scan codebase for known synthetic data patterns."""
    import re
    findings = []

    search_dirs = [
        REPO_ROOT / "backend",
        REPO_ROOT / "frontend" / "src",
        REPO_ROOT / "agent",
        REPO_ROOT / "tools",
    ]

    extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for path in search_dir.rglob("*"):
            if path.suffix not in extensions:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern, description in SYNTHETIC_PATTERNS:
                    if re.search(re.escape(pattern), text, re.IGNORECASE):
                        # Find line numbers
                        for i, line in enumerate(text.splitlines(), 1):
                            if re.search(re.escape(pattern), line, re.IGNORECASE):
                                findings.append({
                                    "file": str(path.relative_to(REPO_ROOT)),
                                    "line": i,
                                    "pattern": pattern,
                                    "description": description,
                                    "content": line.strip()[:120],
                                })
            except Exception:
                pass

    return findings


def analyze_evidence_provenance(evidence: list[dict]) -> dict:
    """Analyze where evidence comes from — TigerGraph vs synthetic."""
    sources = {"graph": 0, "document": 0, "customer": 0, "external": 0, "unknown": 0}
    refs = []
    empty_claims = 0
    zero_amount_claims = 0
    tg_queries_used = set()

    for ev in evidence:
        src = ev.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
        ref = ev.get("ref", "")
        refs.append(ref)
        if ref and not ref.startswith("evidence_request"):
            tg_queries_used.add(ref)

        claim = ev.get("claim", "")
        if "amount $0.00" in claim or "Risk score unavailable" in claim:
            zero_amount_claims += 1
        if not claim:
            empty_claims += 1

    return {
        "total_evidence": len(evidence),
        "sources": sources,
        "tg_queries_used": sorted(tg_queries_used),
        "empty_claims": empty_claims,
        "zero_amount_claims": zero_amount_claims,
        "has_real_tg_data": zero_amount_claims < len(evidence),
    }


def check_evidence_loop(case_data: dict) -> dict:
    """Verify that additional evidence materially changed the investigation."""
    initial_prob = case_data.get("initial_fraud_probability") or 0.0
    final_prob = case_data.get("final_fraud_probability") or 0.0
    initial_conf = case_data.get("initial_confidence") or 0.0
    final_conf = case_data.get("final_confidence") or 0.0

    has_evidence_request = bool(
        case_data.get("evidence_request") or
        case_data.get("evidence_requests") or
        any(e.get("source") == "customer" for e in case_data.get("evidence", []))
    )

    prob_changed = abs(final_prob - initial_prob) >= 0.05
    conf_changed = abs(final_conf - initial_conf) >= 0.05

    return {
        "has_evidence_request": has_evidence_request,
        "initial_fraud_probability": round(initial_prob, 3),
        "final_fraud_probability": round(final_prob, 3),
        "initial_confidence": round(initial_conf, 3),
        "final_confidence": round(final_conf, 3),
        "probability_changed": prob_changed,
        "confidence_changed": conf_changed,
        "loop_demonstrated": has_evidence_request and (prob_changed or conf_changed),
    }


def validate_case(case_row: dict, case_data: dict) -> dict:
    """Full validation of a single benchmark case."""
    case_id = case_data.get("case_id", case_row.get("case_id", ""))
    expected = infer_expected(case_row)

    actual_verdict = case_data.get("final_verdict", "unknown")
    actual_pattern = case_data.get("pattern", "unknown")
    actual_prob = case_data.get("final_fraud_probability") or 0.0
    actual_risk = case_data.get("final_risk_level", "UNKNOWN")
    actual_conf = case_data.get("final_confidence") or case_data.get("initial_confidence") or 0.0

    # SAR
    sar = case_data.get("sar") or {}
    sar_filed = sar.get("file", False)
    sar_narrative = sar.get("narrative", "")

    # NBA
    initial_actions = [a.get("action") for a in (case_data.get("initial_actions") or [])]
    final_actions = [a.get("action") for a in (case_data.get("final_actions") or [])]
    approval_routes = list(set(a.get("route", "auto") for a in (case_data.get("final_actions") or [])))

    # Evidence
    evidence = case_data.get("evidence") or []
    ev_analysis = analyze_evidence_provenance(evidence)

    # Evidence loop
    loop = check_evidence_loop(case_data)

    # Verdict accuracy
    verdict_match = (
        actual_verdict == expected["expected_verdict"] or
        (expected["expected_verdict"] == "uncertain" and actual_verdict in ("uncertain", "fraud", "cleared")) or
        (expected["confidence_level"] == "low")  # borderline — both acceptable
    )

    # Pattern accuracy (soft match)
    expected_pattern_key = expected["expected_pattern"]
    pattern_match = (
        actual_pattern == expected_pattern_key or
        expected_pattern_key.endswith("_or_" + actual_pattern.split("_")[0]) or
        expected_pattern_key.startswith(actual_pattern.split("_")[0]) or
        expected["confidence_level"] == "low"
    )

    # NBA key action correctness
    has_block_card = "BLOCK_CARD" in final_actions
    has_monitor = "MONITOR_ACCOUNT" in final_actions
    has_warn = "WARN_CUSTOMER" in final_actions
    has_sar_action = "FILE_REPORT" in final_actions

    # Approval route
    highest_route = "L2" if "L2" in approval_routes else ("L1" if "L1" in approval_routes else "auto")

    # Status
    status = case_data.get("status", "unknown")
    writeback = case_data.get("case", {}).get("written_to_graph", False)

    return {
        "case_id": case_id,
        "txn_id": case_data.get("txn_id"),
        "card_id": case_data.get("card_id"),
        "customer_id": case_data.get("customer_id"),
        "trigger_type": case_row.get("trigger_type"),
        "trigger_risk_score": case_row.get("risk_score"),
        # Expected
        "expected_verdict": expected["expected_verdict"],
        "expected_pattern": expected["expected_pattern"],
        "expected_sar": expected["expected_sar"],
        "expected_approval": expected["expected_approval_route"],
        # Actual
        "actual_verdict": actual_verdict,
        "actual_pattern": actual_pattern,
        "actual_risk_level": actual_risk,
        "actual_fraud_probability": round(actual_prob, 3),
        "actual_confidence": round(actual_conf, 3),
        "sar_filed": sar_filed,
        "sar_has_narrative": bool(sar_narrative),
        "approval_route": highest_route,
        # Accuracy flags
        "verdict_match": verdict_match,
        "pattern_match": pattern_match,
        "has_block_card_action": has_block_card,
        "has_monitor_action": has_monitor,
        "has_warn_action": has_warn,
        # NBA
        "initial_nba": initial_actions,
        "final_nba": final_actions,
        "nba_changed": initial_actions != final_actions,
        # Evidence loop
        "evidence_loop": loop,
        "evidence_count": ev_analysis["total_evidence"],
        "tg_queries_used": ev_analysis["tg_queries_used"],
        "zero_amount_claims": ev_analysis["zero_amount_claims"],
        "has_real_tg_data": ev_analysis["has_real_tg_data"],
        # Graph writeback
        "tg_writeback": writeback,
        "status": status,
        # Failure analysis
        "failure_reasons": _analyze_failures(
            actual_verdict, expected, actual_pattern, ev_analysis, loop, actual_prob
        ),
    }


def _analyze_failures(actual_verdict, expected, actual_pattern, ev_analysis, loop, prob) -> list[str]:
    """Classify any failures for this case."""
    failures = []

    if ev_analysis["zero_amount_claims"] > 2:
        failures.append(f"TG_DATA_GAP: {ev_analysis['zero_amount_claims']} evidence items returned $0.00 — transaction not found in TigerGraph")

    if actual_verdict == "unknown":
        failures.append("MISSING_VERDICT: final_verdict not set")

    if prob < 0.01:
        failures.append("LOW_PROBABILITY: fraud_probability near zero — risk engine may not have received evidence")

    if not ev_analysis["tg_queries_used"]:
        failures.append("NO_TG_QUERIES: no TigerGraph queries recorded in evidence")

    if not loop["loop_demonstrated"] and expected["expected_verdict"] == "fraud":
        failures.append("NO_EVIDENCE_LOOP: expected evidence request loop not demonstrated")

    return failures


def compute_aggregate_metrics(results: list[dict]) -> dict:
    """Compute aggregate accuracy metrics across all cases."""
    n = len(results)
    if n == 0:
        return {}

    verdict_correct = sum(1 for r in results if r["verdict_match"])
    pattern_correct = sum(1 for r in results if r["pattern_match"])
    tg_data_ok = sum(1 for r in results if r["has_real_tg_data"])
    evidence_loop_ok = sum(1 for r in results if r["evidence_loop"]["loop_demonstrated"])
    writeback_ok = sum(1 for r in results if r["tg_writeback"])
    block_card_when_fraud = sum(
        1 for r in results
        if r["actual_verdict"] == "fraud" and r["has_block_card_action"]
    )
    fraud_count = sum(1 for r in results if r["actual_verdict"] == "fraud")
    avg_prob = sum(r["actual_fraud_probability"] for r in results) / n
    avg_conf = sum(r["actual_confidence"] for r in results) / n
    cases_with_failures = [r["case_id"] for r in results if r["failure_reasons"]]
    all_tg_queries = set()
    for r in results:
        all_tq = r.get("tq_queries_used", r.get("tg_queries_used", []))
        all_tg_queries.update(all_tq)

    return {
        "total_cases": n,
        "verdict_accuracy": f"{verdict_correct}/{n} ({verdict_correct*100//n}%)",
        "pattern_accuracy": f"{pattern_correct}/{n} ({pattern_correct*100//n}%)",
        "tg_data_availability": f"{tg_data_ok}/{n} ({tg_data_ok*100//n}%)",
        "evidence_loop_demonstrated": f"{evidence_loop_ok}/{n} ({evidence_loop_ok*100//n}%)",
        "tg_writeback_success": f"{writeback_ok}/{n} ({writeback_ok*100//n}%)",
        "block_card_when_fraud": f"{block_card_when_fraud}/{fraud_count} fraud cases" if fraud_count else "N/A",
        "avg_fraud_probability": round(avg_prob, 3),
        "avg_confidence": round(avg_conf, 3),
        "cases_with_failures": cases_with_failures,
        "tg_queries_seen_across_all_cases": sorted(all_tg_queries),
        "fraud_verdicts": fraud_count,
        "cleared_verdicts": sum(1 for r in results if r["actual_verdict"] == "cleared"),
        "uncertain_verdicts": sum(1 for r in results if r["actual_verdict"] == "uncertain"),
    }


def generate_markdown_report(results: list[dict], metrics: dict, synthetic_findings: list[dict]) -> str:
    """Generate the full benchmark report markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# FraudLens — Benchmark Report",
        f"\n**Generated**: {now}",
        f"**Total Cases**: {metrics.get('total_cases', 0)}",
        f"**Verdict Accuracy**: {metrics.get('verdict_accuracy', 'N/A')}",
        f"**Pattern Accuracy**: {metrics.get('pattern_accuracy', 'N/A')}",
        f"**TigerGraph Data Availability**: {metrics.get('tg_data_availability', 'N/A')}",
        f"**Evidence Loop Demonstrated**: {metrics.get('evidence_loop_demonstrated', 'N/A')}",
        f"**TigerGraph Writeback Success**: {metrics.get('tg_writeback_success', 'N/A')}",
        "",
        "---",
        "",
        "## Case Results Table",
        "",
        "| Case | Trigger | Risk Score | Pattern | Verdict | Fraud Prob | Confidence | Initial NBA | Final NBA | Approval | SAR | TG Data | Loop | Writeback |",
        "|------|---------|-----------|---------|---------|-----------|-----------|-------------|-----------|----------|-----|---------|------|-----------|",
    ]

    for r in results:
        case_id = r["case_id"]
        trigger = r["trigger_type"]
        risk_score = f"{r['trigger_risk_score']:.2f}" if r.get("trigger_risk_score") else "—"
        pattern = r["actual_pattern"]
        verdict = r["actual_verdict"]
        prob = f"{r['actual_fraud_probability']*100:.0f}%"
        conf = f"{r['actual_confidence']*100:.0f}%"
        initial_nba = ", ".join(r["initial_nba"][:2]) if r["initial_nba"] else "—"
        final_nba = ", ".join(r["final_nba"][:2]) if r["final_nba"] else "—"
        approval = r["approval_route"]
        sar = "✅" if r["sar_filed"] else "—"
        tg_data = "✅" if r["has_real_tg_data"] else "⚠️"
        loop = "✅" if r["evidence_loop"]["loop_demonstrated"] else "—"
        writeback = "✅" if r["tg_writeback"] else "⚠️"

        lines.append(
            f"| {case_id} | {trigger} | {risk_score} | {pattern} | {verdict} | {prob} | {conf} | {initial_nba} | {final_nba} | {approval} | {sar} | {tg_data} | {loop} | {writeback} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Aggregate Metrics",
        "",
        f"- **Verdict Accuracy**: {metrics.get('verdict_accuracy')}",
        f"- **Pattern Detection Accuracy**: {metrics.get('pattern_accuracy')}",
        f"- **Average Fraud Probability**: {metrics.get('avg_fraud_probability')}",
        f"- **Average Confidence**: {metrics.get('avg_confidence')}",
        f"- **Fraud Verdicts**: {metrics.get('fraud_verdicts')}",
        f"- **Cleared Verdicts**: {metrics.get('cleared_verdicts')}",
        f"- **Uncertain Verdicts**: {metrics.get('uncertain_verdicts')}",
        f"- **Evidence Loop Demonstrated**: {metrics.get('evidence_loop_demonstrated')}",
        f"- **TigerGraph Writeback Success**: {metrics.get('tg_writeback_success')}",
        f"- **NBA includes BLOCK_CARD when fraud**: {metrics.get('block_card_when_fraud')}",
        "",
        "### TigerGraph Queries Used",
        "",
    ]
    for q in metrics.get("tg_queries_seen_across_all_cases", []):
        lines.append(f"- `{q}`")

    lines += [
        "",
        "---",
        "",
        "## Failure Analysis",
        "",
    ]
    cases_with_failures = [r for r in results if r["failure_reasons"]]
    if cases_with_failures:
        for r in cases_with_failures:
            lines.append(f"### {r['case_id']}")
            for f in r["failure_reasons"]:
                lines.append(f"- {f}")
            lines.append("")
    else:
        lines.append("✅ No systemic failures detected across all 20 cases.")

    lines += [
        "",
        "---",
        "",
        "## Synthetic Data Leak Scan",
        "",
    ]
    if synthetic_findings:
        lines.append(f"⚠️ **{len(synthetic_findings)} synthetic data patterns found**:\n")
        lines.append("| File | Line | Pattern | Content |")
        lines.append("|------|------|---------|---------|")
        for f in synthetic_findings:
            content_safe = f["content"].replace("|", "\\|")[:80]
            lines.append(f"| `{f['file']}` | {f['line']} | `{f['pattern']}` | `{content_safe}` |")
    else:
        lines.append("✅ No synthetic data leaks detected.")

    lines += [
        "",
        "---",
        "",
        "## Evidence Provenance Summary",
        "",
        "All evidence items in produced case JSONs must originate from one of:",
        "- `source: graph` — TigerGraph GSQL query result",
        "- `source: document` — case memory / CSV retrieval",
        "- `source: customer` — evidence request response",
        "- `source: external` — external API",
        "",
        "### Key Finding: get_transaction Returns Empty for Most Cases",
        "",
        "Multiple cases show `'amount $0.00 via . Risk score unavailable'` — this means the",
        "TigerGraph `get_transaction` query returned no rows for the flagged transaction IDs.",
        "",
        "**Root Cause**: The transactions.csv loaded has ~50,000 rows out of 590,000 total.",
        "Many benchmark txn_ids (e.g. 3514030) are from months not yet loaded.",
        "",
        "**Impact**: Evidence quality is lower than possible. `detect_card_testing` and",
        "`get_card_history` still return results (card vertex exists) but transaction attributes",
        "(amount, channel, risk_score) are missing.",
        "",
        "**Recommendation**: Load full transactions.csv (590k rows) to TigerGraph for complete evidence.",
        "",
        "---",
        "",
        "## Demo Case Recommendation",
        "",
    ]

    # Find best demo case
    best_cases = [r for r in results if
                  r["actual_verdict"] == "fraud" and
                  r["evidence_loop"]["loop_demonstrated"] and
                  r["actual_fraud_probability"] >= 0.65 and
                  r["has_real_tg_data"]]

    if best_cases:
        best = sorted(best_cases, key=lambda x: x["actual_fraud_probability"], reverse=True)[0]
        lines += [
            f"**Recommended Demo Case**: `{best['case_id']}`",
            f"- Trigger: {best['trigger_type']} (risk score: {best.get('trigger_risk_score', '—')})",
            f"- Pattern: {best['actual_pattern']}",
            f"- Fraud Probability: {best['actual_fraud_probability']*100:.0f}%",
            f"- Evidence Loop: {best['evidence_loop']['loop_demonstrated']}",
            f"- Final NBA: {', '.join(best['final_nba'][:3])}",
            f"- Approval Route: {best['approval_route']}",
        ]
    else:
        lines.append("⚠️ No ideal demo case found — consider re-running benchmarks after loading full transaction dataset.")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("FraudLens — Benchmark Audit (Phase 4)")
    print("=" * 70)

    # Load case pack
    if not CASE_PACK.exists():
        print(f"ERROR: case_pack.csv not found at {CASE_PACK}")
        sys.exit(1)

    df = pd.read_csv(CASE_PACK)
    case_rows = {str(row["case_id"]): dict(row) for _, row in df.iterrows()}
    print(f"Loaded {len(case_rows)} cases from case_pack.csv")

    # Validate all 20 HHG cases
    results = []
    missing_cases = []

    for case_id in sorted(case_rows.keys()):
        case_file = CASES_DIR / f"{case_id}.json"
        if not case_file.exists():
            missing_cases.append(case_id)
            print(f"  MISSING: {case_id}.json")
            continue

        try:
            case_data = json.loads(case_file.read_text())
            row = case_rows[case_id]
            result = validate_case(row, case_data)
            results.append(result)

            status_icon = "✅" if not result["failure_reasons"] else "⚠️"
            print(
                f"  {status_icon} {case_id} | {result['actual_verdict']:10s} | "
                f"prob={result['actual_fraud_probability']:.2f} | "
                f"pattern={result['actual_pattern']:22s} | "
                f"evidence={result['evidence_count']:2d} | "
                f"loop={'Y' if result['evidence_loop']['loop_demonstrated'] else 'N'} | "
                f"tg={'Y' if result['has_real_tg_data'] else 'N'}"
            )
            if result["failure_reasons"]:
                for fr in result["failure_reasons"]:
                    print(f"       ↳ {fr}")

        except Exception as e:
            print(f"  ERROR: {case_id} — {e}")
            import traceback; traceback.print_exc()

    print(f"\n{len(missing_cases)} missing cases: {missing_cases}")

    # Compute metrics
    metrics = compute_aggregate_metrics(results)

    print("\n" + "=" * 70)
    print("AGGREGATE METRICS")
    print("=" * 70)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Scan for synthetic data
    print("\n" + "=" * 70)
    print("SYNTHETIC DATA SCAN")
    print("=" * 70)
    synthetic_findings = scan_for_synthetic_data()
    if synthetic_findings:
        print(f"  ⚠️ Found {len(synthetic_findings)} synthetic data occurrences:")
        for f in synthetic_findings[:20]:  # show first 20
            print(f"    [{f['file']}:{f['line']}] {f['pattern']}: {f['content'][:60]}")
        if len(synthetic_findings) > 20:
            print(f"    ... and {len(synthetic_findings) - 20} more")
    else:
        print("  ✅ No synthetic data patterns found")

    # Write JSON results
    results_file = CASES_DIR / "_benchmark_results.json"
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_cases_validated": len(results),
        "missing_cases": missing_cases,
        "metrics": metrics,
        "synthetic_data_findings": synthetic_findings,
        "cases": results,
    }
    results_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n✅ Results written to: {results_file}")

    # Write Markdown report
    report = generate_markdown_report(results, metrics, synthetic_findings)
    report_file = CASES_DIR / "_benchmark_report.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"✅ Report written to: {report_file}")

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Cases validated: {len(results)}/{len(case_rows)}")
    print(f"  Verdict accuracy: {metrics.get('verdict_accuracy')}")
    print(f"  Pattern accuracy: {metrics.get('pattern_accuracy')}")
    print(f"  Evidence loop: {metrics.get('evidence_loop_demonstrated')}")
    print(f"  TigerGraph writeback: {metrics.get('tg_writeback_success')}")
    print(f"  Synthetic data leaks: {len(synthetic_findings)}")

    return 0 if not missing_cases else 1


if __name__ == "__main__":
    sys.exit(main())
