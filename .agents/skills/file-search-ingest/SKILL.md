---
name: file-search-ingest
description: Ingesting the 21 KB PDFs into Gemini File Search stores, archiving originals in GCS, and generating 768-dim pgvector embeddings for experience cases and fault retrieval.
---

# File Search & Embedding Ingestion (`kb/`)

## Storage & Store Layout
1. **Originals in GCS:** Gemini File Search deletes raw uploaded files after 48 hours. Always archive source PDFs in `gs://${GCS_BUCKET_KB}/` first and record `storage_uri` in `kb_document`.
2. **Store topology (`FILE_SEARCH_STORE_PREFIX=keepwell-kb`):**
   - Global store (`keepwell-kb-global`): OEM manuals, error-code tables, safe-fix manuals, warranty terms (the 21 dataset PDFs in `input/dataset/kb/`).
   - Per-centre store (`keepwell-kb-<centre_key>`): private centre bulletins and notes (never leaked across centres).
3. **Citations:** Every `search_manuals` response must return `{doc_title, page, uri, snippet}` grounded in File Search grounding metadata. Never fabricate a page number or document title.
4. **Live API constraint:** File Search cannot be attached directly to a Gemini Live session. The Live agent invokes the `search_manuals` tool, which calls the standard Gemini API against the File Search store.

## pgvector Embeddings (`gemini-embedding-2`, 768d)
- Embed `experience_case` symptom text, fault descriptions, and part aliases using `GEMINI_MODEL_EMBED` (`gemini-embedding-2`, output dimensionality `768`).
- Store in Postgres `vector(768)` columns indexed with HNSW (`vector_cosine_ops`).
- Always filter by `brand_id` and `category_code` before cosine similarity ranking (see Q19 in `keepwell_example_queries.sql`).
- Ingestion scripts must be idempotent (skip unchanged files by content hash / `file_search_doc` ref).
