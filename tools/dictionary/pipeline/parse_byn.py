#!/usr/bin/env python3
"""Parse the five consolidated A-C 1990 BYN final-entry tables without loss."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


ENTRY = re.compile(r"^\s*(\d+)\s+(\S+)\s{2,}([^\t]*?)(?:\t+(.*))?$")


def parse_byn(path: Path):
    raw = path.read_bytes()
    # These DOS-era files are 7-bit text with CRLF and an occasional EOF byte.
    text = raw.decode("ascii").replace("\x1a", "")
    lines = text.splitlines()
    starts = []
    for number, line in enumerate(lines, 1):
        match = ENTRY.match(line)
        if match:
            starts.append((number, match))
    records = []
    for position, (start, match) in enumerate(starts, 1):
        end = starts[position][0] - 1 if position < len(starts) else len(lines)
        block = lines[start - 1:end]
        citations = (match.group(4) or "").strip()
        extensions, alternates, notes = [], [], []
        mode = None
        for line in block[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if "E~:" in line:
                mode = "extension"
                value = line.split("E~:", 1)[1].strip()
                if value:
                    extensions.append(value)
                continue
            if "A~:" in line:
                mode = "alternate"
                value = line.split("A~:", 1)[1].strip().split("\t", 1)[0].strip()
                if value:
                    alternates.append(value)
                continue
            fields = [part.strip() for part in line.split("\t") if part.strip()]
            if mode == "alternate" and fields and not fields[0].startswith("("):
                candidate = fields[0]
                if " " not in candidate:
                    alternates.append(candidate)
                    continue
            if mode == "extension" and fields and not re.search(r"\b[bUO]\d+s\d+p\d+", fields[0]):
                extensions.append(fields[0])
                continue
            notes.append(stripped)
        records.append({
            "source_record": f"{path.name}:{position}",
            "record_number": position,
            "line_start": start,
            "line_end": end,
            "declared_reference_count": int(match.group(1)),
            "headword_ascii": match.group(2),
            "gloss": match.group(3).strip(),
            "citation_summary": citations,
            "extensions": extensions,
            "alternate_forms_ascii": list(dict.fromkeys(alternates)),
            "notes": notes,
            "raw_lines": block,
        })
    return {
        "path": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw),
        "record_count": len(records),
        "conversion_rule": "ASCII CRLF table; numbered row starts record; E~ and A~ continuations retained; DOS EOF ignored only for decoding",
        "records": records,
    }
