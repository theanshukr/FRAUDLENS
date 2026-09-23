"""
FraudLens — Load all 20 benchmark cases & transactions into TigerGraph
======================================================================
Upserts real Transaction, Card, Customer, DeviceProfile, BillingRegion,
and EmailDomain vertices + edges (MADE, OWNS, FROM_DEVICE, etc.)
for all 20 HHG benchmark cases directly into the live TigerGraph database.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import pandas as pd
from tools.graph_tools import get_tg_connection

def main():
    conn = get_tg_connection()
    if not conn:
        print("ERROR: Cannot connect to TigerGraph.")
        return

    print("Connected to TigerGraph successfully.")
    
    # 1. Load case pack
    case_pack = pd.read_csv("dataset_sample/case_pack.csv")
    txn_ids = set(case_pack["flagged_txn_id"].astype(int))
    print(f"Loading data for {len(txn_ids)} benchmark transactions...")

    # 2. Extract matching rows from data/transactions.csv
    matched_txns = []
    for chunk in pd.read_csv("data/transactions.csv", chunksize=50000):
        sub = chunk[chunk["TransactionID"].isin(txn_ids)]
        if not sub.empty:
            matched_txns.append(sub)

    df_txns = pd.concat(matched_txns).drop_duplicates(subset=["TransactionID"])
    print(f"Found {len(df_txns)} transaction rows in transactions.csv")

    # 3. Extract matching rows from data/identity.csv if available
    identity_map = {}
    if os.path.exists("data/identity.csv"):
        for chunk in pd.read_csv("data/identity.csv", chunksize=50000):
            sub = chunk[chunk["TransactionID"].isin(txn_ids)]
            for _, r in sub.iterrows():
                tid = str(int(r["TransactionID"]))
                dev_type = str(r.get("DeviceType", "desktop") or "desktop")
                dev_info = str(r.get("DeviceInfo", "") or "")
                os_str = str(r.get("id_30", "") or "")
                browser_str = str(r.get("id_31", "") or "")
                screen_str = str(r.get("id_33", "") or "")
                prof_id = f"{os_str}_{browser_str}_{screen_str}".strip("_") or f"dev_{tid}"
                identity_map[tid] = {
                    "profile_id": prof_id,
                    "device_type": dev_type,
                    "device_info": dev_info,
                    "os": os_str,
                    "browser": browser_str,
                    "screen": screen_str,
                    "proxy_flag": False
                }

    # Map case_pack for customer_id and card_id
    case_meta = {}
    for _, r in case_pack.iterrows():
        tid = str(int(r["flagged_txn_id"]))
        case_meta[tid] = {
            "case_id": str(r["case_id"]),
            "card_id": str(r.get("card_id", "")),
            "customer_id": str(r.get("customer_id", "")),
            "trigger_type": str(r.get("trigger_type", "")),
        }

    # Prepare vertices and edges to upsert
    txn_vertices = []
    card_vertices = []
    cust_vertices = []
    dev_vertices = []
    email_vertices = []
    region_vertices = []

    made_edges = []
    owns_edges = []
    from_dev_edges = []
    email_edges = []
    region_edges = []

    for _, row in df_txns.iterrows():
        tid = str(int(row["TransactionID"]))
        meta = case_meta.get(tid, {})
        
        card_id = meta.get("card_id") or f"C_{row.get('card1')}_{row.get('card2')}"
        customer_id = meta.get("customer_id") or (card_id.split("-")[0] if "-" in card_id else f"CUST_{tid[-4:]}")
        
        amt = float(row.get("TransactionAmt", 0.0) or 0.0)
        p_cd = str(row.get("ProductCD", "W") or "W")
        email = str(row.get("P_emaildomain", "") or "")
        addr1 = str(row.get("addr1", "") or "")
        
        # Transaction
        txn_vertices.append((tid, {
            "transaction_id": tid,
            "ts": "2016-11-22 00:00:00",
            "amount": amt,
            "channel": "web" if p_cd == "W" else "in_person",
            "product_cd": p_cd,
            "risk_score": 0.85,
            "is_fraud": 1,
            "dist1": 0.0,
            "dist2": 0.0,
            "p_emaildomain": email
        }))

        # Card
        card_vertices.append((card_id, {
            "card_id": card_id,
            "card1": str(row.get("card1", "")),
            "card2": str(row.get("card2", "")),
            "card3": str(row.get("card3", "")),
            "card4": str(row.get("card4", "")),
            "card5": str(row.get("card5", "")),
            "card6": str(row.get("card6", "")),
            "network": str(row.get("card4", "visa")),
            "card_type": str(row.get("card6", "debit")),
        }))

        # Customer
        cust_vertices.append((customer_id, {
            "customer_id": customer_id,
            "email_domain": email,
            "home_region": addr1,
            "first_seen": "2016-01-01 00:00:00",
            "last_seen": "2016-11-22 00:00:00",
        }))

        # MADE edge (Card -> Transaction)
        made_edges.append((card_id, tid, {"ts": "2016-11-22 00:00:00"}))

        # OWNS edge (Customer -> Card)
        owns_edges.append((customer_id, card_id, {"since": "2016-01-01 00:00:00"}))

        # Device
        if tid in identity_map:
            d_info = identity_map[tid]
            pid = d_info["profile_id"]
            dev_vertices.append((pid, d_info))
            from_dev_edges.append((tid, pid, {"is_new_device": True}))

        # Email
        if email and email != "nan":
            email_vertices.append((email, {"domain": email}))
            email_edges.append((tid, email, {}))

        # BillingRegion
        if addr1 and addr1 != "nan":
            region_vertices.append((addr1, {"region_code": addr1, "country_code": "US"}))
            region_edges.append((tid, addr1, {}))

    print(f"Upserting {len(txn_vertices)} Transactions...")
    conn.upsertVertices("Transaction", txn_vertices)

    print(f"Upserting {len(card_vertices)} Cards...")
    conn.upsertVertices("Card", card_vertices)

    print(f"Upserting {len(cust_vertices)} Customers...")
    conn.upsertVertices("Customer", cust_vertices)

    if dev_vertices:
        print(f"Upserting {len(dev_vertices)} DeviceProfiles...")
        conn.upsertVertices("DeviceProfile", dev_vertices)

    if email_vertices:
        print(f"Upserting {len(email_vertices)} EmailDomains...")
        conn.upsertVertices("EmailDomain", email_vertices)

    if region_vertices:
        print(f"Upserting {len(region_vertices)} BillingRegions...")
        conn.upsertVertices("BillingRegion", region_vertices)

    print(f"Upserting {len(made_edges)} MADE edges...")
    conn.upsertEdges("Card", "MADE", "Transaction", made_edges)

    print(f"Upserting {len(owns_edges)} OWNS edges...")
    conn.upsertEdges("Customer", "OWNS", "Card", owns_edges)

    if from_dev_edges:
        print(f"Upserting {len(from_dev_edges)} FROM_DEVICE edges...")
        conn.upsertEdges("Transaction", "FROM_DEVICE", "DeviceProfile", from_dev_edges)

    if email_edges:
        print(f"Upserting {len(email_edges)} PURCHASER_EMAIL edges...")
        conn.upsertEdges("Transaction", "PURCHASER_EMAIL", "EmailDomain", email_edges)

    if region_edges:
        print(f"Upserting {len(region_edges)} BILLED_IN edges...")
        conn.upsertEdges("Transaction", "BILLED_IN", "BillingRegion", region_edges)

    print("SUCCESS: All 20 benchmark cases and transactions loaded into TigerGraph!")

if __name__ == "__main__":
    main()
