#!/usr/bin/env python3
"""Create an exhaustive byte-level inventory of the authoritative MILUK directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from convert_fin import document_body, strip_wordperfect_codes
from parse_byn import parse_byn

BYN_NAMES = {"DICT#.BYN", "DICT%.BYN", "DICTA.BYN", "DICTB.BYN", "DICTC.BYN"}


def decoded(raw):
    try:
        return strip_wordperfect_codes(document_body(raw))
    except Exception:
        return raw.decode("ascii", errors="replace").replace("\x1a", "")


def container(raw, suffix):
    if raw.startswith(b"\xffWPC"):
        return "WordPerfect 5.x document"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WAVE":
        return "RIFF WAVE audio"
    if raw.startswith(b"\xd0\xcf\x11\xe0"):
        return "OLE compound document"
    if raw.startswith(b"PK\x03\x04"):
        return "ZIP container"
    if suffix.lower() in {".ttf", ".fon", ".pfb"}:
        return "font binary"
    printable = sum(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in raw)
    if not raw or printable / len(raw) > .94:
        return "7-bit text"
    return "binary"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--archive-fin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    paths = sorted((path for path in root.rglob("*") if path.is_file()),
                   key=lambda path: path.relative_to(root).as_posix().encode())
    hashes = defaultdict(list)
    preliminary = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        hashes[sha].append(rel)
        text = decoded(raw)
        refs = len(re.findall(r"(?im)^\s*Reference List\s*:", text))
        if path.name in BYN_NAMES:
            try:
                apparent = parse_byn(path)["record_count"]
                structure = "1990 consolidated final-entry table (numbered rows with E~/A~ continuations)"
            except Exception:
                apparent = 0
                structure = "malformed BYN-named table"
        elif refs:
            apparent = refs
            structure = "WordCruncher reference-list record" if refs == 1 else "WordCruncher reference-list aggregate"
        elif raw.startswith(b"\xffWPC"):
            apparent, structure = 0, "WordPerfect support document"
        else:
            apparent, structure = 0, "support asset or non-entry data"
        preliminary.append({
            "relative_path": rel, "filename": path.name, "byte_length": len(raw),
            "sha256": sha, "detected_container": container(raw, path.suffix),
            "structural_format": structure, "apparent_entry_count": apparent,
        })

    # Canonical final sources: one root D-Z FIN copy and the ABC table copy.
    canonical = {}
    for item in preliminary:
        rel = item["relative_path"]
        if "/" not in rel and rel.endswith(".FIN"):
            canonical[item["sha256"]] = rel
        elif rel.startswith("ABC/") and item["filename"] in BYN_NAMES:
            canonical[item["sha256"]] = rel

    abc_support_hashes = {item["sha256"] for item in preliminary
                          if item["relative_path"].startswith("ABC/")
                          and "." not in item["filename"] and item["filename"] not in {".", ".."}}
    for item in preliminary:
        rel, sha = item["relative_path"], item["sha256"]
        if canonical.get(sha) == rel:
            if rel.endswith(".FIN"):
                item.update(classification="final-entry source", pipeline_disposition="admitted-existing")
            else:
                item.update(classification="final-entry source", pipeline_disposition="admitted-recovered")
        elif sha in canonical:
            item.update(classification="duplicate", pipeline_disposition="duplicate-not-read",
                        duplicate_of=canonical[sha])
        elif sha in abc_support_hashes:
            item.update(classification="final-entry support file", pipeline_disposition="archived-support-not-record-source")
        elif "Reference List:" in decoded((root / rel).read_bytes()):
            item.update(classification="support file", pipeline_disposition="support-not-record-source")
        else:
            item.update(classification="support file", pipeline_disposition="support-not-record-source")

    archived_fin = sorted(args.archive_fin.glob("*.FIN"), key=lambda p: p.name.encode())
    archive_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archived_fin}
    root_fin = {item["filename"]: item["sha256"] for item in preliminary
                if "/" not in item["relative_path"] and item["filename"].endswith(".FIN")}
    admitted = [item for item in preliminary if item["pipeline_disposition"].startswith("admitted-")]
    result = {
        "schema": "miluk-authoritative-directory-inventory/1",
        "source_root": str(root),
        "inventory_order": "relative path as UTF-8 bytes",
        "totals": {
            "regular_files": len(preliminary), "byte_length": sum(item["byte_length"] for item in preliminary),
            "unique_sha256": len(hashes), "duplicate_paths": sum(len(v) - 1 for v in hashes.values()),
            "root_level_files": sum("/" not in item["relative_path"] for item in preliminary),
            "extensionless_files": sum(Path(item["filename"]).suffix == "" for item in preliminary),
            "fin_paths_case_insensitive": sum(Path(item["filename"]).suffix.lower() == ".fin" for item in preliminary),
            "admitted_final_sources": len(admitted),
            "admitted_existing_fin_sources": sum(item["pipeline_disposition"] == "admitted-existing" for item in preliminary),
            "admitted_recovered_sources": sum(item["pipeline_disposition"] == "admitted-recovered" for item in preliminary),
            "recovered_records": sum(item["apparent_entry_count"] for item in preliminary
                                     if item["pipeline_disposition"] == "admitted-recovered"),
        },
        "comparison": {
            "old_fin_manifest_count": 684,
            "old_archived_input_count": len(archived_fin),
            "old_archive_matches_authoritative_root_fin": archive_hashes == root_fin,
            "old_converter_rule": "Path.glob('*.FIN') at directory root; expected exactly 684",
            "old_parser_shape": "one converted text container per FIN; no BYN table parser",
            "omitted_admitted_sources": [item["relative_path"] for item in admitted
                                         if item["pipeline_disposition"] == "admitted-recovered"],
        },
        "disposition_counts": dict(sorted(Counter(item["pipeline_disposition"] for item in preliminary).items())),
        "files": preliminary,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
