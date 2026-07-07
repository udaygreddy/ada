"""
Shared helpers for ADA scripts. Standard library only (no third-party deps),
so the bundle is fully client-reviewable and auditable.
"""
import datetime
import hashlib
import json
import os

GENESIS_PREV = "sha256:" + ("0" * 64)


# ---------- hashing / encoding ----------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_str(s):
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical(obj):
    """Deterministic JSON for hashing — sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------- jsonl io ----------

def read_jsonl(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def append_jsonl(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------- taxonomy (minimal YAML subset loader) ----------
# Supports exactly the flat scalar-only schema ADA uses:
#   items:
#     - id: 1.msa
#       label: "Master Service Agreement"
#       ...

def _kv(s):
    k, _, v = s.partition(":")
    k = k.strip()
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return k, v


def load_taxonomy(path):
    items = []
    cur = None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "items:":
                continue
            if stripped.startswith("- "):
                if cur is not None:
                    items.append(cur)
                cur = {}
                k, v = _kv(stripped[2:])
                cur[k] = v
            elif cur is not None:
                k, v = _kv(stripped)
                cur[k] = v
    if cur is not None:
        items.append(cur)
    return items
