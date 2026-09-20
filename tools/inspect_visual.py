"""Inspect Safetensors headers without loading tensor data or importing ML libraries."""
import argparse
import collections
import hashlib
import json
import math
import struct
from pathlib import Path

DTYPE_BYTES = {'BF16': 2, 'F16': 2, 'F32': 4, 'F64': 8, 'I64': 8, 'I32': 4, 'I16': 2, 'I8': 1, 'U8': 1, 'BOOL': 1}

def unique_object(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('Duplicate JSON key: ' + k)
        d[k] = v
    return d

def inspect(path):
    path = Path(path)
    size = path.stat().st_size
    with path.open('rb') as f:
        prefix = f.read(8)
        if len(prefix) != 8:
            raise ValueError('Missing header length')
        n = struct.unpack('<Q', prefix)[0]
        if not (2 <= n <= min(100_000_000, size - 8)):
            raise ValueError('Invalid header length')
        raw = f.read(n)
    h = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
    tensors = {k: v for k, v in h.items() if k != '__metadata__'}
    intervals = []
    for name, t in tensors.items():
        shape, offsets, dtype = t['shape'], t['data_offsets'], t['dtype']
        if any(type(x) is not int or x < 0 for x in shape):
            raise ValueError('Invalid shape: ' + name)
        if len(offsets) != 2 or any(type(x) is not int for x in offsets):
            raise ValueError('Invalid offsets: ' + name)
        a, b = offsets
        if not 0 <= a <= b <= size - 8 - n:
            raise ValueError('Out-of-file data: ' + name)
        if dtype not in DTYPE_BYTES:
            raise ValueError('Unsupported dtype for this inspector: ' + dtype)
        if math.prod(shape) * DTYPE_BYTES[dtype] != b - a:
            raise ValueError('Shape/byte mismatch: ' + name)
        if b > a:
            intervals.append((a, b, name))
    cursor = 0
    for a, b, name in sorted(intervals):
        if a != cursor:
            raise ValueError('Overlapping or missing data interval: ' + name)
        cursor = b
    if cursor != size - 8 - n:
        raise ValueError('Unindexed bytes at end')
    visual = {k: v for k, v in tensors.items() if k.startswith('model.visual.')}
    if not visual:
        raise ValueError('No model.visual tensors')
    visual_bytes = sum(t['data_offsets'][1] - t['data_offsets'][0] for t in visual.values())
    blocks = sorted({int(k.split('.')[3]) for k in visual if k.startswith('model.visual.blocks.')})
    return {'source': str(path.resolve()), 'file_bytes': size, 'header_bytes': n,
            'header_sha256': hashlib.sha256(raw).hexdigest(), 'data_start': n + 8,
            'tensor_count': len(tensors), 'visual_tensor_count': len(visual),
            'visual_bytes': visual_bytes, 'visual_parameters': sum(math.prod(t['shape']) for t in visual.values()),
            'visual_dtypes': dict(collections.Counter(t['dtype'] for t in visual.values())),
            'visual_blocks': blocks, 'visual_tensors': visual,
            'checks': {'header_and_byte_ranges': 'pass', 'weights_finite': 'not_checked',
                       'official_identity': 'not_checked', 'gguf_equivalence': 'not_checked'}}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    report = inspect(args.source)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'visual_tensors'}, ensure_ascii=False, indent=2))
    print('Visual example tensors:', list(report['visual_tensors'])[:6])
