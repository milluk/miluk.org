#!/usr/bin/env python3
"""Create a deterministic SHA-256 manifest for an archival directory."""
import argparse
import hashlib
from pathlib import Path

from jsonio import write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--glob', default='*')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--schema', default='miluk-archive-hash-manifest/1')
    args = parser.parse_args()
    files = sorted((path for path in args.root.glob(args.glob) if path.is_file()),
                   key=lambda path: path.relative_to(args.root).as_posix().encode())
    records = []
    for path in files:
        data = path.read_bytes()
        records.append({'path': path.relative_to(args.root).as_posix(),
                        'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    write(args.output, {'schema': args.schema, 'file_count': len(records), 'files': records})
    print(f'manifested {len(records)} files in {args.output}')


if __name__ == '__main__':
    main()
