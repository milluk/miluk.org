#!/usr/bin/env python3
"""Jacobs-aware Miluk initial units and documentary index exceptions."""
from __future__ import annotations

import re
import unicodedata


def unit(key, display, aliases=(), series=""):
    return {"key": key, "display": display.lower(), "search_aliases": list(aliases),
            "series": series, "status": "Jacobs phonetic unit"}


# Order follows Jacobs's vowel list and then the consonant series in his prose.
# Keys are Troy Anderson's historical 1990 ASCII notation.
JACOBS_ALPHABET = [
    unit("@", "Ə", ("schwa",), "vowel"),
    unit("a", "A", (), "vowel"), unit("e", "Ɛ", ("e",), "vowel"),
    unit("i", "I", (), "vowel"), unit("u", "U", (), "vowel"),
    unit("b", "B", (), "bilabial"), unit("p", "P", (), "bilabial"),
    unit("p!", "P'", ("p'",), "bilabial"),
    unit("w", "W", (), "bilabial"), unit("w:", "W'", ("w'",), "bilabial"),
    unit("m", "M", (), "bilabial"), unit("m:", "M'", ("m'",), "bilabial"),
    unit("d", "D", (), "alveolar"), unit("t", "T", (), "alveolar"),
    unit("t!", "T'", ("t'",), "alveolar"), unit("dz", "DZ", (), "alveolar"),
    unit("ts", "TS", (), "alveolar"), unit("t's", "T'S", ("ts'",), "alveolar"),
    unit("s", "S", (), "alveolar"), unit("s:", "S'", ("s'",), "alveolar"),
    unit("n", "N", (), "alveolar"), unit("n:", "N'", ("n'",), "alveolar"),
    unit("dj", "DJ", ("j",), "c-series"),
    unit("tc", "TC", ("ch", "č"), "c-series"),
    unit("t'c", "T'C", ("ch'", "č'", "tc'"), "c-series"),
    unit("c", "C", ("sh", "š", "ʃ"), "c-series"),
    unit("c:", "C'", ("sh'", "š'", "ʃ'"), "c-series"),
    unit("g&", "G̯", ("gy",), "anterior palatal"),
    unit("k&", "K̯", ("ky",), "anterior palatal"),
    unit("k!&", "K̯'", ("ky'",), "anterior palatal"),
    unit("x&", "X̯", ("xy",), "anterior palatal"),
    unit("x:&", "X̯'", ("xy'",), "anterior palatal"),
    unit("y", "Y", ("ɣy",), "anterior palatal"),
    unit("y:", "Y'", ("y'", "ɣy'"), "anterior palatal"),
    unit("g", "G", (), "medial palatal"), unit("gw", "GW", (), "medial palatal"),
    unit("k", "K", (), "medial palatal"), unit("kw", "KW", (), "medial palatal"),
    unit("k!", "K'", ("k'",), "medial palatal"),
    unit("k!w", "K'W", ("kw'", "k'w"), "medial palatal"),
    unit("%", "Ɣ", ("gamma", "ɣ"), "medial palatal"),
    unit("%:", "Ɣ'", ("ɣ'",), "medial palatal"),
    unit("%w", "ƔW", ("ɣw",), "medial palatal"),
    unit("x", "X", (), "medial palatal"), unit("x:", "X'", ("x'",), "medial palatal"),
    unit("xw", "XW", (), "medial palatal"),
    unit("g;", "G̣", ("ɢ",), "velar"), unit("g;w", "G̣W", ("ɢw",), "velar"),
    unit("q", "Q", (), "velar"), unit("qw", "QW", (), "velar"),
    unit("q!", "Q'", ("q'",), "velar"), unit("q!w", "Q'W", ("qw'", "q'w"), "velar"),
    unit("%;", "Ɣ̣", ("ɣ̣",), "velar"), unit("%;:", "Ɣ̣'", ("ɣ̣'",), "velar"),
    unit("%;w", "Ɣ̣W", ("ɣ̣w",), "velar"),
    unit("x;", "X̣", (), "velar"), unit("x;:", "X̣'", ("x̣'",), "velar"),
    unit("x;w", "X̣W", (), "velar"),
    unit("'", "ʔ", ("glottal stop",), "faucal"),
    unit("h", "H", (), "faucal"), unit("hw", "HW", (), "faucal"),
    unit("dl", "DL", (), "lateral"), unit("t#", "TŁ", ("tl", "ƛ"), "lateral"),
    unit("t'#", "T'Ł", ("tl'", "ƛ'"), "lateral"),
    unit("l", "L", (), "lateral"), unit("l:", "L'", ("l'",), "lateral"),
    unit("#", "Ł", ("ƚ", "ł"), "lateral"), unit("#:", "Ł'", ("ł'",), "lateral"),
]

DOCUMENTARY_EXCEPTIONS = [{
    "key": "z-exception", "display": "z", "search_aliases": ["z"],
    "series": "documentary exception", "status": "1990 documentary index exception",
    "entry_id": "e1111-z", "source_file": "Z", "headword_ascii": "Z",
    "explanation": "Preserves the literal 1990 Z.FIN headword without asserting independent phonemic status for z.",
}]

