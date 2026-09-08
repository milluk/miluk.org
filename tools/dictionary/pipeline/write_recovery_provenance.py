#!/usr/bin/env python3
"""Write deterministic manifests for archived recovery inputs and Jacobs inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jacobs_alphabet import DOCUMENTARY_EXCEPTIONS, JACOBS_ALPHABET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-dir", type=Path, required=True)
    parser.add_argument("--jacobs-pdf", type=Path, required=True)
    parser.add_argument("--mapping-guide", type=Path, required=True)
    args = parser.parse_args()
    tool = args.tool_dir.resolve()
    abc = tool / "archive" / "1990-abc"
    root_support = tool / "archive" / "1990-root-support"
    final_names = {"DICT#.BYN", "DICT%.BYN", "DICTA.BYN", "DICTB.BYN", "DICTC.BYN"}
    files = []
    for archive, original_prefix in ((abc, "ABC"), (root_support, "")):
        for path in sorted(archive.iterdir(), key=lambda p: p.name.encode()):
            original = f"{original_prefix}/{path.name}" if original_prefix else path.name
            files.append({
                "original_relative_path": original,
                "archive_path": path.relative_to(tool).as_posix(),
                "filename": path.name, "byte_length": path.stat().st_size, "sha256": sha(path),
                "classification": "final-entry source" if original_prefix == "ABC" and path.name in final_names
                                  else "final-entry support file",
            })
    write(tool / "provenance" / "recovered-source-manifest.json", {
        "schema": "miluk-recovered-source-manifest/1", "file_count": len(files), "files": files,
        "root_support_note": "The five root support files are byte-identical to ABC copies and are archived separately to preserve their exact original paths.",
    })
    write(tool / "provenance" / "jacobs-alphabet.json", {
        "schema": "miluk-jacobs-alphabet/1",
        "authority": {"path": str(args.jacobs_pdf.resolve()), "sha256": sha(args.jacobs_pdf),
                      "byte_length": args.jacobs_pdf.stat().st_size,
                      "relevant_pdf_pages_zero_based": list(range(8, 16)),
                      "printed_pages": "11-18"},
        "historical_mapping": {"path": str(args.mapping_guide.resolve()),
                               "sha256": sha(args.mapping_guide),
                               "byte_length": args.mapping_guide.stat().st_size},
        "ordering_rule": "Vowels, then Jacobs's consonant series in the sequence described on printed pages 12-13; longest matching unit wins.",
        "phonetic_unit_count": len(JACOBS_ALPHABET),
        "documentary_exception_count": len(DOCUMENTARY_EXCEPTIONS),
        "phonetic_inventory": JACOBS_ALPHABET,
        "documentary_index_exceptions": DOCUMENTARY_EXCEPTIONS,
    })


if __name__ == "__main__":
    main()
