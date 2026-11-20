from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI

from services.common.db import get_rls_session
from services.common.logging import get_logger
from services.worker.projections import projection_store

logger = get_logger("keepwell.worker")
app = FastAPI(title="Keepwell Worker (kw-worker)", version="1.0.0")


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok", "service": "kw-worker"}


@app.post("/tasks/drain-outbox")
def drain_outbox() -> Dict[str, Any]:
    """Drain unprocessed outbox_event rows into Firestore projections."""
    processed = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_rls_session(role="platform") as db:
        rows = db.raw_query("SELECT * FROM outbox_event WHERE processed_at IS NULL ORDER BY created_at LIMIT 200")
        for r in rows:
            if r["centre_id"]:
                projection_store.set_doc(
                    f"centres/{r['centre_id']}/feed/{r['id']}",
                    {
                        "id": r["id"],
                        "at": r["created_at"],
                        "centre_id": r["centre_id"],
                        "ticket_id": r["ticket_id"],
                        "conversation_id": r["conversation_id"],
                        "type": r["event_type"],
                        "actor": r["actor"],
                        "title": r["title"],
                        "detail": r["detail"],
                        "payload": r["payload"],
                    },
                )
            db.conn.execute("UPDATE outbox_event SET processed_at = ? WHERE id = ?", (now_iso, r["id"]))
            processed += 1
    return {"processed": processed}


@app.post("/scheduler/reminders")
def dispatch_due_reminders(monthly_cap: int = 2) -> Dict[str, Any]:
    """Q20: Send due reminders only from last_served_centre_id with active consent and monthly cap."""
    sent: List[str] = []
    today = datetime.now(timezone.utc).date().isoformat()
    month_prefix = today[:7]
    with get_rls_session(role="platform") as db:
        due = db.raw_query(
            """
            SELECT r.id, r.centre_id, r.household_id, r.appliance_id, r.reminder_type, r.template_name
            FROM reminder r
            JOIN household h ON h.id = r.household_id AND h.status = 'active'
            JOIN appliance a ON a.id = r.appliance_id AND a.last_served_centre_id = r.centre_id
            WHERE r.status = 'scheduled' AND r.due_on <= ?
            """,
            (today,),
        )
        for r in due:
            purpose = {
                "warranty_ending": "warranty_alerts",
                "rating_request": "follow_up",
                "after_repair": "follow_up",
            }.get(r["reminder_type"], "service_reminders")
            consent = db.raw_query(
                """
                SELECT 1 FROM consent_ledger
                WHERE subject_type = 'household' AND subject_id = ?
                  AND purpose = ? AND withdrawn_at IS NULL
                  AND (scope_centre_id IS NULL OR scope_centre_id = ?)
                LIMIT 1
                """,
                (r["household_id"], purpose, r["centre_id"]),
            )
            if not consent:
                continue
            sent_month = db.raw_query(
                """
                SELECT count(*) AS c FROM reminder
                WHERE household_id = ? AND status IN ('sent','delivered','read','acted')
                  AND sent_at LIKE ?
                """,
                (r["household_id"], f"{month_prefix}%"),
            )[0]["c"]
            if int(sent_month) >= monthly_cap:
                continue
            now_iso = datetime.now(timezone.utc).isoformat()
            db.conn.execute("UPDATE reminder SET status = 'sent', sent_at = ? WHERE id = ?", (now_iso, r["id"]))
            sent.append(r["id"])
    return {"reminders_sent": len(sent), "ids": sent}


@app.post("/scheduler/media-retention")
def enforce_media_retention() -> Dict[str, Any]:
    """Delete expired raw media references past retain_until (48h default unless consented)."""
    today = datetime.now(timezone.utc).date().isoformat()
    with get_rls_session(role="platform") as db:
        cur = db.conn.execute("DELETE FROM diagnosis_media WHERE retain_until < ?", (today,))
        deleted = cur.rowcount
    return {"expired_media_deleted": deleted}
