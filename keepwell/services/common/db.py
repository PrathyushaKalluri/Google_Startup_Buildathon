from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Tuple

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from services.common.config import settings
from services.common.crypto import encrypt_phone, hash_phone_bytes, hash_phone_hex


def _normalise_value(val: Any) -> Any:
    """Convert PostgreSQL driver types (UUID, datetime, Decimal, memoryview) into JSON-friendly Python values."""
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, memoryview):
        return bytes(val)
    return val


def _normalise_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _normalise_value(v) for k, v in row.items()}


def parse_pg_array(val: Any) -> List[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, tuple):
        return [str(x) for x in val]
    s = str(val).strip()
    if s in ("{}", ""):
        return []
    if s.startswith("{") and s.endswith("}"):
        return [item.strip().strip('"') for item in s[1:-1].split(",") if item.strip()]
    return [s]


def parse_pg_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val != 0
    if isinstance(val, str):
        return val.lower() in ("t", "true", "1", "yes")
    return False


def parse_pg_json(val: Any, default: Any = None) -> Any:
    if val is None:
        return default if default is not None else {}
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default if default is not None else {}


def parse_pg_point(val: Any) -> Optional[Tuple[float, float]]:
    """Parse PostGIS WKT 'POINT(lon lat)' or 'SRID=4326;POINT(lon lat)' -> (lat, lon)."""
    if not val:
        return None
    s = str(val)
    if "POINT(" not in s:
        return None
    try:
        coords = s.split("POINT(", 1)[1].rstrip(")").strip().split()
        lon, lat = float(coords[0]), float(coords[1])
        return (lat, lon)
    except Exception:
        return None


JSONB_COLUMNS = {
    "specs", "covers", "steps", "condition", "hours", "commission_terms",
    "access_notes", "preferred_slots", "usage_profile", "care_index_reasons",
    "evidence", "weights", "params", "payload", "raw_inputs", "case_card",
    "facts", "observations", "details", "already_tried", "required_skills",
    "score_breakdown", "checklist", "parts", "extracted", "unresolved", "google_pay_json",
}


def _adapt_param(v: Any, col: Optional[str] = None) -> Any:
    if isinstance(v, Jsonb):
        return v
    if isinstance(v, dict):
        return Jsonb(v)
    if isinstance(v, list):
        if col in JSONB_COLUMNS or (v and isinstance(v[0], dict)):
            return Jsonb(v)
        return v
    return v


