from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from services.common.config import KEEPWELL_ROOT, settings
from services.common.crypto import encrypt_phone, hash_phone_bytes, hash_phone_hex


CENTRE_ISOLATED_TABLES = {
    "ticket",
    "conversation",
    "urgency_assessment",
    "consent_gate",
    "clarifying_qa",
    "diagnosis_session",
    "diagnosis_media",
    "fix_attempt",
    "visit_plan",
    "plan_hypothesis",
    "plan_part",
    "assignment_candidate",
    "slot_proposal",
    "quote",
    "quote_line",
    "visit",
    "visit_media",
    "visit_part_used",
    "reservation",
    "route",
    "route_stop",
    "settlement_line",
    "feedback",
    "reminder",
    "brand_referral",
    "retailer_handover",
    "centre_price",
    "centre_commercial",
    "technician",
    "technician_skill",
    "technician_availability",
    "technician_metrics",
    "visit_debrief",
    "payment_intent",
}


def parse_pg_array(val: Optional[str]) -> List[str]:
    """Parse PostgreSQL text[] CSV literal like '{"a","b"}' or '{a,b}' into Python list."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    s = val.strip()
    if s in ("{}", ""):
        return []
    if s.startswith("["):
        try:
            return json.loads(s)
        except Exception:
            pass
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1]
        if not inner:
            return []
        out: List[str] = []
        cur = ""
        in_quotes = False
        esc = False
        for ch in inner:
            if esc:
                cur += ch
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_quotes = not in_quotes
            elif ch == "," and not in_quotes:
                out.append(cur)
                cur = ""
            else:
                cur += ch
        out.append(cur)
        return out
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


def parse_pg_point(val: Optional[str]) -> Optional[Tuple[float, float]]:
    """Parse 'SRID=4326;POINT(lon lat)' -> (lat, lon)."""
    if not val or "POINT(" not in val:
        return None
    try:
        coords = val.split("POINT(", 1)[1].rstrip(")").strip().split()
        lon, lat = float(coords[0]), float(coords[1])
        return (lat, lon)
    except Exception:
        return None


def _sqlite_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1))
    return KEEPWELL_ROOT / "db" / "keepwell_part_a.db"


class RLSSession:
    """
    Row-Level Security aware database session.
    In PostgreSQL mode: runs SET LOCAL kw.centre_id / SET LOCAL kw.role = 'platform' inside one tx.
    In SQLite dev/test mode: enforces identical centre isolation, household_centre_link checks,
    and SECURITY DEFINER cross-centre helpers in Python.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        centre_id: Optional[str] = None,
        role: str = "centre_admin",
    ):
        self.conn = conn
        self.centre_id = centre_id
        self.role = role

    @property
    def is_platform(self) -> bool:
        return self.role == "platform"

    def _rls_where(self, table: str) -> Tuple[str, List[Any]]:
        if self.is_platform:
            return ("1=1", [])
        if table in CENTRE_ISOLATED_TABLES:
            if not self.centre_id:
                return ("1=0", [])
            return ("centre_id = ?", [self.centre_id])
        if table == "stock":
            if not self.centre_id:
                return ("centre_id IS NULL", [])
            return ("(centre_id IS NULL OR centre_id = ?)", [self.centre_id])
        if table == "household":
            if not self.centre_id:
                return ("1=0", [])
            return (
                "id IN (SELECT household_id FROM household_centre_link WHERE centre_id = ?)",
                [self.centre_id],
            )
        if table in ("household_member", "appliance"):
            if not self.centre_id:
                return ("1=0", [])
            return (
                "household_id IN (SELECT household_id FROM household_centre_link WHERE centre_id = ?)",
                [self.centre_id],
            )
        if table == "appliance_event":
            if not self.centre_id:
                return ("1=0", [])
            return (
                "(centre_id = ? OR (centre_id IS NULL AND appliance_id IN "
                "(SELECT a.id FROM appliance a JOIN household_centre_link l ON l.household_id = a.household_id WHERE l.centre_id = ?)))",
                [self.centre_id, self.centre_id],
            )
        if table == "access_log":
            if not self.centre_id:
                return ("1=0", [])
            return (
                "(actor_centre_id = ? OR owner_centre_id = ?)",
                [self.centre_id, self.centre_id],
            )
        return ("1=1", [])

    def select(
        self,
        table: str,
        where: Optional[str] = None,
        params: Sequence[Any] = (),
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rls_sql, rls_params = self._rls_where(table)
        clauses = [rls_sql]
        all_params: List[Any] = list(rls_params)
        if where:
            clauses.append(f"({where})")
            all_params.extend(params)
        sql = f'SELECT * FROM "{table}" WHERE ' + " AND ".join(clauses)
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        cur = self.conn.execute(sql, all_params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def select_one(
        self,
        table: str,
        where: str,
        params: Sequence[Any] = (),
        order_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        rows = self.select(table, where=where, params=params, order_by=order_by, limit=1)
        return rows[0] if rows else None

    def raw_query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        cur = self.conn.execute(sql, params)
        if not cur.description:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_platform and table in CENTRE_ISOLATED_TABLES:
            if "centre_id" in row and row["centre_id"] != self.centre_id:
                raise PermissionError(f"RLS violation: cannot insert into {table} for another centre")
            row = {**row, "centre_id": self.centre_id}
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        vals = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else (
                ("t" if v else "f") if isinstance(v, bool) else v
            )
            for v in row.values()
        ]
        self.conn.execute(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})', vals)
        return row

    def update(
        self,
        table: str,
        updates: Dict[str, Any],
        where: str,
        params: Sequence[Any] = (),
    ) -> int:
        rls_sql, rls_params = self._rls_where(table)
        set_parts = [f'"{k}" = ?' for k in updates.keys()]
        set_vals = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else (
                ("t" if v else "f") if isinstance(v, bool) else v
            )
            for v in updates.values()
        ]
        sql = f'UPDATE "{table}" SET {", ".join(set_parts)} WHERE {rls_sql} AND ({where})'
        cur = self.conn.execute(sql, set_vals + rls_params + list(params))
        return cur.rowcount

    # ---- SECURITY DEFINER cross-centre functions (Schema Section 12) ----

    def centre_authority(self, centre_id: str, brand_id: str, on_date: Optional[str] = None) -> str:
        """Mirrors kw.centre_authority(p_centre, p_brand, p_on)."""
        d = on_date or datetime.now(timezone.utc).date().isoformat()
        rows = self.raw_query(
            """
            SELECT level FROM centre_brand_authorisation
            WHERE centre_id = ? AND brand_id = ?
              AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)
            ORDER BY CASE level
              WHEN 'authorised_service' THEN 1
              WHEN 'installation_only' THEN 2
              ELSE 3 END
            LIMIT 1
            """,
            (centre_id, brand_id, d, d),
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
        """Mirrors kw.identify_household() + external_ref member lookup (Q1)."""
        p_hex = hash_phone_hex(phone)
        p_pg_bytea = "\\x" + p_hex
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check external_ref first (covers both household and household_member numbers)
        ref = self.raw_query(
            """
            SELECT x.entity_id AS household_id
            FROM external_ref x
            JOIN household h ON h.id = x.entity_id AND h.status = 'active'
            WHERE x.entity_type = 'household' AND x.ref_type = 'phone' AND x.ref_norm = ?
            LIMIT 1
            """,
            (p_hex,),
        )
        hid: Optional[str] = ref[0]["household_id"] if ref else None
        if not hid:
            hh = self.raw_query(
                "SELECT id FROM household WHERE phone_hash = ? AND status <> 'merged' LIMIT 1",
                (p_pg_bytea,),
            )
            if hh:
                hid = hh[0]["id"]
            else:
                hm = self.raw_query(
                    "SELECT household_id FROM household_member WHERE phone_hash = ? LIMIT 1",
                    (p_pg_bytea,),
                )
                if hm:
                    hid = hm[0]["household_id"]

        existed = hid is not None
        if not existed:
            hid = str(uuid.uuid4())
            p_enc_hex = "\\x" + encrypt_phone(phone).hex()
            self.conn.execute(
                """
                INSERT INTO household (
                  id, phone_enc, phone_hash, phone_verified_at, verified_via,
                  language, address_line, pincode, location_verified, access_notes,
                  preferred_slots, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'f', '{}', '{}', 'active', ?, ?)
                """,
                (hid, p_enc_hex, p_pg_bytea, now_iso, verified_via, language, address_line, pincode, now_iso, now_iso),
            )
            self.conn.execute(
                """
                INSERT INTO external_ref (
                  id, entity_type, entity_id, ref_type, ref_norm, owner_type, owner_id, verified, first_seen_at
                ) VALUES (?, 'household', ?, 'phone', ?, 'keepwell', NULL, 't', ?)
                """,
                (str(uuid.uuid4()), hid, p_hex, now_iso),
            )
            if display_name:
                self.conn.execute(
                    """
                    INSERT INTO household_member (
                      id, household_id, name, phone_enc, phone_hash, role, may_raise_ticket, created_at
                    ) VALUES (?, ?, ?, ?, ?, 'owner', 't', ?)
                    """,
                    (str(uuid.uuid4()), hid, display_name, p_enc_hex, p_pg_bytea, now_iso),
                )

        # Link to centre
        existing_link = self.raw_query(
            "SELECT contact_count FROM household_centre_link WHERE household_id = ? AND centre_id = ?",
            (hid, centre_id),
        )
        known_to_this_centre = bool(existing_link)
        if existing_link:
            cnt = int(existing_link[0]["contact_count"] or 0) + 1
            self.conn.execute(
                "UPDATE household_centre_link SET contact_count = ? WHERE household_id = ? AND centre_id = ?",
                (str(cnt), hid, centre_id),
            )
        else:
            self.conn.execute(
                "INSERT INTO household_centre_link (household_id, centre_id, first_contact_at, contact_count) VALUES (?, ?, ?, '1')",
                (hid, centre_id, now_iso),
            )

        other_centres = self.raw_query(
            "SELECT count(*) AS c FROM household_centre_link WHERE household_id = ? AND centre_id <> ?",
            (hid, centre_id),
        )[0]["c"]

        if existed and other_centres > 0 and not known_to_this_centre:
            self.conn.execute(
                """
                INSERT INTO access_log (
                  id, actor_type, actor_id, actor_centre_id, record_table, record_id,
                  owner_centre_id, cross_centre, ticket_id, reason, occurred_at
                ) VALUES (?, 'agent', 'identify_household', ?, 'household', ?, NULL, 't', NULL, ?, ?)
                """,
                (str(uuid.uuid4()), centre_id, hid, "identity lookup on first contact with this centre", now_iso),
            )

        return {
            "household_id": hid,
            "existed": existed,
            "known_to_this_centre": known_to_this_centre,
            "other_centres": int(other_centres),
            "verified_via": verified_via,
        }

    def shared_history_allowed(self, appliance_id: str) -> bool:
        """Mirrors kw.shared_history_allowed(p_appliance)."""
        rows = self.raw_query(
            """
            SELECT 1 FROM appliance a
            JOIN consent_ledger c
              ON c.subject_type = 'household'
             AND c.subject_id = a.household_id
             AND c.purpose = 'share_technical_history'
             AND c.withdrawn_at IS NULL
            WHERE a.id = ?
            LIMIT 1
            """,
            (appliance_id,),
        )
        return bool(rows)

    def read_shared_history(
        self,
        appliance_id: str,
        centre_id: str,
        ticket_id: Optional[str] = None,
        reason: str = "repeat or related fault",
    ) -> List[Dict[str, Any]]:
        """Mirrors kw.read_shared_history(): checks link & consent, writes access_log for cross-centre rows."""
        linked = self.raw_query(
            """
            SELECT 1 FROM household_centre_link l
            JOIN appliance a ON a.household_id = l.household_id
            WHERE a.id = ? AND l.centre_id = ?
            """,
            (appliance_id, centre_id),
        )
        if not linked and not self.is_platform:
            raise PermissionError(f"centre {centre_id} has no link to this household")

        ok = self.shared_history_allowed(appliance_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        if ok:
            cross_rows = self.raw_query(
                """
                SELECT id, centre_id FROM appliance_event
                WHERE appliance_id = ? AND visibility = 'technical' AND (centre_id IS NULL OR centre_id <> ?)
                """,
                (appliance_id, centre_id),
            )
            for r in cross_rows:
                self.conn.execute(
                    """
                    INSERT INTO access_log (
                      id, actor_type, actor_id, actor_centre_id, record_table, record_id,
                      owner_centre_id, cross_centre, ticket_id, reason, occurred_at
                    ) VALUES (?, 'agent', 'read_shared_history', ?, 'appliance_event', ?, ?, 't', ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), centre_id, r["id"], r["centre_id"], ticket_id, reason, now_iso),
                )

            return self.raw_query(
                """
                SELECT * FROM appliance_event
                WHERE appliance_id = ? AND (centre_id = ? OR visibility = 'technical')
                ORDER BY occurred_at
                """,
                (appliance_id, centre_id),
            )

        # No sharing consent: return ONLY own centre's rows
        return self.raw_query(
            """
            SELECT * FROM appliance_event
            WHERE appliance_id = ? AND centre_id = ?
            ORDER BY occurred_at
            """,
            (appliance_id, centre_id),
        )


@contextmanager
def get_rls_session(
    centre_id: Optional[str] = None,
    role: str = "centre_admin",
    db_path: Optional[Path] = None,
):
    target = db_path or _sqlite_path()
    if not target.exists():
        from db.seed.load_seed import load_seed_sqlite

        load_seed_sqlite(db_path=target, force_rebuild=True)

    conn = sqlite3.connect(str(target), check_same_thread=False)
    try:
        session = RLSSession(conn, centre_id=centre_id, role=role)
        yield session
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
