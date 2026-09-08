#!/usr/bin/env python3
"""Import the 922-row Jacobs collation workbook without third-party packages."""
import argparse
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from jsonio import read, write

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def worksheet_rows(workbook, sheet_number):
    with zipfile.ZipFile(workbook) as archive:
        root = ET.fromstring(archive.read(f'xl/worksheets/sheet{sheet_number}.xml'))
    rows = []
    for row in root.findall('.//m:sheetData/m:row', NS):
        values = {}
        for cell in row.findall('m:c', NS):
            column = re.match(r'[A-Z]+', cell.attrib['r']).group()
            if cell.attrib.get('t') == 'inlineStr':
                value = ''.join(node.text or '' for node in cell.findall('.//m:t', NS))
            else:
                node = cell.find('m:v', NS)
                value = node.text if node is not None else ''
            values[column] = value
        rows.append(values)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--applied', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = worksheet_rows(args.workbook, 1)
    if len(rows) != 923:
        raise SystemExit(f'expected header plus 922 collation rows, found {len(rows)}')
    applied = read(args.applied)
    applied_by_target = {}
    for item in applied:
        key = (re.match(r't\d+', item['story_id']).group(), str(item['line']))
        applied_by_target.setdefault(key, []).append(item)
    corrections = []
    for row in rows[1:]:
        number = int(row['A'])
        story_code = re.match(r't\d+', row['B']).group()
        candidates = applied_by_target.get((story_code, row['C']), [])
        applied_item = next(
            (item for item in candidates
             if item['transcription'].rstrip('.)') == row['F'].rstrip('.)')),
            None,
        )
        workbook_applied = row['G'] == 'APPLIED to corpus'
        disposition = 'changed' if workbook_applied and applied_item else 'unresolved'
        corrections.append({
            'correction_id': f'collation-1939-{number:04d}',
            'target': {'source': 'corpus', 'story_id': row['B'],
                       'line': int(row['C']), 'field': 'miluk_ascii'},
            'original_value': row['F'],
            'revised_value': applied_item['new'] if applied_item else None,
            'disposition': disposition,
            'reason': row['D'],
            'verification_source': f"Jacobs, Coos Narrative and Ethnologic Texts (1939), {row['H']}",
            'affects': '1939',
            'restoration_stage': '2026 Jacobs collation',
            'jacobs_prints': row['E'],
            'workbook_status': row['G'],
        })
    write(args.output, {
        'schema': 'miluk-correction-ledger/1',
        'source_record_count': 922,
        'summary': {
            'changed_observations': sum(c['disposition'] == 'changed' for c in corrections),
            'unresolved_observations': sum(c['disposition'] == 'unresolved' for c in corrections),
            'unique_applied_transformations': len(applied),
        },
        'corrections': corrections,
    })
    print(f'imported {len(corrections)} collation observations')


if __name__ == '__main__':
    main()
