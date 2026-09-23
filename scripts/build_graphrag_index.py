"""
FraudLens — Build GraphRAG Vector Index
========================================
Extracts historical closed cases from TigerGraph / closed_cases_history.csv,
generates dense vector embeddings, and builds a persistent VectorStore index.

Usage:
  python scripts/build_graphrag_index.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from loguru import logger
from tools.graphrag_tools import (
    TFIDFEmbeddingProvider,
    LocalVectorStore,
    VectorDocument,
    VECTOR_STORE_DIR,
)

DATA_DIR = REPO_ROOT / "data"
CLOSED_CASES_CSV = DATA_DIR / "closed_cases_history.csv"


def build_canonical_document(row: dict) -> tuple[str, dict]:
    """Construct a clean, information-dense text representation for embedding."""
    cid = str(row.get("case_id", "")).strip()
    cust = str(row.get("customer_id", "")).strip()
    card = str(row.get("card_id", "")).strip()
    pattern = str(row.get("pattern", "unknown")).strip()
    outcome = str(row.get("outcome", "unknown")).strip()
    exposure = float(row.get("exposure_usd", 0.0) or 0.0)
    actions = str(row.get("actions_taken", "")).strip()
    notes = str(row.get("analyst_notes", "")).strip()
    
    text = (
        f"Case {cid}: pattern={pattern}, outcome={outcome}, exposure=${exposure:.2f}. "
        f"Actions taken: {actions}. Investigation notes: {notes}"
    )

    metadata = {
        "case_id": cid,
        "customer_id": cust,
        "card_id": card,
        "pattern": pattern,
        "outcome": outcome,
        "exposure_usd": exposure,
        "actions_taken": actions,
        "analyst_notes": notes,
        "source": "closed_cases_history",
    }
    return text, metadata


def main():
    print("=" * 70)
    print("FraudLens — GraphRAG Vector Index Builder")
    print("=" * 70)

    if not CLOSED_CASES_CSV.exists():
        print(f"ERROR: {CLOSED_CASES_CSV} not found.")
        sys.exit(1)

    t0 = time.time()
    df = pd.read_csv(CLOSED_CASES_CSV)
    print(f"Loaded {len(df)} historical cases from {CLOSED_CASES_CSV.name}")

    # Build canonical texts
    texts = []
    metadata_list = []
    doc_ids = []

    for _, row in df.iterrows():
        text, meta = build_canonical_document(row.to_dict())
        texts.append(text)
        metadata_list.append(meta)
        doc_ids.append(meta["case_id"])

    # Fit TF-IDF embedding model on historical corpus
    print("Fitting TF-IDF embedding vectorizer on historical case narratives...")
    embedder = TFIDFEmbeddingProvider()
    embedder.fit_documents(texts)

    print("Generating dense vector embeddings for all cases...")
    embeddings = embedder.embed_documents(texts)

    # Build VectorDocuments
    vector_docs = []
    for i in range(len(doc_ids)):
        vector_docs.append(VectorDocument(
            doc_id=doc_ids[i],
            text=texts[i],
            metadata=metadata_list[i],
            embedding=embeddings[i],
        ))

    # Upsert into LocalVectorStore
    print(f"Upserting {len(vector_docs)} case vectors into VectorStore at {VECTOR_STORE_DIR}...")
    vstore = LocalVectorStore()
    vstore.upsert(vector_docs)

    elapsed = time.time() - t0
    print("=" * 70)
    print(f"GRAPHRAG INDEXING COMPLETE: {vstore.count()} cases indexed in {elapsed:.2f}s")
    print(f"Vector Store Directory: {VECTOR_STORE_DIR}")
    print("=" * 70)

    # Sanity check test query
    test_query = "card testing with micro authorization sequence on web channel"
    test_vec = embedder.embed_text(test_query)
    results = vstore.search(test_vec, top_k=3)
    print(f"\nSanity Check Search for query: '{test_query}'")
    for r in results:
        print(f"  - Case {r['case_id']} | Score: {r['score']:.4f} | Pattern: {r['metadata']['pattern']}")


if __name__ == "__main__":
    main()
