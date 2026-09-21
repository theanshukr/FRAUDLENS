"""
FraudLens     Data Loading Script
=================================
Loads CSV data files into TigerGraph using the installed loading jobs.

Usage:
    python scripts/load_data.py                    # Load all files
    python scripts/load_data.py --sample 10000    # Load first N rows (dev)
    python scripts/load_data.py --dry-run          # Validate CSVs only
    python scripts/load_data.py --file transactions # Load one file

Data files expected in ./data/:
    transactions.csv          (~590,742 rows, 708 MB)
    identity.csv              (~144,432 rows)
    closed_cases_history.csv  (~5,565 rows)
    case_pack.csv             (20 benchmark cases)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Expected row counts (approximate)
EXPECTED_ROWS = {
    "transactions.csv":           590_742,
    "identity.csv":               144_432,
    "closed_cases_history.csv":   5_565,
    "case_pack.csv":              20,
}

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))


def validate_csvs() -> bool:
    """Validate CSV files exist and have expected row counts."""
    all_ok = True
    for filename, expected in EXPECTED_ROWS.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            logger.error(f"MISSING: {filepath}")
            all_ok = False
            continue

        try:
            # Count rows efficiently
            df = pd.read_csv(filepath, nrows=5)
            # Get total row count
            with open(filepath, "r") as f:
                row_count = sum(1 for _ in f) - 1  # -1 for header

            tolerance = 0.05  # 5% tolerance
            if abs(row_count - expected) / expected > tolerance:
                logger.warning(
                    f"ROW COUNT MISMATCH: {filename} has {row_count:,} rows, "
                    f"expected ~{expected:,}"
                )
            else:
                logger.success(f"OK: {filename}     {row_count:,} rows | Columns: {list(df.columns[:5])}...")

        except Exception as e:
            logger.error(f"ERROR reading {filename}: {e}")
            all_ok = False

    return all_ok


def load_data(
    sample: int = None,
    file_filter: str = None,
    dry_run: bool = False,
) -> None:
    """Load CSV data into TigerGraph."""

    logger.info(f"Data directory: {DATA_DIR.resolve()}")

    # Step 1: Validate
    logger.info("Validating CSV files...")
    if not validate_csvs():
        logger.error("CSV validation failed. Please check your data directory.")
        sys.exit(1)

    if dry_run:
        logger.success("[DRY RUN] CSV validation complete. No data loaded.")
        return

    # Step 2: Connect to TigerGraph
    try:
        import pyTigerGraph as tg
        conn = tg.TigerGraphConnection(
            host=os.getenv("TG_HOST", "http://localhost"),
            graphname=os.getenv("TG_GRAPH_NAME", "FraudLens"),
            username=os.getenv("TG_USERNAME", "tigergraph"),
            password=os.getenv("TG_PASSWORD", "tigergraph"),
        )
        conn.getToken(os.getenv("TG_SECRET", ""))
        logger.info("Connected to TigerGraph")
    except ImportError:
        logger.error("pyTigerGraph not installed. Run: pip install pyTigerGraph")
        sys.exit(1)

    # Step 3: Run loading jobs
    files_to_load = list(EXPECTED_ROWS.keys())
    if file_filter:
        files_to_load = [f for f in files_to_load if file_filter in f]

    for filename in files_to_load:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue

        job_name = f"load_{filename.replace('.csv', '').replace('-', '_')}"
        logger.info(f"Running loading job: {job_name} for {filename}")

        try:
            if sample:
                logger.info(f"  Loading sample of {sample:,} rows from {filename}")
                # For sample loading, use pyTigerGraph upsert instead
                df = pd.read_csv(filepath, nrows=sample)
                logger.info(f"  Loaded {len(df):,} rows from {filename}")
                # TODO: Upsert via pyTigerGraph vertex/edge API
            else:
                result = conn.runLoadingJobWithFile(
                    filePath=str(filepath.resolve()),
                    jobName=job_name,
                    fileTag="f_" + filename.replace(".csv", "").replace("-", "_"),
                )
                logger.success(f"  Loading job complete: {result}")
        except Exception as e:
            logger.error(f"  Loading job failed for {filename}: {e}")

    logger.success("Data loading complete!")

    # Step 4: Verify counts
    logger.info("Verifying vertex/edge counts...")
    try:
        stats = conn.getVertexStats("*")
        logger.info(f"Vertex counts: {stats}")
    except Exception as e:
        logger.warning(f"Could not fetch vertex stats: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load FraudLens CSV data into TigerGraph")
    parser.add_argument("--sample", type=int, help="Load only first N rows (for dev)")
    parser.add_argument("--file", type=str, help="Load specific file (e.g., 'transactions')")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSVs without loading")
    args = parser.parse_args()

    load_data(sample=args.sample, file_filter=args.file, dry_run=args.dry_run)
