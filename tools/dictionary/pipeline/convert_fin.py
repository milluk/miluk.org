#!/usr/bin/env python3
"""Convert recovered WordPerfect 5.x .FIN files to deterministic UTF-8 text.

The recovered files contain either plain CRLF text or a WordPerfect header whose
little-endian document pointer identifies a mostly-ASCII body. WordPerfect
formatting packets are removed; lexical bytes are not normalized or corrected.
"""
import argparse
from pathlib import Path


def document_body(raw):
    if raw.startswith(b'\xffWPC'):
        if len(raw) < 8:
            raise ValueError('truncated WordPerfect header')
        offset = int.from_bytes(raw[4:8], 'little')
        if not 8 <= offset <= len(raw):
            raise ValueError(f'invalid WordPerfect document offset {offset}')
        raw = raw[offset:]
    return raw


def strip_wordperfect_codes(raw):
    out = bytearray()
    i = 0
    while i < len(raw):
        byte = raw[i]
        if byte == 0x1A:  # DOS end-of-file marker
            i += 1
            continue
        if byte == 0x90:  # WordPerfect soft line break inside a wrapped line
            i += 1
            continue
        if byte == 0xEE:  # unrecovered legacy glyph; preserve uncertainty visibly
            out.extend('�'.encode('utf-8'))
            i += 1
            continue
        if byte >= 0xC0:
            end = raw.find(bytes([byte]), i + 1, min(len(raw), i + 96))
            if end != -1:
                i = end + 1
                continue
        if byte in (9, 10, 13) or 32 <= byte <= 126:
            out.append(byte)
        i += 1
    text = out.decode('utf-8')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='directory containing .FIN files')
    parser.add_argument('--output', type=Path, required=True, help='directory for UTF-8 .txt files')
    parser.add_argument('--expected-count', type=int, default=684)
    args = parser.parse_args()
    files = sorted(args.input.glob('*.FIN'), key=lambda p: p.name.encode())
    if len(files) != args.expected_count:
        raise SystemExit(f'expected {args.expected_count} .FIN files, found {len(files)}')
    args.output.mkdir(parents=True, exist_ok=True)
    for source in files:
        text = strip_wordperfect_codes(document_body(source.read_bytes()))
        (args.output / (source.stem + '.txt')).write_text(text, encoding='utf-8', newline='\n')
    print(f'converted {len(files)} .FIN files to {args.output}')


if __name__ == '__main__':
    main()
