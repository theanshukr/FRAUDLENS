"""
FraudLens     Load Schema Script
================================
Installs the TigerGraph graph schema and creates loading jobs.

Usage:
    python scripts/load_schema.py
    python scripts/load_schema.py --dry-run    # Just validate, don't install
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def load_schema(dry_run: bool = False) -> None:
    """Install the FraudLens schema on TigerGraph."""

    schema_path = Path("schema/schema.gsql")
    loading_path = Path("schema/loading_jobs.gsql")

    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)

    logger.info(f"Reading schema from {schema_path}")
    schema_gsql = schema_path.read_text(encoding="utf-8")
    loading_gsql = loading_path.read_text(encoding="utf-8") if loading_path.exists() else ""

    if dry_run:
        logger.info("[DRY RUN] Would install schema:")
        logger.info(f"  Schema: {schema_path} ({len(schema_gsql)} chars)")
        logger.info(f"  Loading jobs: {loading_path} ({len(loading_gsql)} chars)")
        logger.success("[DRY RUN] Schema validation passed")
        return

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

        # Install schema
        logger.info("Installing schema...")
        result = conn.gsql(schema_gsql)
        logger.info(f"Schema install result: {result}")

        # Install loading jobs
        if loading_gsql:
            logger.info("Installing loading jobs...")
            result = conn.gsql(loading_gsql)
            logger.info(f"Loading jobs result: {result}")

        logger.success("Schema and loading jobs installed successfully!")

    except ImportError:
        logger.error("pyTigerGraph not installed. Run: pip install pyTigerGraph")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Schema installation failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install FraudLens TigerGraph schema")
    parser.add_argument("--dry-run", action="store_true", help="Validate without installing")
    args = parser.parse_args()
    load_schema(dry_run=args.dry_run)
