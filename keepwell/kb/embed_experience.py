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
from typing import Any, Dict, List, Optional

from services.common.config import settings
from services.common.db import RLSSession, get_rls_session


EMBED_DIM = 768


def compute_embedding(text: str, use_live_api: bool = False) -> List[float]:
    """Return a 768-d unit vector via gemini-embedding-2 or deterministic bag-of-trigrams fallback."""
    if use_live_api and settings.gemini_api_key:
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=settings.gemini_api_key)
            resp = client.models.embed_content(
                model=settings.gemini_model_embed,
                contents=text,
                config={"output_dimensionality": EMBED_DIM},
            )
            return list(resp.embeddings[0].values)
        except Exception:
            pass

    # Deterministic 768-d hashed token/trigram projection for offline parity
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

    rows = db.raw_query(
        f"SELECT id, symptom_text, error_code, root_cause, parts, duration_min, embedding FROM experience_case WHERE {' AND '.join(clauses)}",
        params,
    )
    q_vec = compute_embedding(symptom_text, use_live_api=False)
    scored: List[tuple[float, Dict[str, Any]]] = []
    for r in rows:
        emb = json.loads(r["embedding"]) if r.get("embedding") else compute_embedding(
            f"{r.get('symptom_text', '')} {r.get('error_code', '')} {r.get('root_cause', '')}",
            use_live_api=False,
        )
        sim = cosine_similarity(q_vec, emb)
        scored.append((sim, {
            "id": r["id"],
            "symptom_text": r["symptom_text"],
            "error_code": r["error_code"],
            "root_cause": r["root_cause"],
            "parts": json.loads(r["parts"]) if isinstance(r["parts"], str) else (r["parts"] or []),
            "duration_min": int(r["duration_min"]) if r.get("duration_min") else 60,
            "similarity": round(sim, 4),
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]
