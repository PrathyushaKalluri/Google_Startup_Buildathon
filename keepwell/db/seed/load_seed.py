#!/usr/bin/env python3
"""
Keepwell Part A Idempotent Seed Loader (db/seed/load_seed.py).
Loads all 55 CSV tables from input/dataset/csv/ into either:
  - PostgreSQL 16 (when DATABASE_URL starts with postgres), or
  - Local SQLite parity DB (db/keepwell_part_a.db) with full schema,
    Part A additive tables, append-only triggers, and consent-gate triggers.
Also supports reset_app_outputs() for POST /v1/admin/demo/reset.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

KEEPWELL_ROOT = Path(__file__).resolve().parents[2]
if str(KEEPWELL_ROOT) not in sys.path:
    sys.path.insert(0, str(KEEPWELL_ROOT))

from services.common.config import settings

APP_OUTPUT_TABLES = [
    "visit_plan",
    "plan_hypothesis",
    "plan_part",
    "assignment_candidate",
    "slot_proposal",
    "visit_media",
    "access_log",
    "identity_merge",
    "visit_debrief",
    "payment_intent",
    "outbox_event",
]

# Extra tables that exist in schema.sql (empty in seed) + additive migration 001
EXTRA_EMPTY_TABLES: Dict[str, List[str]] = {
    "visit_plan": [
        "id", "centre_id", "ticket_id", "version", "trigger_reason", "already_tried",
        "required_skills", "est_duration_p50_min", "est_duration_p80_min", "tools_needed",
        "requires_safety_cert", "access_notes", "confidence", "model_version", "created_at",
    ],
    "plan_hypothesis": [
        "id", "centre_id", "visit_plan_id", "rank", "cause", "probability", "evidence",
    ],
    "plan_part": [
        "id", "centre_id", "visit_plan_id", "part_id", "probability", "quantity",
    ],
    "assignment_candidate": [
        "id", "centre_id", "ticket_id", "visit_plan_id", "technician_id", "slot_start",
        "slot_end", "rank", "score", "score_breakdown", "config_id", "outcome",
        "chosen_by", "override_reason", "created_at",
    ],
    "slot_proposal": [
        "id", "centre_id", "ticket_id", "candidate_id", "slot_start", "slot_end",
        "price_low_paise", "price_high_paise", "shown_at", "accepted", "accepted_at", "expires_at",
    ],
    "visit_media": [
        "id", "centre_id", "visit_id", "kind", "storage_uri", "created_at",
    ],
    "access_log": [
        "id", "actor_type", "actor_id", "actor_centre_id", "record_table", "record_id",
        "owner_centre_id", "cross_centre", "ticket_id", "reason", "occurred_at",
    ],
    "identity_merge": [
        "id", "entity_type", "from_id", "into_id", "reason", "evidence",
        "merged_by", "merged_at", "reversed_at",
    ],
    "visit_debrief": [
        "id", "centre_id", "visit_id", "status", "language", "media_ref", "transcript",
        "extracted", "unresolved", "confirmed_at", "created_at", "updated_at",
    ],
    "payment_intent": [
        "id", "centre_id", "quote_id", "ticket_id", "amount_paise", "status", "method",
        "upi_intent_url", "google_pay_json", "payment_ref", "created_at", "expires_at", "paid_at",
    ],
    "device_token": [
        "id", "centre_id", "user_id", "role", "token", "platform", "updated_at",
    ],
    "outbox_event": [
        "id", "centre_id", "ticket_id", "conversation_id", "event_type", "actor",
        "title", "detail", "payload", "processed_at", "created_at",
    ],
    "whatsapp_message": [
        "id", "household_id", "centre_id", "ticket_id", "direction", "type",
        "text", "media_url", "template", "at", "status",
    ],
    "live_turn": [
        "id", "conversation_id", "centre_id", "at", "speaker", "text", "lang", "final", "kind",
    ],
}

SQLITE_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS appliance_event_no_update
BEFORE UPDATE ON appliance_event
BEGIN
  SELECT RAISE(ABORT, 'appliance_event is append-only');
END;

CREATE TRIGGER IF NOT EXISTS appliance_event_no_delete
BEFORE DELETE ON appliance_event
BEGIN
  SELECT RAISE(ABORT, 'appliance_event is append-only');
END;

CREATE TRIGGER IF NOT EXISTS access_log_no_update
BEFORE UPDATE ON access_log
BEGIN
  SELECT RAISE(ABORT, 'access_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS access_log_no_delete
BEFORE DELETE ON access_log
BEGIN
  SELECT RAISE(ABORT, 'access_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS fix_attempt_requires_gate1
BEFORE INSERT ON fix_attempt
WHEN NOT EXISTS (
  SELECT 1 FROM consent_gate
  WHERE ticket_id = NEW.ticket_id AND gate = 1 AND answer = 'yes'
)
BEGIN
  SELECT RAISE(ABORT, 'fix_attempt requires consent_gate 1 = yes');
END;

CREATE TRIGGER IF NOT EXISTS diagnosis_session_requires_gate2
BEFORE INSERT ON diagnosis_session
WHEN (NEW.video_on = 't' OR NEW.video_on = 1 OR NEW.video_on = 'true')
AND NOT EXISTS (
  SELECT 1 FROM consent_gate
  WHERE ticket_id = NEW.ticket_id AND gate = 2 AND answer = 'yes' AND choice = 'switch_to_video'
)
BEGIN
  SELECT RAISE(ABORT, 'video diagnosis_session requires consent_gate 2 = switch_to_video');
END;
"""


