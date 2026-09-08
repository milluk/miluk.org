#!/usr/bin/env python3
"""Audit DOS-safe .FIN filenames against their first Reference List form.

A source form is safe to use as a public lemma representative only when its
file has one dictionary entry, exactly one Reference List, and the historical
filename is the same form after the old DOS-safe fold.  Everything else stays
an audit finding, rather than becoming an inferred headword.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

REFERENCE = re.compile(r"(?m)^\s*Reference List:\s*(.*)")


def dos_fold(value: str) -> str:
    """The conservative filename fold evidenced by matching 1990 sources."""
    value = value.lower().replace("@", "e").replace("#", "l")
    value = value.replace("%", "g").replace("$", "d").replace("v", "w")
    return re.sub(r"[<:!&;'`^~.,/\\\\-]", "", value)


def first_reference(path: Path) -> tuple[str | None, int]:
    text = path.read_bytes().decode("ascii", errors="ignore")
    matches = REFERENCE.findall(text)
    if len(matches) != 1:
        return None, len(matches)
    fields = re.split(r"[,\s]+", matches[0].strip())
    return (fields[0] if fields and fields[0] else None), 1


def audit(dictionary: dict, fin_dir: Path) -> dict:
    # Delayed to keep this inventory builder usable before the generated
    # inventory is loaded by jacobs_alphabet during a clean rebuild.
    from jacobs_alphabet import initial_key

    by_source = collections.defaultdict(list)
    for entry in dictionary["entries"]:
        by_source[entry.get("source_file", "")].append(entry)

    records, aliases = [], []
    for entry in dictionary["entries"]:
        source = entry.get("source_file", "")
        path = fin_dir / f"{source}.FIN"
        record = {
            "entry_id": entry["entry_id"],
            "source_file": source,
            "headword_ascii": entry.get("headword_ascii", ""),
        }
        if not path.exists():
            record["disposition"] = "not-fin-source"
        elif len(by_source[source]) != 1:
            record["disposition"] = "shared-fin-source"
        else:
            form_ascii, reference_list_count = first_reference(path)
            if reference_list_count != 1 or form_ascii is None:
                record["disposition"] = "not-single-reference-list"
                record["reference_list_count"] = reference_list_count
            elif dos_fold(source) != dos_fold(form_ascii):
                record["disposition"] = "filename-reference-fold-mismatch"
                record["first_reference_ascii"] = form_ascii
            else:
                forms = entry.get("forms", [])
                if not forms or forms[0].get("ascii") != form_ascii:
                    raise ValueError(
                        f"first Reference List form does not match structured data: "
                        f"{entry['entry_id']} {source!r} {form_ascii!r}")
                form_display = forms[0].get("form")
                initial = initial_key(form_ascii)
                record.update({
                    "disposition": "accepted-filename-surrogate",
                    "first_reference_ascii": form_ascii,
                    "first_reference_display": form_display,
                    "initial_key": initial,
                })
                aliases.append(dict(record))
        records.append(record)

    counts = collections.Counter(record["disposition"] for record in records)
    initial_changes = [record for record in aliases if initial_key(
        next(entry for entry in dictionary["entries"]
             if entry["entry_id"] == record["entry_id"])["headword_ascii"],
        entry_id=record["entry_id"], source_file=record["source_file"]
    ) != record["initial_key"]]
    return {
        "schema": "miluk-1990-filename-surrogate-audit/1",
        "rule": ("A public lemma may use the exact first Reference List form only when "
                 "a one-entry .FIN source has exactly one Reference List and its "
                 "DOS-safe filename fold equals that form's fold."),
        "entry_count": len(records),
        "disposition_counts": dict(sorted(counts.items())),
        "accepted_alias_count": len(aliases),
        "initial_repair_count": len(initial_changes),
        "accepted_aliases": aliases,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--fin-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = audit(json.loads(args.dictionary.read_text(encoding="utf-8")), args.fin_dir)
    args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"audited {inventory['entry_count']} entries: "
          f"{inventory['accepted_alias_count']} accepted aliases, "
          f"{inventory['initial_repair_count']} initial repairs")


if __name__ == "__main__":
    main()
