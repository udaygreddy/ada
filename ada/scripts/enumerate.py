#!/usr/bin/env python3
"""
enumerate.py — list + hash candidate documents from a source folder.

Deterministic discovery step (PLAYBOOK §3, §5 Phase A). Walks a drop folder
(e.g. a Paychex export folder, or materialized QuickBooks pulls), hashes each
file, and emits one JSON candidate per line. It does NOT classify — classification
is the agent's judgment; this script only produces the verifiable candidate set.

Usage:
  enumerate.py SCAN_DIR --connector NAME [--out FILE]

Output candidate:
  { connector, source, source_ref, filename, ext, size, mime, content_hash,
    sensitivity: "unknown" }
"""
import argparse
import mimetypes
import os
import sys

import _ada

# Junk we never treat as candidates.
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_DIRS = {".git", "__pycache__", ".ada"}


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name in SKIP_NAMES or name.startswith("."):
                continue
            yield os.path.join(dirpath, name)


def main():
    p = argparse.ArgumentParser(description="Enumerate + hash candidate documents")
    p.add_argument("scan_dir")
    p.add_argument("--connector", required=True,
                   help="e.g. paychex-export | intuit | local")
    p.add_argument("--out", default="", help="output jsonl (default: stdout)")
    a = p.parse_args()

    if not os.path.isdir(a.scan_dir):
        sys.exit(f"not a directory: {a.scan_dir}")

    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    n = 0
    for path in sorted(iter_files(a.scan_dir)):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        cand = {
            "connector": a.connector,
            "source": a.connector,
            "source_ref": os.path.abspath(path),
            "filename": os.path.basename(path),
            "ext": ext,
            "size": os.path.getsize(path),
            "mime": mimetypes.guess_type(path)[0] or "application/octet-stream",
            "content_hash": _ada.sha256_file(path),
            "sensitivity": "unknown",
        }
        out.write(_ada.canonical(cand) + "\n")
        n += 1
    if a.out:
        out.close()
    sys.stderr.write(f"enumerated {n} candidate(s) from {a.scan_dir}\n")


if __name__ == "__main__":
    main()