class RLSSession:
    """
    PostgreSQL 16 Row-Level Security session backed by psycopg 3.
    Connects as non-superuser `kw_app` (NOBYPASSRLS). Every transaction sets
    `SET LOCAL search_path = kw, public` and either `SET LOCAL kw.centre_id = %s`
    or `SET LOCAL kw.role = 'platform'`. PostgreSQL itself enforces all RLS policies.
    """

    def __init__(
        self,
        conn: psycopg.Connection[Dict[str, Any]],
        centre_id: Optional[str] = None,
        role: str = "centre_admin",
    ):
        self.conn = conn
        self.centre_id = centre_id
        self.role = role

    @property
    def is_platform(self) -> bool:
        return self.role == "platform"

    def raw_query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, tuple(_adapt_param(p) for p in params) if params else None)
            if cur.description is None:
                return []
            return [_normalise_row(r) for r in cur.fetchall()]

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(_adapt_param(p) for p in params) if params else None)
            return cur.rowcount

    def select(
        self,
        table: str,
        where: Optional[str] = None,
        params: Sequence[Any] = (),
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        sql = f'SELECT * FROM kw."{table}"'
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return self.raw_query(sql, params)

    def select_one(
        self,
        table: str,
        where: str,
        params: Sequence[Any] = (),
        order_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        rows = self.select(table, where=where, params=params, order_by=order_by, limit=1)
        return rows[0] if rows else None

    def insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        cols = list(row.keys())
        placeholders = ", ".join("%s" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        vals = [_adapt_param(v, col=k) for k, v in row.items()]
        with self.conn.cursor() as cur:
            cur.execute(f'INSERT INTO kw."{table}" ({col_list}) VALUES ({placeholders})', vals)
        return row

    def update(
        self,
        table: str,
        updates: Dict[str, Any],
        where: str,
        params: Sequence[Any] = (),
    ) -> int:
        set_parts = [f'"{k}" = %s' for k in updates.keys()]
        set_vals = [_adapt_param(v, col=k) for k, v in updates.items()]
        sql = f'UPDATE kw."{table}" SET {", ".join(set_parts)} WHERE {where}'
        with self.conn.cursor() as cur:
            cur.execute(sql, set_vals + list(params))
            return cur.rowcount

    # ---- Native PostgreSQL SECURITY DEFINER functions (Schema Section 12) ----

    def centre_authority(self, centre_id: str, brand_id: str, on_date: Optional[str] = None) -> str:
        """Calls native kw.centre_authority(p_centre, p_brand, p_on)."""
        d = on_date or datetime.now(timezone.utc).date().isoformat()
        rows = self.raw_query(
            "SELECT kw.centre_authority(%s::uuid, %s::uuid, %s::date) AS level",
            (centre_id, brand_id, d),
        )
        return rows[0]["level"] if rows else "none"

    def identify_household(
        self,
        phone: str,
        centre_id: str,
        verified_via: str = "call_line",
        display_name: Optional[str] = None,
        language: str = "en",
        address_line: Optional[str] = None,
        pincode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calls native kw.identify_household() + external_ref member lookup (Q1)."""
        p_bytes = hash_phone_bytes(phone)
        p_hex = p_bytes.hex()
        p_enc = encrypt_phone(phone)

        # Check external_ref first (handles household_member phones like C20)
        ref = self.raw_query(
            """
            SELECT x.entity_id AS household_id
            FROM kw.external_ref x
            WHERE x.entity_type = 'household' AND x.ref_type = 'phone' AND x.ref_norm = %s
            LIMIT 1
            """,
            (p_hex,),
        )
        if ref:
            hid = ref[0]["household_id"]
            # Ensure household_centre_link exists for this centre
            now_iso = datetime.now(timezone.utc).isoformat()
            existing = self.raw_query(
                "SELECT contact_count FROM kw.household_centre_link WHERE household_id = %s::uuid AND centre_id = %s::uuid",
                (hid, centre_id),
            )
            known_to_this_centre = bool(existing)
            if not known_to_this_centre:
                self.execute(
                    """
                    INSERT INTO kw.household_centre_link (household_id, centre_id, first_contact_at, contact_count)
                    VALUES (%s::uuid, %s::uuid, %s::timestamptz, 1)
                    ON CONFLICT (household_id, centre_id) DO UPDATE
                    SET contact_count = kw.household_centre_link.contact_count + 1
                    """,
                    (hid, centre_id, now_iso),
                )
            other_rows = self.raw_query(
                "SELECT count(*) AS c FROM kw.household_centre_link WHERE household_id = %s::uuid AND centre_id <> %s::uuid",
                (hid, centre_id),
            )
            return {
                "household_id": hid,
                "existed": True,
                "known_to_this_centre": known_to_this_centre,
                "other_centres": int(other_rows[0]["c"]),
                "verified_via": verified_via,
            }

        # Call native PostgreSQL SECURITY DEFINER kw.identify_household()
        rows = self.raw_query(
            "SELECT kw.identify_household(%s::bytea, %s::bytea, %s::uuid, %s::text) AS household_id",
            (p_bytes, p_enc, centre_id, verified_via),
        )
        hid = rows[0]["household_id"]

        # Store external_ref & optional profile fields if newly created
        now_iso = datetime.now(timezone.utc).isoformat()
        self.execute(
            """
            INSERT INTO kw.external_ref (entity_type, entity_id, ref_type, ref_norm, owner_type, owner_id, verified, first_seen_at)
            VALUES ('household', %s::uuid, 'phone', %s, 'keepwell', NULL, TRUE, %s::timestamptz)
            ON CONFLICT DO NOTHING
            """,
            (hid, p_hex, now_iso),
        )
        if address_line or pincode or language:
            self.execute(
                """
                UPDATE kw.household
                SET language = COALESCE(NULLIF(%s, ''), language),
                    address_line = COALESCE(address_line, %s),
                    pincode = COALESCE(pincode, %s)
                WHERE id = %s::uuid
                """,
                (language, address_line, pincode, hid),
            )
        if display_name:
            existing_mem = self.raw_query(
                "SELECT 1 FROM kw.household_member WHERE household_id = %s::uuid LIMIT 1",
                (hid,),
            )
            if not existing_mem:
                self.execute(
                    """
                    INSERT INTO kw.household_member (household_id, name, phone_enc, phone_hash, role, may_raise_ticket)
                    VALUES (%s::uuid, %s, %s::bytea, %s::bytea, 'owner', TRUE)
                    ON CONFLICT DO NOTHING
                    """,
                    (hid, display_name, p_enc, p_bytes),
                )

        other_rows = self.raw_query(
            "SELECT count(*) AS c FROM kw.household_centre_link WHERE household_id = %s::uuid AND centre_id <> %s::uuid",
            (hid, centre_id),
        )
        return {
            "household_id": hid,
            "existed": False,
            "known_to_this_centre": True,
            "other_centres": int(other_rows[0]["c"]),
            "verified_via": verified_via,
        }

    def shared_history_allowed(self, appliance_id: str) -> bool:
        """Calls native kw.shared_history_allowed(p_appliance)."""
        rows = self.raw_query(
            "SELECT kw.shared_history_allowed(%s::uuid) AS allowed",
            (appliance_id,),
        )
        return bool(rows[0]["allowed"]) if rows else False

    def read_shared_history(
        self,
        appliance_id: str,
        centre_id: str,
        ticket_id: Optional[str] = None,
        reason: str = "repeat or related fault",
    ) -> List[Dict[str, Any]]:
        """Calls native SECURITY DEFINER kw.read_shared_history() which checks consent and writes access_log."""
        return self.raw_query(
            "SELECT * FROM kw.read_shared_history(%s::uuid, %s::uuid, %s::uuid, %s::text)",
            (appliance_id, centre_id, ticket_id, reason),
        )


@contextmanager
def get_rls_session(
    centre_id: Optional[str] = None,
    role: str = "centre_admin",
    dsn: Optional[str] = None,
) -> Iterator[RLSSession]:
    """
    Open a single PostgreSQL 16 transaction as non-superuser `kw_app` (NOBYPASSRLS)
    and apply `SET LOCAL kw.centre_id` or `SET LOCAL kw.role = 'platform'`.
    """
    settings.require_postgres()
    conn_dsn = dsn or settings.psycopg_dsn
    with psycopg.connect(conn_dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL search_path = kw, public;")
            if role == "platform":
                cur.execute("SET LOCAL kw.role = 'platform';")
            elif centre_id:
                cur.execute("SELECT set_config('kw.centre_id', %s, true);", (centre_id,))
        session = RLSSession(conn, centre_id=centre_id, role=role)
        try:
            yield session
            conn.commit()
        except Exception:
            conn.rollback()
            raise


@asynccontextmanager
async def async_get_rls_session(
    centre_id: Optional[str] = None,
    role: str = "centre_admin",
    dsn: Optional[str] = None,
) -> AsyncIterator[psycopg.AsyncConnection[Dict[str, Any]]]:
    """
    Async psycopg 3 connection context manager for async FastAPI endpoints.
    Sets search_path and RLS session context inside one transaction as `kw_app`.
    """
    settings.require_postgres()
    conn_dsn = dsn or settings.psycopg_dsn
    aconn = await psycopg.AsyncConnection.connect(conn_dsn, autocommit=False, row_factory=dict_row)
    try:
        async with aconn.cursor() as cur:
            await cur.execute("SET LOCAL search_path = kw, public;")
            if role == "platform":
                await cur.execute("SET LOCAL kw.role = 'platform';")
            elif centre_id:
                await cur.execute("SELECT set_config('kw.centre_id', %s, true);", (centre_id,))
        yield aconn
        await aconn.commit()
    except Exception:
        await aconn.rollback()
        raise
    finally:
        await aconn.close()