# KA.FIN is a DOS-safe filename surrogate, not the lexical headword. Its
# preserved 1990 Reference List begins with anterior-palatal ejective forms
# (``k!&...``). Keep the archival fields and stable entry ID unchanged while
# restoring the intended lexical representative on public surfaces.
DOCUMENTARY_HEADWORD_ALIASES = {
    ("e0511-ka", "KA", "KA"): {
        "ascii": "k!&a",
        "display": "k̯̓a",
        "initial_key": "k!&",
        "reason": "KA.FIN is the DOS-safe surrogate for the 1990 Anderson headword k!&a",
    },
}

ALL_CATEGORIES = JACOBS_ALPHABET + DOCUMENTARY_EXCEPTIONS
BY_KEY = {row["key"]: row for row in ALL_CATEGORIES}
ORDER = {row["key"]: number for number, row in enumerate(ALL_CATEGORIES)}
MATCH_KEYS = sorted((row["key"] for row in JACOBS_ALPHABET),
                    key=lambda key: (-len(key), ORDER[key]))


def _initial_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"t[’ʼ̓]([cs])", r"t'\1", value)
    value = re.sub(r"t[’ʼ̓](?:ł|ƚ)", "t'#", value)
    value = value.replace("č’", "t'c").replace("čʼ", "t'c").replace("č̓", "t'c")
    value = value.replace("ƛ’", "t'#").replace("ƛʼ", "t'#").replace("ƛ̓", "t'#")
    decomposed = unicodedata.normalize("NFD", value)
    out = []
    for ch in decomposed:
        if ch == "\u0323":
            if out and out[-1] != ";":
                out.append(";")
        elif ch == "\u032f":
            out.append("&")
        elif ch == "\u0313":
            out.append("!")
        elif unicodedata.combining(ch):
            continue
        else:
            out.append(ch)
    value = "".join(out)
    value = value.replace("’", "!").replace("ʼ", "!")
    value = value.replace("ɛ", "e").replace("ə", "@").replace("ł", "#").replace("ƚ", "#")
    value = value.replace("ɣ", "%").replace("ƛ", "t#").replace("č", "tc")
    value = value.replace("ǯ", "dj").replace("dʒ", "dj").replace("ʒ", "dj")
    value = value.replace("ʃ", "c").replace("š", "c")
    value = value.replace("ɢ", "g;").replace("ʷ", "w").replace("ʸ", "&")
    value = value.replace("·", ":")
    # Anderson's anterior-palatal voiced continuant spellings represent
    # Jacobs y/y', not additional gamma phonemes.
    value = re.sub(r"^%:&", "y:", value)
    value = re.sub(r"^%&", "y", value)
    value = re.sub(r"^[<:/=\-]+", "", value)
    return value


def initial_key(value: str, *, entry_id=None, source_file=None) -> str:
    text = _initial_text(value)
    if text.startswith("z"):
        exception = DOCUMENTARY_EXCEPTIONS[0]
        if (entry_id == exception["entry_id"] and source_file == exception["source_file"]
                and value == exception["headword_ascii"]):
            return exception["key"]
        raise ValueError(f"unauthorized independent-z initial: {value!r} ({entry_id}, {source_file})")
    for key in MATCH_KEYS:
        if text.startswith(key):
            return key
    raise ValueError(f"unclassifiable Jacobs initial: {value!r} -> {text!r}")


def initial_for_entry(entry) -> str:
    alias = DOCUMENTARY_HEADWORD_ALIASES.get(
        (entry.get("entry_id"), entry.get("source_file"), entry.get("headword_ascii")))
    if alias is not None:
        return alias["initial_key"]
    # The recovered A-C tables use a colon after barred L as a length mark,
    # which the display converter renders as a middle dot. Do not let the raw
    # longest-match key ``#:`` reinterpret that prosodic mark as Jacobs's
    # separate glottalized-barred-L unit. The distinction is intentionally
    # presentation-aware here; source bytes and the 68-unit inventory stay
    # unchanged.
    display = entry.get("headword", "").strip().lower()
    if display.startswith(("ł·", "ƚ·")):
        return "#"
    # The sole x-plus-length lexical headword likewise displays a middle dot.
    # Do not reinterpret that visible length as the separate Jacobs x' unit.
    if display.startswith("x·"):
        return "x"
    return initial_key(entry.get("headword_ascii") or entry["headword"],
                       entry_id=entry.get("entry_id"), source_file=entry.get("source_file"))


def public_headword_for_entry(entry) -> str:
    alias = DOCUMENTARY_HEADWORD_ALIASES.get(
        (entry.get("entry_id"), entry.get("source_file"), entry.get("headword_ascii")))
    return alias["display"] if alias is not None else entry["headword"]


def category(key: str):
    return BY_KEY[key]
