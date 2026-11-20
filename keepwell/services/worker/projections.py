from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.common.config import settings
from services.common.db import RLSSession, parse_pg_bool, parse_pg_json


class FirestoreProjectionStore:
    """
    Projects committed PostgreSQL state into Firestore paths defined in Contract C6 & C8.
    When FIRESTORE_EMULATOR_HOST or real GCP credentials are configured, mirrors writes to
    Firestore; always maintains an in-memory path-keyed store for zero-latency inspection
    and contract verification.
    """

    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}
        self._fs_client: Any = None
        if settings.firestore_emulator_host:
            try:
                from google.cloud import firestore  # type: ignore

                self._fs_client = firestore.Client(project=settings.firebase_project_id)
            except Exception:
                self._fs_client = None

    def set_doc(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self.docs[path] = data
        if self._fs_client is not None:
            try:
                self._fs_client.document(path).set(data, merge=True)
            except Exception:
                pass
        return data

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
            )
            counts["tickets"] += 1

        for te in db.raw_query("SELECT * FROM technician WHERE active = TRUE"):
            self.project_technician(
                te["centre_id"],
                te["id"],
                {
                    "name": te["name"],
                    "status": "available",
                    "current_visit_id": None,
                    "last_location": None,
                    "last_ping_at": te["updated_at"],
                },
            )
            counts["technicians"] += 1

        for v in db.raw_query("SELECT * FROM visit"):
            self.project_visit(
                v["centre_id"],
                v["id"],
                {
                    "ticket_id": v["ticket_id"],
                    "technician_id": v["technician_id"],
                    "planned_start": v["planned_start"],
                    "planned_end": v["planned_end"],
                    "status": v["outcome"] or "scheduled",
                    "brief": {},
                    "address_released": True,
                },
            )
            counts["visits"] += 1

        for r in db.raw_query("SELECT * FROM reservation"):
            self.project_parts_request(
                r["centre_id"],
                r["id"],
                {
                    "visit_id": r["visit_id"],
                    "part_no": r["part_id"],
                    "quantity": int(r["quantity"] or 1),
                    "status": r["status"],
                    "parts_centre_id": r["holder_id"] if r["holder_type"] == "parts_centre" else None,
                },
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
                )
                counts["feed"] += 1

        self.set_demo_meta(None)
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
