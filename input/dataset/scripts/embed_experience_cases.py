"""Fills kw.experience_case.embedding (vector(768)) using the Gemini embeddings API.
UNTESTED against the live API (no key was available when this dataset was built). Needs: pip install google-genai "psycopg[binary]" ; env GEMINI_API_KEY, DATABASE_URL.
Text embedded = what a technician would search by: brand, series, error code, symptom, confirmed root cause (never prices or households)."""
import os, time
import psycopg
from google import genai
from google.genai import types

MODEL = "gemini-embedding-2"     # per the Gemini API docs at build time; gemini-embedding-001 also works for text (then pass task_type=RETRIEVAL_DOCUMENT in the config)
DIM = 768
BATCH = 50

client = genai.Client()
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute("SET search_path = kw, public")
    rows = conn.execute("""
        SELECT e.id, b.name, e.category_code, coalesce(e.model_series,''), coalesce(e.error_code,''), e.symptom_text, coalesce(e.root_cause,'')
        FROM experience_case e JOIN brand b ON b.id = e.brand_id WHERE e.embedding IS NULL""").fetchall()
    print(len(rows), "cases to embed")
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        texts = [f"task: search result | document: {b} {cat} {series}. Error code: {code or 'none'}. Symptom: {sym}. Confirmed cause: {cause}" for _, b, cat, series, code, sym, cause in chunk]
        res = client.models.embed_content(model=MODEL, contents=texts, config=types.EmbedContentConfig(output_dimensionality=DIM))
        for (cid, *_), emb in zip(chunk, res.embeddings):
            vec = "[" + ",".join(f"{x:.6f}" for x in emb.values) + "]"
            conn.execute("UPDATE experience_case SET embedding = %s::vector WHERE id = %s", (vec, cid))
        conn.commit()
        time.sleep(1)
    print("done")
