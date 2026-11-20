from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from services.common.config import settings
from services.common.db import RLSSession, parse_pg_bool, parse_pg_json


def _fs_safe(val: Any) -> Any:
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (uuid.UUID, Decimal)):
        return str(val)
    if isinstance(val, dict):
        return {str(k): _fs_safe(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_fs_safe(v) for v in val]
    return val


class FirestoreProjectionStore:
    """
    Projects committed PostgreSQL state into Firestore paths defined in Contract C6 & C8.
    - When FIRESTORE_EMULATOR_HOST is set: writes to the Firestore Emulator (`emulator`).
    - When LIVE_GOOGLE=1 (or USE_LIVE_FIRESTORE=1) with ADC/GCP project: writes to real
      Firestore Native (`real_firestore`).
    - Otherwise (offline tests): maintains an in-memory path-keyed store (`memory_fallback`).
    """

    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}
        self._fs_client: Any = None
        self.backend_mode: str = "memory_fallback"
        self.refresh_client()

    def refresh_client(self) -> str:
        """Initialise or refresh the Firestore client based on current env."""
        emu = os.getenv("FIRESTORE_EMULATOR_HOST") or settings.firestore_emulator_host
        use_live = os.getenv("LIVE_GOOGLE") == "1" or os.getenv("USE_LIVE_FIRESTORE") == "1"
        if emu:
            try:
                from google.cloud import firestore  # type: ignore

                self._fs_client = firestore.Client(project=settings.firebase_project_id)
                self.backend_mode = "emulator"
                return self.backend_mode
            except Exception:
                self._fs_client = None
                self.backend_mode = "memory_fallback"
                return self.backend_mode
        if use_live and settings.gcp_project_id and settings.gcp_project_id != "keepwell-dev":
            try:
                from google.cloud import firestore  # type: ignore

                self._fs_client = firestore.Client(project=settings.gcp_project_id)
                self.backend_mode = "real_firestore"
                return self.backend_mode
            except Exception:
                self._fs_client = None
                self.backend_mode = "memory_fallback"
                return self.backend_mode
        self._fs_client = None
        self.backend_mode = "memory_fallback"
        return self.backend_mode

    def set_doc(self, path: str, data: Dict[str, Any], *, defer_remote: bool = False) -> Dict[str, Any]:
        safe = _fs_safe(data)
        self.docs[path] = safe
        if self._fs_client is not None and not defer_remote:
            try:
                self._fs_client.document(path).set(safe, merge=True)
            except Exception:
                pass
        return safe

    def flush_all_remote(self) -> int:
        """Batch-write all in-memory docs to Firestore (400 docs/batch) for fast idempotent rebuilds."""
        if self._fs_client is None:
            return 0
        items = list(self.docs.items())
        written = 0
        chunk_size = 400
        for i in range(0, len(items), chunk_size):
            batch = self._fs_client.batch()
            for path, data in items[i : i + chunk_size]:
                batch.set(self._fs_client.document(path), data, merge=True)
                written += 1
            batch.commit()
        return written

    def get_doc(self, path: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(path)

    def list_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        return [v for k, v in self.docs.items() if k.startswith(prefix)]

    def clear(self) -> None:
        self.docs.clear()

    # ---- Typed Contract C6 & C8 Writers ----

    def emit_event(
        self,
        db: RLSSession,
        centre_id: str,
        event_type: str,
        actor: str,
        title: str,
        detail: str = "",
        ticket_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Write to Postgres outbox_event AND project to centres/{cid}/feed/{event_id}."""
        eid = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        ev = {
            "id": eid,
            "at": now_iso,
            "centre_id": centre_id,
            "ticket_id": ticket_id,
            "conversation_id": conversation_id,
            "type": event_type,
            "actor": actor,
            "title": title,
            "detail": detail,
            "payload": payload or {},
        }
        db.execute(
            """
            INSERT INTO outbox_event (id, centre_id, ticket_id, conversation_id, event_type, actor, title, detail, payload, processed_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                eid,
                centre_id,
                ticket_id,
                conversation_id,
                event_type,
                actor,
                title,
                detail,
                json.dumps(payload or {}, ensure_ascii=False),
                now_iso,
                now_iso,
            ),
        )
        self.set_doc(f"centres/{centre_id}/feed/{eid}", ev)
        return ev

    def project_ticket(self, centre_id: str, ticket_card: Dict[str, Any], assignee: Optional[Dict[str, Any]] = None, payment_status: str = "none") -> Dict[str, Any]:
        doc = {
            **ticket_card,
            "unread": True,
            "last_event_at": ticket_card.get("updated_at") or datetime.now(timezone.utc).isoformat(),
            "assignee": assignee,
            "next_action": _derive_next_action(ticket_card.get("status", "new")),
            "payment_status": payment_status,
        }
        return self.set_doc(f"centres/{centre_id}/tickets/{ticket_card['id']}", doc)

    def project_conversation(self, centre_id: str, conv_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"centres/{centre_id}/conversations/{conv_id}", data)

    def project_turn(self, centre_id: str, conv_id: str, turn_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"centres/{centre_id}/conversations/{conv_id}/turns/{turn_id}", data)

    def project_technician(self, centre_id: str, tech_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"centres/{centre_id}/technicians/{tech_id}", data)

    def project_visit(self, centre_id: str, visit_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"centres/{centre_id}/visits/{visit_id}", data)

    def project_parts_request(self, centre_id: str, req_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"centres/{centre_id}/parts_requests/{req_id}", data)

    def project_whatsapp_message(self, household_id: str, msg_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_doc(f"households/{household_id}/whatsapp_thread/{msg_id}", data)

    def set_demo_meta(self, active_case_id: Optional[str] = None) -> Dict[str, Any]:
        return self.set_doc(
            "meta/demo",
            {
                "active_case_id": active_case_id,
                "reset_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def rebuild_all(self, db: RLSSession) -> Dict[str, int]:
        """Idempotently rebuild all Firestore projections from PostgreSQL 16."""
        self.refresh_client()
        self.clear()
        counts = {"tickets": 0, "technicians": 0, "visits": 0, "parts_requests": 0, "feed": 0}

        for t in db.raw_query("SELECT * FROM ticket"):
            cid = t["centre_id"]
            self.set_doc(
                f"centres/{cid}/tickets/{t['id']}",
                {
                    "id": t["id"],
                    "centre_id": cid,
                    "trigger": t["trigger"],
                    "channel": t["channel"],
                    "job_type": t["job_type"],
                    "status": t["status"],
                    "resolution": t["resolution"],
                    "urgency_class": t["urgency_class"],
                    "safety_flag": parse_pg_bool(t["safety_flag"]),
                    "unread": t["status"] in ("new", "triage", "escalated"),
                    "last_event_at": t["updated_at"] or t["created_at"],
                    "next_action": _derive_next_action(t["status"]),
                    "payment_status": "none",
                },
                defer_remote=True,
            )
            counts["tickets"] += 1

        for te in db.raw_query("SELECT * FROM technician WHERE active = TRUE"):
            self.set_doc(
                f"centres/{te['centre_id']}/technicians/{te['id']}",
                {
                    "name": te["name"],
                    "status": "available",
                    "current_visit_id": None,
                    "last_location": None,
                    "last_ping_at": te["updated_at"],
                },
                defer_remote=True,
            )
            counts["technicians"] += 1

        for v in db.raw_query("SELECT * FROM visit"):
            self.set_doc(
                f"centres/{v['centre_id']}/visits/{v['id']}",
                {
                    "ticket_id": v["ticket_id"],
                    "technician_id": v["technician_id"],
                    "planned_start": v["planned_start"],
                    "planned_end": v["planned_end"],
                    "status": v["outcome"] or "scheduled",
                    "brief": {},
                    "address_released": True,
                },
                defer_remote=True,
            )
            counts["visits"] += 1

        for r in db.raw_query("SELECT * FROM reservation"):
            self.set_doc(
                f"centres/{r['centre_id']}/parts_requests/{r['id']}",
                {
                    "visit_id": r["visit_id"],
                    "part_no": r["part_id"],
                    "quantity": int(r["quantity"] or 1),
                    "status": r["status"],
                    "parts_centre_id": r["holder_id"] if r["holder_type"] == "parts_centre" else None,
                },
                defer_remote=True,
            )
            counts["parts_requests"] += 1

        for ev in db.raw_query("SELECT * FROM outbox_event ORDER BY created_at"):
            cid = ev["centre_id"]
            if cid:
                self.set_doc(
                    f"centres/{cid}/feed/{ev['id']}",
                    {
                        "id": ev["id"],
                        "at": ev["created_at"],
                        "centre_id": cid,
                        "ticket_id": ev["ticket_id"],
                        "conversation_id": ev["conversation_id"],
                        "type": ev["event_type"],
                        "actor": ev["actor"],
                        "title": ev["title"],
                        "detail": ev["detail"],
                        "payload": parse_pg_json(ev["payload"], {}),
                    },
                    defer_remote=True,
                )
                counts["feed"] += 1

        self.set_doc(
            "meta/demo",
            {
                "active_case_id": None,
                "reset_at": datetime.now(timezone.utc).isoformat(),
            },
            defer_remote=True,
        )
        self.flush_all_remote()
        return counts


def _derive_next_action(status: str) -> str:
    return {
        "new": "triage",
        "triage": "assess_urgency",
        "clarifying": "await_household",
        "self_fix": "guide_safe_fix",
        "diagnosed": "plan_visit",
        "awaiting_slot": "confirm_slot",
        "booked": "prepare_parts",
        "scheduled": "dispatch_visit",
        "in_progress": "complete_visit",
        "needs_part": "source_part",
        "completed": "collect_otp",
        "closed": "done",
        "cancelled": "done",
        "escalated": "urgent_dispatch",
    }.get(status, "review")


projection_store = FirestoreProjectionStore()
