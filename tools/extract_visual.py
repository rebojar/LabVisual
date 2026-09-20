"""Copy validated visual tensor bytes into a separate Safetensors file."""
import hashlib
import argparse
import json
import os
import shutil
import struct
from pathlib import Path
from inspect_visual import inspect

EXPECTED_SHA = 'b62b0c4cd7e44edee103ee8f4fe225f246d5e768e07bfd5f25b63a8aa1fdd0c6'
REVISION = 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'
CHUNK = 4 * 1024 * 1024

def digest_range(f, start, size):
    f.seek(start)
    h = hashlib.sha256()
    while size:
        b = f.read(min(size, CHUNK))
        if not b:
            raise ValueError('Unexpected EOF')
        size -= len(b)
        h.update(b)
    return h.hexdigest()

def main(root):
    ROOT = Path(root).expanduser().resolve()
    SOURCE = ROOT / 'model.safetensors-00004-of-00004.safetensors'
    DEST = ROOT / 'Qwen3.5-9B-Vision-BF16.safetensors'
    TEMP = ROOT / 'Qwen3.5-9B-Vision-BF16.safetensors.partial'
    REPORT = ROOT / 'verificacao_encoder_visual.json'
    if not ROOT.is_dir():
        raise FileNotFoundError(f'Diretório do modelo não encontrado: {ROOT}')
    if any(p.exists() for p in (DEST, TEMP, REPORT)):
        raise FileExistsError('Destination, partial file or report already exists; nothing overwritten')
    info = inspect(SOURCE)
    with SOURCE.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != EXPECTED_SHA:
            raise ValueError('Source checksum differs from official file')
    if info['visual_tensor_count'] != 333 or info['visual_blocks'] != list(range(27)):
        raise ValueError('Unexpected visual architecture')
    if shutil.disk_usage(ROOT).free < info['visual_bytes'] + 100_000_000:
        raise OSError('Insufficient disk space')
    header = {'__metadata__': {'format': 'pt', 'source_repository': 'Qwen/Qwen3.5-9B',
              'source_revision': REVISION, 'source_sha256': EXPECTED_SHA,
              'scope': 'model.visual.*; original tensor names and bytes preserved'}}
    position = 0
    names = sorted(info['visual_tensors'])
    for name in names:
        t = info['visual_tensors'][name]
        size = t['data_offsets'][1] - t['data_offsets'][0]
        header[name] = {'dtype': t['dtype'], 'shape': t['shape'], 'data_offsets': [position, position + size]}
        position += size
    raw = json.dumps(header, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    raw += b' ' * ((-len(raw)) % 8)
    with SOURCE.open('rb') as src, TEMP.open('xb') as dst:
        dst.write(struct.pack('<Q', len(raw)))
        dst.write(raw)
        for name in names:
            a, b = info['visual_tensors'][name]['data_offsets']
            src.seek(info['data_start'] + a)
            remaining = b - a
            while remaining:
                chunk = src.read(min(CHUNK, remaining))
                if not chunk:
                    raise ValueError('Unexpected EOF while copying')
                dst.write(chunk)
                remaining -= len(chunk)
        dst.flush()
        os.fsync(dst.fileno())
    after = inspect(TEMP)
    if set(after['visual_tensors']) != set(names) or after['tensor_count'] != len(names):
        raise ValueError('Wrong output tensor names')
    with SOURCE.open('rb') as src, TEMP.open('rb') as dst:
        for name in names:
            a, b = info['visual_tensors'][name]['data_offsets']
            c, d = after['visual_tensors'][name]['data_offsets']
            if digest_range(src, info['data_start'] + a, b - a) != digest_range(dst, after['data_start'] + c, d - c):
                raise ValueError('Copied tensor differs: ' + name)
    with TEMP.open('rb') as f:
        output_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    TEMP.rename(DEST)
    report = {'origem': str(SOURCE), 'destino': str(DEST), 'checkpoint': 'Qwen/Qwen3.5-9B',
              'revisao_oficial': REVISION, 'sha256_origem': EXPECTED_SHA, 'sha256_destino': output_sha,
              'tensores_visuais': len(names), 'parametros': info['visual_parameters'],
              'bytes_dos_pesos': info['visual_bytes'], 'bytes_arquivo': DEST.stat().st_size,
              'verificacoes': {'download_oficial_sha256': 'confirmado',
                'copia_dos_333_tensores_byte_a_byte': 'confirmada',
                'nomes_dimensoes_tipo_offsets': 'confirmados',
                'carregamento_no_pytorch': 'ainda_nao_testado',
                'equivalencia_com_mmproj_gguf': 'ainda_nao_verificada'},
              'observacao': 'Arquivo contém torre visual e merger; prefixo model.visual. preservado. Não é um pacote AutoModel completo.'}
    with REPORT.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extrai sem treinamento a torre visual do checkpoint oficial Qwen3.5-9B.')
    parser.add_argument('model_dir', help='Pasta local com o quarto shard oficial e os arquivos de configuração.')
    main(parser.parse_args().model_dir)
