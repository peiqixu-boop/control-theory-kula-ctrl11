"""Package generated CSVs losslessly for small, independently verifiable uploads."""
from pathlib import Path
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / 'data/generated/archive'
archive.mkdir(parents=True, exist_ok=True)
manifest = {}
for name in ('critical', 'fast', 'chr'):
    data = (ROOT / f'data/generated/{name}.csv').read_bytes()
    packed = gzip.compress(data, compresslevel=9, mtime=0)
    entry = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'parts': []}
    for i, offset in enumerate(range(0, len(packed), 512 * 1024), 1):
        chunk = packed[offset:offset + 512 * 1024]
        filename = f'{name}.csv.gz.part{i:03d}'
        (archive / filename).write_bytes(chunk)
        entry['parts'].append({'file': filename, 'sha256': hashlib.sha256(chunk).hexdigest()})
    manifest[name] = entry
(archive / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print('Packed three full-resolution CSVs with SHA-256 checksums.')
