#!/usr/bin/env python3
"""
Keepwell Experience Case Embeddings (kb/embed_experience.py).
Computes 768-dimensional embeddings using gemini-embedding-2 (or deterministic
hashing fallback offline) for the 674 experience_case rows and supports
brand+category filtered cosine-similarity retrieval (Q19).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from services.common.config import settings
from services.common.db import RLSSession, get_rls_session


EMBED_DIM = 768


def _offline_hash_embedding(text: str) -> List[float]:
    vec = [0.0] * EMBED_DIM
    tokens = [t.strip(".,?!:;()[]") for t in text.lower().split() if t.strip()]
    for tok in tokens:
        h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % EMBED_DIM] += 1.0
        for i in range(max(0, len(tok) - 2)):
            tri = tok[i : i + 3]
            ht = int(hashlib.md5(tri.encode("utf-8")).hexdigest()[:8], 16)
            vec[ht % EMBED_DIM] += 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 5) for v in vec]


def compute_embeddings_batch(
    texts: List[str],
    use_live_api: Optional[bool] = None,
) -> Tuple[List[List[float]], str]:
    """Batch-embed texts using gemini-embedding-2 (768-d) or deterministic offline fallback."""
    live = (os.getenv("LIVE_GOOGLE") == "1") if use_live_api is None else use_live_api
    if live and settings.gemini_api_key and texts:
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=settings.gemini_api_key)
            resp = client.models.embed_content(
                model=settings.gemini_model_embed,
                contents=texts,
                config={"output_dimensionality": EMBED_DIM},
            )
            return [list(e.values) for e in resp.embeddings], "real_gemini_embedding_2"
        except Exception:
            pass
    return [_offline_hash_embedding(t) for t in texts], "offline_hash_fallback"


def compute_embedding(text: str, use_live_api: Optional[bool] = None) -> List[float]:
    """Return a 768-d unit vector via gemini-embedding-2 or deterministic bag-of-trigrams fallback."""
    vecs, _ = compute_embeddings_batch([text], use_live_api=use_live_api)
    return vecs[0]


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def populate_pgvector_embeddings(
    use_live_api: bool = True,
    batch_size: int = 50,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Embed experience_case rows with gemini-embedding-2 and store in Postgres pgvector."""
    updated = 0
    backends: set[str] = set()
    with get_rls_session(role="platform") as db:
        q = "SELECT id, symptom_text, error_code, root_cause FROM experience_case ORDER BY id"
        if limit:
            q += f" LIMIT {int(limit)}"
        rows = db.raw_query(q)
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            texts = [
                f"{r.get('symptom_text') or ''} {r.get('error_code') or ''} {r.get('root_cause') or ''}".strip()
                or "appliance fault"
                for r in chunk
            ]
            vecs, backend = compute_embeddings_batch(texts, use_live_api=use_live_api)
            backends.add(backend)
            for r, vec in zip(chunk, vecs):
                db.execute(
                    "UPDATE experience_case SET embedding = %s::vector WHERE id = %s",
                    (_vec_literal(vec), r["id"]),
                )
                updated += 1
    return {
        "rows_embedded": updated,
        "dim": EMBED_DIM,
        "model": settings.gemini_model_embed,
        "backend": ",".join(sorted(backends)) if backends else "none",
    }


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def find_similar_experience_cases(
    db: RLSSession,
    symptom_text: str,
    brand_id: Optional[str] = None,
    category_code: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Mirrors Q19: filter by brand_id and category_code, rank by cosine similarity."""
    clauses = ["verified_by_technician = TRUE"]
    params: List[Any] = []
    if brand_id:
        clauses.append("brand_id = %s")
        params.append(brand_id)
    if category_code:
        clauses.append("category_code = %s")
        params.append(category_code)

    # Use native PostgreSQL pgvector cosine distance (<=>) when embeddings are populated
    q_vec, q_backend = compute_embeddings_batch([symptom_text])
    q_lit = _vec_literal(q_vec[0])
    pg_rows = db.raw_query(
        f"""
        SELECT id, symptom_text, error_code, root_cause, parts, duration_min,
               (1 - (embedding <=> %s::vector)) AS similarity
        FROM experience_case
        WHERE {' AND '.join(clauses)} AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        [q_lit, *params, q_lit, top_k],
    )
    if pg_rows:
        return [
            {
                "id": r["id"],
                "symptom_text": r["symptom_text"],
                "error_code": r["error_code"],
                "root_cause": r["root_cause"],
                "parts": json.loads(r["parts"]) if isinstance(r["parts"], str) else (r["parts"] or []),
                "duration_min": int(r["duration_min"]) if r.get("duration_min") else 60,
                "similarity": round(float(r["similarity"]), 4),
                "backend": f"pgvector+{q_backend}",
            }
            for r in pg_rows
        ]

    rows = db.raw_query(
        f"SELECT id, symptom_text, error_code, root_cause, parts, duration_min, embedding FROM experience_case WHERE {' AND '.join(clauses)}",
        params,
    )
    scored: List[tuple[float, Dict[str, Any]]] = []
    for r in rows:
        emb = json.loads(r["embedding"]) if r.get("embedding") else compute_embedding(
            f"{r.get('symptom_text', '')} {r.get('error_code', '')} {r.get('root_cause', '')}",
            use_live_api=False,
        )
        sim = cosine_similarity(q_vec[0], emb)
        scored.append((sim, {
            "id": r["id"],
            "symptom_text": r["symptom_text"],
            "error_code": r["error_code"],
            "root_cause": r["root_cause"],
            "parts": json.loads(r["parts"]) if isinstance(r["parts"], str) else (r["parts"] or []),
            "duration_min": int(r["duration_min"]) if r.get("duration_min") else 60,
            "similarity": round(sim, 4),
            "backend": "python_cosine_fallback",
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]
