"""
FraudLens — High-Speed Chunked Loader for Transactions
======================================================
Loads transactions.csv into TigerGraph in 10,000-row batches.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
import pyTigerGraph as tg

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
tx_file = DATA_DIR / "transactions.csv"

def get_connection():
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
    return conn

def load_chunked(batch_size: int = 10000, max_batches: int = None):
    conn = get_connection()
    logger.info(f"Connected to TigerGraph: {conn.host}")
    logger.info(f"Reading {tx_file} in chunks of {batch_size}...")

    total_loaded = 0
    chunk_iter = pd.read_csv(tx_file, chunksize=batch_size, low_memory=False)

    for i, df_tx in enumerate(chunk_iter):
        if max_batches and i >= max_batches:
            break
        
        # Customers
        df_cust = pd.DataFrame({
            "customer_id": df_tx["customer_id"].astype(str),
            "email_domain": df_tx["P_emaildomain"].fillna("").astype(str),
            "home_region": df_tx["addr1"].fillna("").astype(str),
            "first_seen": df_tx["ts"],
            "last_seen": df_tx["ts"]
        }).drop_duplicates(subset=["customer_id"])
        conn.upsertVertexDataFrame(df_cust, vertexType="Customer", v_id="customer_id")

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

        # Email Domains
        domains = df_tx["P_emaildomain"].dropna().unique()
        if len(domains) > 0:
            df_domains = pd.DataFrame({"domain": domains})
            conn.upsertVertexDataFrame(df_domains, vertexType="EmailDomain", v_id="domain")

        # Billing Regions
        regions = df_tx["addr1"].dropna().unique()
        if len(regions) > 0:
            df_regions = pd.DataFrame({"region_code": regions.astype(str), "country_code": ""})
            conn.upsertVertexDataFrame(df_regions, vertexType="BillingRegion", v_id="region_code")

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

        # Edges
        df_owns = pd.DataFrame({"source": df_tx["customer_id"].astype(str), "target": card_ids, "since": df_tx["ts"]}).drop_duplicates(subset=["source", "target"])
        conn.upsertEdgeDataFrame(df_owns, sourceVertexType="Customer", edgeType="OWNS", targetVertexType="Card", from_id="source", to_id="target", attributes={"since": "since"})
        
        df_made = pd.DataFrame({"source": card_ids, "target": df_tx["TransactionID"].astype(str), "ts": df_tx["ts"]})
        conn.upsertEdgeDataFrame(df_made, sourceVertexType="Card", edgeType="MADE", targetVertexType="Transaction", from_id="source", to_id="target", attributes={"ts": "ts"})

        total_loaded += len(df_tx)
        logger.info(f"Batch {i+1} loaded: {total_loaded:,} transactions processed")

    logger.success(f"All transactions loaded: {total_loaded:,} rows.")

if __name__ == "__main__":
    load_chunked(batch_size=10000)
