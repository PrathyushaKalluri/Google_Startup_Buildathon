---
name: service-evidence
description: Evidence standards for appliance identification, Home Memory provenance, warranty verification, and preventing unverified identities from driving part selection.
---

# Service Evidence & Identity Standards

## Evidence Levels
Every appliance identification is classified into one of three additive `appliance.evidence_level` values alongside the schema's `identity_status` (`provisional | verified | merged`):

| `evidence_level` | Criteria | Allowed `identity_status` | Can drive part selection? |
|---|---|---|---|
| `confirmed` | Rating sticker, model plate, or invoice read via Gemini vision/OCR above confidence threshold AND matched to `appliance_model` (+ `serial_norm` for `verified`). | `verified` (if `serial_norm` present) or `provisional` | Yes |
| `probable` | Partial sticker read, `external_ref` alias, or household statement matching exactly one catalogue model. | `provisional` | Only with household confirmation |
| `unverified` | Brand/category guess or ambiguous model; low OCR confidence. | `provisional` | **No** — request sticker/invoice photo or hold part reservation |

## Rules
1. **Confidence threshold:** Vision extractions (sticker, invoice, error display, carton) below threshold are never silently accepted; prompt the household to confirm or retake (`ui_hint: show_sticker` on Live calls).
2. **Global serial conflict:** `brand_id + serial_norm` is globally unique. If a serial matches another household's appliance, flag a conflict for resolution—never auto-merge across households.
3. **Cross-centre history:** Read other centres' technical events only via `read_shared_history()`, which enforces `share_technical_history` consent and appends an immutable `access_log` row (`cross_centre = true`). Prices and private centre notes never cross.
4. **Zero fabricated citations:** Every diagnostic hypothesis cites a real `kb_document` title + page/snippet returned by `search_manuals`.
