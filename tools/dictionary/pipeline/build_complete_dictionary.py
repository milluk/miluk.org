#!/usr/bin/env python3
"""Rebuild dictionary.json from the frozen D-Z checkpoint plus recovered A-C tables."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from anderson import convert  # noqa: E402
from jacobs_alphabet import initial_key  # noqa: E402
from parse_byn import parse_byn  # noqa: E402


def slug(value):
    value = value.lower().replace("#", "l").replace("%", "gamma").replace("@", "e")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:48] or "entry"


def verify_superset_duplicate(records):
    by_id = {record["source_record"]: record for record in records}
    earlier = by_id["DICT#.BYN:27"]
    retained = by_id["DICT#.BYN:28"]
    same_fields = ("headword_ascii", "gloss", "citation_summary", "declared_reference_count")
    if not all(earlier[field] == retained[field] for field in same_fields):
        raise ValueError("DICT#.BYN:27/28 no longer share duplicate identity fields")
    earlier_alts, retained_alts = set(earlier["alternate_forms_ascii"]), set(retained["alternate_forms_ascii"])
    earlier_ext, retained_ext = set(earlier["extensions"]), set(retained["extensions"])
    earlier_notes, retained_notes = set(earlier["notes"]), set(retained["notes"])
    if not (earlier_alts <= retained_alts and earlier_ext <= retained_ext and
            earlier_notes <= retained_notes):
        raise ValueError("DICT#.BYN:28 is not a documentary superset of row 27")
    additions = {
        "alternate_forms_ascii": sorted(retained_alts - earlier_alts),
        "extensions": sorted(retained_ext - earlier_ext),
        "notes": sorted(retained_notes - earlier_notes),
    }
    if not any(additions.values()):
        raise ValueError("DICT#.BYN:28 is not a strict documentary superset of row 27")
    return {
        "excluded_source_record": earlier["source_record"],
        "retained_source_record": retained["source_record"],
        "relationship": "strict-documentary-superset",
        "identity_fields": list(same_fields),
        "retained_additions": additions,
    }


def build(checkpoint: Path, sources: Path):
    base = json.loads(checkpoint.read_text(encoding="utf-8"))
    entries = list(base["entries"])
    original_ids = [entry["entry_id"] for entry in entries]
    source_documents, source_records = [], []
    next_number = max(int(entry_id[1:5]) for entry_id in original_ids) + 1
    duplicate_relationship = None
    for name in ("DICT#.BYN", "DICT%.BYN", "DICTA.BYN", "DICTB.BYN", "DICTC.BYN"):
        document = parse_byn(sources / name)
        if name == "DICT#.BYN":
            duplicate_relationship = verify_superset_duplicate(document["records"])
        source_documents.append({key: document[key] for key in
                                 ("path", "sha256", "byte_length", "record_count", "conversion_rule")})
        for record in document["records"]:
            # DICT#.BYN rows 27/28 repeat the same entry. Row 28 is a strict
            # documentary superset (same headword/gloss/citation/forms, plus
            # extension -t and form #dje`). Preserve row 27 in the receipt but
            # do not duplicate the final dictionary entry.
            if record["source_record"] == "DICT#.BYN:27":
                source_records.append({
                    "source_record": record["source_record"], "entry_id": None,
                    "headword_ascii": record["headword_ascii"],
                    "line_start": record["line_start"], "line_end": record["line_end"],
                    "disposition": "excluded-superseded-duplicate",
                    "duplicate_of": "DICT#.BYN:28",
                    "rule": "exclude only when the adjacent later row has identical headword, gloss, citation and a strict superset of documentary content",
                })
                continue
            ascii_forms = [record["headword_ascii"], *record["alternate_forms_ascii"]]
            forms = []
            for ascii_form in dict.fromkeys(ascii_forms):
                display = convert(ascii_form)
                forms.append({"ascii": ascii_form, "form": display,
                              "search": display, "evidence": "unverified"})
            eid = f"e{next_number:04d}-{slug(record['headword_ascii'])}"
            next_number += 1
            entry = {
                "entry_id": eid,
                "headword": convert(record["headword_ascii"]),
                "headword_ascii": record["headword_ascii"],
                "gloss": record["gloss"],
                "source_file": name,
                "source_record": record["source_record"],
                "source_records": ([record["source_record"], "DICT#.BYN:27"]
                                   if record["source_record"] == "DICT#.BYN:28"
                                   else [record["source_record"]]),
                "source_sha256": document["sha256"],
                "source_lines": {"start": record["line_start"], "end": record["line_end"]},
                "conversion_rule": document["conversion_rule"],
                "declared_reference_count": record["declared_reference_count"],
                "citation_summary": record["citation_summary"],
                "extensions": record["extensions"],
                "record_notes": record["notes"],
                "raw_source_lines": record["raw_lines"],
                "forms": forms,
                "cross_references": [], "examples": [], "attestations": [],
            }
            initial_key(entry["headword_ascii"])
            entries.append(entry)
            source_records.append({"source_record": record["source_record"], "entry_id": eid,
                                   "headword_ascii": record["headword_ascii"],
                                   "line_start": record["line_start"], "line_end": record["line_end"],
                                   "disposition": "admitted",
                                   **({"supersedes": "DICT#.BYN:27"}
                                      if record["source_record"] == "DICT#.BYN:28" else {})})
    assert [entry["entry_id"] for entry in entries[:len(original_ids)]] == original_ids
    return {
        "schema": base["schema"], "entry_count": len(entries), "entries": entries,
        "recovery": {
            "baseline_entry_count": len(original_ids),
            "recovered_source_record_count": len(source_records),
            "recovered_entry_count": sum(item['entry_id'] is not None for item in source_records),
            "documented_exclusion_count": sum(item['entry_id'] is None for item in source_records),
            "identifier_policy": "Existing e0001-e1111 identifiers preserved byte-for-byte; recovered records append e1112 onward in source/record order.",
            "duplicate_relationships": [duplicate_relationship],
            "source_documents": source_documents,
        },
    }, source_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records-output", type=Path)
    args = parser.parse_args()
    dictionary, records = build(args.checkpoint, args.sources)
    args.output.write_text(json.dumps(dictionary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if args.records_output:
        receipt = {"schema": "miluk-1990-recovered-records/1", "record_count": len(records),
                   "records": records}
        args.records_output.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(dictionary['entries'])} entries; preserved 1111 IDs; admitted {sum(r['entry_id'] is not None for r in records)} of {len(records)} recovered records")


if __name__ == "__main__":
    main()
