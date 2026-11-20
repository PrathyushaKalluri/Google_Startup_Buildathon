#!/usr/bin/env python3
"""
Keepwell Part A PostgreSQL 16 Idempotent Seed Loader (db/seed/load_seed.py).
Uses psycopg 3 directly against PostgreSQL 16:
  1. Loads input/docs/keepwell_schema.sql unmodified.
  2. Configures role `kw_app` as LOGIN NOSUPERUSER NOBYPASSRLS.
  3. Loads all 55 CSV tables from input/dataset/csv/ via PostgreSQL COPY FROM STDIN.
  4. Applies db/migrations/001_part_a_additions.sql.
  5. Verifies exact row counts against input/dataset/manifest.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg

KEEPWELL_ROOT = Path(__file__).resolve().parents[2]
if str(KEEPWELL_ROOT) not in sys.path:
    sys.path.insert(0, str(KEEPWELL_ROOT))

from services.common.config import settings


def verify_seed_counts(counts: Dict[str, int]) -> None:
    manifest: List[Dict[str, Any]] = json.loads(
        (settings.dataset_dir / "manifest.json").read_text(encoding="utf-8")
    )
    for entry in manifest:
        table = entry["table"]
        expected = int(entry["rows"])
        actual = counts.get(table, -1)
        if actual != expected:
            raise AssertionError(f"Seed count mismatch for {table}: expected {expected}, got {actual}")


def load_seed_postgres(admin_dsn: Optional[str] = None) -> Dict[str, int]:
    """Load unmodified keepwell_schema.sql + 55 CSVs + additive migration 001 into PostgreSQL 16."""
    dsn = admin_dsn or settings.admin_psycopg_dsn
    schema_sql = (KEEPWELL_ROOT / "input" / "docs" / "keepwell_schema.sql").read_text(encoding="utf-8")
    mig_sql = (KEEPWELL_ROOT / "db" / "migrations" / "001_part_a_additions.sql").read_text(encoding="utf-8")
    manifest: List[Dict[str, Any]] = json.loads(
        (settings.dataset_dir / "manifest.json").read_text(encoding="utf-8")
    )
    csv_dir = settings.dataset_dir / "csv"

    counts: Dict[str, int] = {}
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS kw CASCADE;")
            cur.execute(schema_sql)
            # Ensure kw_app is a non-superuser login role with NO RLS bypass
            cur.execute("ALTER ROLE kw_app WITH LOGIN PASSWORD 'kw_app_dev' NOSUPERUSER NOBYPASSRLS;")
            cur.execute("SET search_path = kw, public;")

            for entry in manifest:
                table = entry["table"]
                cols = entry["columns"]
                col_list = ", ".join(f'"{c}"' for c in cols)
                csv_file = csv_dir / f"{table}.csv"
                copy_sql = (
                    f'COPY kw."{table}" ({col_list}) '
                    f"FROM STDIN WITH (FORMAT csv, HEADER true, NULL '\\N')"
                )
                with csv_file.open("rb") as fh:
                    with cur.copy(copy_sql) as copy:
                        while chunk := fh.read(65536):
                            copy.write(chunk)
                cur.execute(f'SELECT count(*) FROM kw."{table}"')
                row = cur.fetchone()
                counts[table] = int(row[0]) if row else 0

            # Apply Part A additive migration AFTER historical seed
            cur.execute(mig_sql)
        conn.commit()

    verify_seed_counts(counts)
    return counts


def load_seed() -> Dict[str, int]:
    settings.require_postgres()
    return load_seed_postgres()


if __name__ == "__main__":
    counts = load_seed()
    total = sum(counts.values())
    print(f"Loaded {len(counts)} tables ({total} rows) into PostgreSQL 16 successfully.")
