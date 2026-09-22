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
            fallback = Path("dataset_sample") / filename
            if fallback.exists():
                logger.info(f"Using sample file for {filename}: {fallback}")
                continue
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
        host = os.getenv("TG_HOST", "http://localhost")
        secret = os.getenv("TG_SECRET", "")
        token = os.getenv("TG_TOKEN", "") or os.getenv("TG_API_KEY", "")
        is_cloud = "tgcloud.io" in host

        conn = tg.TigerGraphConnection(
            host=host,
            graphname=os.getenv("TG_GRAPH_NAME", "FraudLens"),
            username=os.getenv("TG_USERNAME", "tigergraph"),
            password=os.getenv("TG_PASSWORD", "tigergraph"),
            gsqlSecret=secret if (secret and secret != "your_secret_here") else "",
            apiToken=token if token else "",
            tgCloud=is_cloud,
        )
        if not token and secret and secret != "your_secret_here":
            conn.getToken(secret)
        logger.info(f"Connected to TigerGraph: {conn.host}")
    except ImportError:
        logger.error("pyTigerGraph not installed. Run: pip install pyTigerGraph")
        sys.exit(1)

    # Check if data or dataset_sample exists
    data_source = DATA_DIR if any((DATA_DIR / f).exists() for f in EXPECTED_ROWS.keys()) else Path("dataset_sample")
    logger.info(f"Loading data from: {data_source.resolve()}")

    # 1. Transactions & Entities
    tx_file = data_source / "transactions.csv"
    if tx_file.exists() and (not file_filter or "trans" in file_filter):
        logger.info(f"Loading {tx_file}...")
        df_tx = pd.read_csv(tx_file, nrows=sample)
        
        # Customers
        df_cust = pd.DataFrame({
            "customer_id": df_tx["customer_id"].astype(str),
            "email_domain": df_tx["P_emaildomain"].fillna("").astype(str),
            "home_region": df_tx["addr1"].fillna("").astype(str),
            "first_seen": df_tx["ts"],
            "last_seen": df_tx["ts"]
        }).drop_duplicates(subset=["customer_id"])
        conn.upsertVertexDataFrame(df_cust, vertexType="Customer", v_id="customer_id")
        logger.info(f"  Loaded {len(df_cust)} Customer vertices")

        # Cards
        card_ids = df_tx.apply(lambda r: f"{r['card1']}_{r['card2']}_{r['card3']}_{r['card4']}_{r['card5']}_{r['card6']}", axis=1)
        df_cards = pd.DataFrame({
            "card_id": card_ids,
            "card1": df_tx["card1"].fillna("").astype(str),
            "card2": df_tx["card2"].fillna("").astype(str),
            "card3": df_tx["card3"].fillna("").astype(str),
            "card4": df_tx["card4"].fillna("").astype(str),
            "card5": df_tx["card5"].fillna("").astype(str),
            "card6": df_tx["card6"].fillna("").astype(str),
            "network": df_tx["card4"].fillna("").astype(str),
            "card_type": df_tx["card6"].fillna("").astype(str)
        }).drop_duplicates(subset=["card_id"])
        conn.upsertVertexDataFrame(df_cards, vertexType="Card", v_id="card_id")
        logger.info(f"  Loaded {len(df_cards)} Card vertices")

        # Email Domains
        domains = df_tx["P_emaildomain"].dropna().unique()
        if len(domains) > 0:
            df_domains = pd.DataFrame({"domain": domains})
            conn.upsertVertexDataFrame(df_domains, vertexType="EmailDomain", v_id="domain")
            logger.info(f"  Loaded {len(df_domains)} EmailDomain vertices")

        # Billing Regions
        regions = df_tx["addr1"].dropna().unique()
        if len(regions) > 0:
            df_regions = pd.DataFrame({"region_code": regions.astype(str), "country_code": ""})
            conn.upsertVertexDataFrame(df_regions, vertexType="BillingRegion", v_id="region_code")
            logger.info(f"  Loaded {len(df_regions)} BillingRegion vertices")

        # Transactions
        df_trans = pd.DataFrame({
            "transaction_id": df_tx["TransactionID"].astype(str),
            "ts": df_tx["ts"],
            "amount": df_tx["TransactionAmt"].astype(float),
            "channel": df_tx["channel"].fillna("").astype(str),
            "product_cd": df_tx["ProductCD"].fillna("").astype(str),
            "risk_score": df_tx["risk_score"].fillna(0.0).astype(float),
            "is_fraud": 0,
            "dist1": df_tx["dist1"].fillna(0.0).astype(float),
            "dist2": df_tx["dist2"].fillna(0.0).astype(float),
            "p_emaildomain": df_tx["P_emaildomain"].fillna("").astype(str)
        })
        conn.upsertVertexDataFrame(df_trans, vertexType="Transaction", v_id="transaction_id")
        logger.info(f"  Loaded {len(df_trans)} Transaction vertices")

        # OWNS & MADE edges
        df_owns = pd.DataFrame({"source": df_tx["customer_id"].astype(str), "target": card_ids, "since": df_tx["ts"]}).drop_duplicates(subset=["source", "target"])
        conn.upsertEdgeDataFrame(df_owns, sourceVertexType="Customer", edgeType="OWNS", targetVertexType="Card", from_id="source", to_id="target", attributes={"since": "since"})
        
        df_made = pd.DataFrame({"source": card_ids, "target": df_tx["TransactionID"].astype(str), "ts": df_tx["ts"]})
        conn.upsertEdgeDataFrame(df_made, sourceVertexType="Card", edgeType="MADE", targetVertexType="Transaction", from_id="source", to_id="target", attributes={"ts": "ts"})

        # PURCHASER_EMAIL
        df_email_edge = df_tx[df_tx["P_emaildomain"].notna()][["TransactionID", "P_emaildomain"]].rename(columns={"TransactionID": "source", "P_emaildomain": "target"})
        if not df_email_edge.empty:
            df_email_edge["source"] = df_email_edge["source"].astype(str)
            df_email_edge["target"] = df_email_edge["target"].astype(str)
            conn.upsertEdgeDataFrame(df_email_edge, sourceVertexType="Transaction", edgeType="PURCHASER_EMAIL", targetVertexType="EmailDomain", from_id="source", to_id="target", attributes={})

        # BILLED_IN
        df_billed_edge = df_tx[df_tx["addr1"].notna()][["TransactionID", "addr1"]].rename(columns={"TransactionID": "source", "addr1": "target"})
        if not df_billed_edge.empty:
            df_billed_edge["source"] = df_billed_edge["source"].astype(str)
            df_billed_edge["target"] = df_billed_edge["target"].astype(str)
            conn.upsertEdgeDataFrame(df_billed_edge, sourceVertexType="Transaction", edgeType="BILLED_IN", targetVertexType="BillingRegion", from_id="source", to_id="target", attributes={})

    # 2. Identity
    id_file = data_source / "identity.csv"
    if id_file.exists() and (not file_filter or "ident" in file_filter):
        logger.info(f"Loading {id_file}...")
        df_id = pd.read_csv(id_file, nrows=sample)
        profile_ids = df_id.apply(lambda r: f"{r['id_30']}_{r['id_31']}_{r['id_33']}", axis=1)
        
        df_dev = pd.DataFrame({
            "profile_id": profile_ids,
            "device_type": df_id["DeviceType"].fillna("").astype(str),
            "device_info": df_id["DeviceInfo"].fillna("").astype(str),
            "os": df_id["id_30"].fillna("").astype(str),
            "browser": df_id["id_31"].fillna("").astype(str),
            "screen": df_id["id_33"].fillna("").astype(str),
            "proxy_flag": False
        }).drop_duplicates(subset=["profile_id"])
        conn.upsertVertexDataFrame(df_dev, vertexType="DeviceProfile", v_id="profile_id")
        
        df_from_dev = pd.DataFrame({"source": df_id["TransactionID"].astype(str), "target": profile_ids, "is_new_device": False})
        conn.upsertEdgeDataFrame(df_from_dev, sourceVertexType="Transaction", edgeType="FROM_DEVICE", targetVertexType="DeviceProfile", from_id="source", to_id="target", attributes={"is_new_device": "is_new_device"})
        logger.info(f"  Loaded {len(df_dev)} DeviceProfile vertices & edges")

    # 3. Closed Cases
    cc_file = data_source / "closed_cases_history.csv"
    if cc_file.exists() and (not file_filter or "closed" in file_filter):
        logger.info(f"Loading {cc_file}...")
        df_cc = pd.read_csv(cc_file, nrows=sample)
        df_closed = pd.DataFrame({
            "case_id": df_cc["case_id"].astype(str),
            "outcome": df_cc["outcome"].fillna("").astype(str),
            "pattern": df_cc["pattern"].fillna("").astype(str),
            "exposure_usd": df_cc["exposure_usd"].fillna(0.0).astype(float),
            "actions_taken": df_cc["actions_taken"].fillna("").astype(str),
            "analyst_notes": df_cc["analyst_notes"].fillna("").astype(str),
            "opened_at": df_cc["opened_at"],
            "closed_at": df_cc["closed_at"]
        })
        conn.upsertVertexDataFrame(df_closed, vertexType="ClosedCase", v_id="case_id")
        logger.info(f"  Loaded {len(df_closed)} ClosedCase vertices")

    # 4. Case Pack
    cp_file = data_source / "case_pack.csv"
    if cp_file.exists() and (not file_filter or "pack" in file_filter):
        logger.info(f"Loading {cp_file}...")
        df_cp = pd.read_csv(cp_file)
        df_fc = pd.DataFrame({
            "case_id": df_cp["case_id"].astype(str),
            "trigger_type": df_cp["trigger_type"].fillna("").astype(str),
            "trigger_text": df_cp["trigger_text"].fillna("").astype(str),
            "flagged_txn_id": df_cp["flagged_txn_id"].fillna("").astype(str),
            "card_id": df_cp["card_id"].fillna("").astype(str),
            "customer_id": df_cp["customer_id"].fillna("").astype(str),
            "risk_score": df_cp["risk_score"].fillna(0.0).astype(float),
            "status": "TRIGGERED",
            "fraud_probability": 0.0,
            "confidence": 0.0,
            "risk_level": "",
            "pattern": "",
            "final_verdict": "",
            "created_at": df_cp["opened_at"],
            "updated_at": df_cp["opened_at"],
            "case_json": ""
        })
        conn.upsertVertexDataFrame(df_fc, vertexType="FraudCase", v_id="case_id")
        logger.info(f"  Loaded {len(df_fc)} FraudCase benchmark vertices")

    logger.success("Data loading complete!")

    # Step 4: Verify counts
    try:
        stats = conn.getVertexCount("*")
        logger.info(f"Vertex counts in TigerGraph: {stats}")
    except Exception as e:
        logger.warning(f"Could not fetch vertex counts: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load FraudLens CSV data into TigerGraph")
    parser.add_argument("--sample", type=int, help="Load only first N rows (for dev)")
    parser.add_argument("--file", type=str, help="Load specific file (e.g., 'transactions')")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSVs without loading")
    args = parser.parse_args()

    load_data(sample=args.sample, file_filter=args.file, dry_run=args.dry_run)
