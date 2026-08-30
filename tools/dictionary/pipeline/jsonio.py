"""Deterministic JSON helpers shared by restoration stages."""
import json


def read(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
