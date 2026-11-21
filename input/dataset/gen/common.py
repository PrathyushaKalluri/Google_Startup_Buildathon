"""Shared helpers: deterministic ids, table registry, CSV writer, fake phone/crypto."""
import csv, hashlib, hmac, json, os, random, uuid, datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo

SEED = 20261120
IST = ZoneInfo("Asia/Kolkata")
NS = uuid.UUID("6b1f0c3e-52a4-4c0e-9d57-0a7c1f2b9e11")
SIM_NOW = dt.datetime(2026, 11, 21, 8, 0, tzinfo=IST)      # the moment the prototype "wakes up"
HISTORY_START = dt.date(2025, 9, 1)                         # Keepwell pilot start

rng = random.Random(SEED)

def uid(ns, key):
    """Deterministic uuid so every run produces identical keys."""
    return str(uuid.uuid5(NS, f"{ns}:{key}"))

# ---- table registry -------------------------------------------------------
TABLES = defaultdict(list)

def add(table, **row):
    TABLES[table].append(row)
    return row

# ---- value formatting for COPY ... CSV -------------------------------------
def fmt(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "t" if v else "f"
    if isinstance(v, (dict, list)) and not isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (dt.datetime,)):
        return v.isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, bytes):
        return "\\x" + v.hex()
    return v

def pgarray(items):
    if not items:
        return "{}"
    return "{" + ",".join('"' + str(i).replace('"', '\\"') + '"' for i in items) + "}"

def write_csvs(outdir, order):
    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for t in order:
        rows = TABLES.get(t, [])
        if not rows:
            continue
        cols = list(rows[0].keys())
        bad = [i for i, r in enumerate(rows) if list(r.keys()) != cols and set(r.keys()) != set(cols)]
        if bad:
            raise SystemExit(f'{t}: {len(bad)} rows have a different column set than row 0; first: {sorted(set(rows[bad[0]].keys()) ^ set(cols))}')
        with open(os.path.join(outdir, f"{t}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([('\\N' if fmt(r.get(c)) is None else fmt(r.get(c))) for c in cols])
        manifest.append((t, cols, len(rows)))
    return manifest

def geo(lon, lat):
    return f"SRID=4326;POINT({lon:.6f} {lat:.6f})"

# ---- fake but well-formed phone numbers (unallocated 5xxxx range) ----------
DEV_HASH_KEY = b"keepwell-dev-hash-key"       # dev only
def fake_phone():
    return "+91 5" + "".join(str(rng.randint(0, 9)) for _ in range(4)) + " " + "".join(str(rng.randint(0, 9)) for _ in range(5))

_seen_phones = set()
def unique_phone():
    while True:
        p = fake_phone()
        if p not in _seen_phones:
            _seen_phones.add(p)
            return p

def phone_hash(p):
    return hmac.new(DEV_HASH_KEY, p.replace(" ", "").encode(), hashlib.sha256).digest()

# Dev-only "encryption": real deployments use Cloud KMS. Fernet keeps the shape (opaque bytes).
from cryptography.fernet import Fernet
import base64
DEV_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(b"keepwell-dev-encryption-key").digest())
_f = Fernet(DEV_FERNET_KEY)
def phone_enc(p):
    # dev only: fixed time and an IV derived from the plaintext, so the dataset is reproducible byte for byte
    iv = hashlib.sha256(b"iv:" + p.encode()).digest()[:16]
    return _f._encrypt_from_parts(p.encode(), 1790000000, iv)

def weighted(items, weights):
    return rng.choices(items, weights=weights, k=1)[0]

def ist(y, m, d, hh=0, mm=0):
    return dt.datetime(y, m, d, hh, mm, tzinfo=IST)
