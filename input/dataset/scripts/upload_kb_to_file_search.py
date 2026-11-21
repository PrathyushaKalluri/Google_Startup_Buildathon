"""Uploads the PDFs in ../kb to one Gemini File Search store and records the store and document names in kw.kb_document.
UNTESTED against the live API (no key was available when this dataset was built). Needs: pip install google-genai "psycopg[binary]" ; env GEMINI_API_KEY, DATABASE_URL."""
import os, time, glob
import psycopg
from google import genai

client = genai.Client()
store = client.file_search_stores.create(config={"display_name": "keepwell-kb-sim"})
print("store:", store.name)
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute("SET search_path = kw, public")
    here = os.path.dirname(os.path.abspath(__file__))
    for path in sorted(glob.glob(os.path.join(here, "..", "kb", "*.pdf"))):
        key = os.path.splitext(os.path.basename(path))[0]
        title, = conn.execute("SELECT title FROM kb_document WHERE storage_uri LIKE %s", (f"%/{key}.pdf",)).fetchone()
        op = client.file_search_stores.upload_to_file_search_store(file=path, file_search_store_name=store.name, config={"display_name": title})
        while not op.done:
            time.sleep(5)
            op = client.operations.get(op)
        conn.execute("UPDATE kb_document SET file_search_store = %s, file_search_doc = %s WHERE storage_uri LIKE %s", (store.name, title, f"%/{key}.pdf"))
        print("uploaded", key)
    conn.commit()
