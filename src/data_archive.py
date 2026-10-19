"""Restore full-resolution CSVs from lossless, SHA-256 checked repository parts."""
from pathlib import Path
import gzip
import hashlib
import json


def restore_saved_data(root):
    generated = Path(root) / 'data/generated'
    archive = generated / 'archive'
    missing = [name for name in ('critical', 'fast', 'chr')
               if not (generated / f'{name}.csv').exists()]
    if not missing:
        return
    manifest = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))
    for name in missing:
        entry = manifest[name]
        chunks = []
        for i, part in enumerate(entry['parts'], 1):
            expected = f'{name}.csv.gz.part{i:03d}'
            if part['file'] != expected:
                raise ValueError(f'Unexpected archive part: {part["file"]}')
            chunk = (archive / expected).read_bytes()
            if hashlib.sha256(chunk).hexdigest() != part['sha256']:
                raise ValueError(f'Archive checksum mismatch: {expected}')
            chunks.append(chunk)
        data = gzip.decompress(b''.join(chunks))
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError(f'CSV checksum mismatch: {name}')
        (generated / f'{name}.csv').write_bytes(data)