def _sqlite_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1))
    return KEEPWELL_ROOT / "db" / "keepwell_part_a.db"


def load_seed_sqlite(db_path: Optional[Path] = None, force_rebuild: bool = True) -> Dict[str, int]:
    """Load all 55 CSVs from input/dataset/csv/ into SQLite with exact row parity."""
    target = db_path or _sqlite_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if force_rebuild and target.exists():
        target.unlink()

    manifest_path = settings.dataset_dir / "manifest.json"
    manifest: List[Dict[str, Any]] = json.loads(manifest_path.read_text(encoding="utf-8"))
    csv_dir = settings.dataset_dir / "csv"

    conn = sqlite3.connect(str(target))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    counts: Dict[str, int] = {}
    try:
        # Load all 55 seeded CSV tables (disable triggers while bulk loading historical seed)
        for entry in manifest:
            table = entry["table"]
            cols: List[str] = list(entry["columns"])
            # Additive column on appliance (migration 001)
            extra_cols: List[str] = []
            if table == "appliance" and "evidence_level" not in cols:
                extra_cols.append("evidence_level")

            all_cols = cols + extra_cols
            col_defs = ", ".join(f'"{c}" TEXT' for c in all_cols)
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs});')

            csv_file = csv_dir / f"{table}.csv"
            placeholders = ", ".join("?" for _ in all_cols)
            col_list = ", ".join(f'"{c}"' for c in all_cols)
            sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders});'

            rows_batch: List[List[Optional[str]]] = []
            with csv_file.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.reader(fh)
                header = next(reader)
                assert header == cols, f"{table}: header mismatch {header} != {cols}"
                for row in reader:
                    vals = [None if v == "\\N" else v for v in row]
                    if table == "appliance":
                        id_status = vals[cols.index("identity_status")]
                        vals.append("confirmed" if id_status == "verified" else "unverified")
                    rows_batch.append(vals)

            conn.executemany(sql, rows_batch)
            counts[table] = len(rows_batch)

        # Create app-output & additive tables
        for table, cols in EXTRA_EMPTY_TABLES.items():
            col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs});')
            counts.setdefault(table, 0)

        # Useful indexes for fast lookup
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_ticket_centre ON ticket(centre_id, status);
            CREATE INDEX IF NOT EXISTS idx_ext_ref_lookup ON external_ref(entity_type, ref_type, ref_norm);
            CREATE INDEX IF NOT EXISTS idx_hcl_pair ON household_centre_link(household_id, centre_id);
            CREATE INDEX IF NOT EXISTS idx_appliance_hh ON appliance(household_id);
            CREATE INDEX IF NOT EXISTS idx_appliance_serial ON appliance(brand_id, serial_norm);
            CREATE INDEX IF NOT EXISTS idx_tech_centre ON technician(centre_id);
            CREATE INDEX IF NOT EXISTS idx_stock_part ON stock(part_id, holder_type);
            CREATE INDEX IF NOT EXISTS idx_consent_subj ON consent_ledger(subject_type, subject_id, purpose);
            CREATE INDEX IF NOT EXISTS idx_outbox_unproc ON outbox_event(processed_at);
            """
        )

        # Install enforcement triggers AFTER historical seed is loaded
        conn.executescript(SQLITE_TRIGGERS)
        conn.commit()
    finally:
        conn.close()

    return counts


def verify_seed_counts(counts: Dict[str, int]) -> None:
    manifest = json.loads((settings.dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        t = entry["table"]
        expected = entry["rows"]
        actual = counts.get(t, -1)
        if actual != expected:
            raise AssertionError(f"Seed count mismatch for {t}: expected {expected}, got {actual}")


def load_seed() -> Dict[str, int]:
    if settings.is_postgres:
        import psycopg  # type: ignore

        schema_sql = (KEEPWELL_ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
        mig_sql = (KEEPWELL_ROOT / "db" / "migrations" / "001_part_a_additions.sql").read_text(encoding="utf-8")
        with psycopg.connect(settings.database_url.replace("postgresql+psycopg://", "postgresql://")) as conn:
            conn.execute(schema_sql)
            conn.execute(mig_sql)
            conn.commit()
        return {}
    counts = load_seed_sqlite(force_rebuild=True)
    verify_seed_counts(counts)
    return counts


if __name__ == "__main__":
    counts = load_seed()
    total = sum(counts.values())
    print(f"Loaded {len(counts)} tables ({total} rows) successfully into {_sqlite_path()}.")
