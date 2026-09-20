"""Cópias locais das pastas escolhidas pelo navegador, sem executar o encoder."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import threading
import uuid

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
MAX_FILE_BYTES = 20_000_000
MAX_FILES = 5000


def relative_name(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Nome de arquivo inválido na pasta selecionada.')
    path = PurePosixPath(value)
    parts = value.split('/')
    devices = {'con', 'prn', 'aux', 'nul'} | {f'{p}{n}' for p in ('com', 'lpt') for n in range(1, 10)}
    if path.is_absolute() or any(
        part in ('', '.', '..') or part != part.rstrip(' .')
        or any(ord(c) < 32 or c in ':*?"<>|' for c in part)
        or part.split('.')[0].casefold() in devices for part in parts
    ):
        raise ValueError('O arquivo precisa ter um caminho relativo válido dentro da pasta.')
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError('Formato de imagem não aceito no lote.')
    return path.as_posix()


class FolderUploads:
    def __init__(self, root):
        self.root = Path(root).resolve() / 'imports'
        self.pending = {}
        self.lock = threading.RLock()

    def start(self, label, files):
        if not isinstance(label, str) or not label.strip() or len(label) > 255:
            raise ValueError('Nome de pasta inválido.')
        if any(c in label for c in '/\\\x00'):
            raise ValueError('Nome de pasta inválido.')
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
            raise ValueError('Escolha de 1 a 5.000 imagens por lote.')
        expected = {}
        seen = set()
        for file in files:
            name = relative_name(file['path'])
            size = file['bytes']
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
                raise ValueError('Cada imagem precisa ter até 20 MB.')
            if name.casefold() in seen:
                raise ValueError('A seleção contém nomes de arquivo repetidos.')
            seen.add(name.casefold())
            expected[name] = size
        with self.lock:
            self.root.mkdir(parents=True, exist_ok=True)
            if sum(expected.values()) + 1_000_000 > shutil.disk_usage(self.root).free:
                raise ValueError('Não há espaço para a cópia local. Use a opção de informar o caminho da pasta.')
            ident = uuid.uuid4().hex
            folder = self.root / ('pasta_' + ident)
            folder.mkdir()
            self.pending[ident] = {'folder': folder, 'label': label, 'expected': expected, 'received': {}}
        return {'id': ident, 'count': len(expected)}

    def put(self, ident, name, raw):
        name = relative_name(name)
        with self.lock:
            entry = self.pending.get(ident)
            if entry is None:
                raise ValueError('Seleção expirada. Escolha a pasta novamente.')
            if name not in entry['expected'] or len(raw) != entry['expected'][name]:
                raise ValueError('O arquivo recebido difere da seleção informada.')
            if name in entry['received']:
                raise ValueError('Este arquivo já foi recebido.')
            destination = (entry['folder'] / name).resolve()
            if not destination.is_relative_to(entry['folder'].resolve()):
                raise ValueError('Arquivo fora da pasta selecionada.')
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as handle:
                handle.write(raw)
            entry['received'][name] = hashlib.sha256(raw).hexdigest()
            return {'received': len(entry['received']), 'total': len(entry['expected'])}

    def finish(self, ident):
        with self.lock:
            entry = self.pending.get(ident)
            if entry is None:
                raise ValueError('Seleção expirada. Escolha a pasta novamente.')
            if entry['received'].keys() != entry['expected'].keys():
                raise ValueError('Aguarde a cópia de todas as imagens antes de conferir a pasta.')
            origin = {'type': 'browser_folder', 'label': entry['label'],
                      'files': [{'path': name, 'bytes': size, 'sha256': entry['received'][name]}
                                for name, size in entry['expected'].items()]}
            (entry['folder'] / 'origem_navegador.json').write_text(
                json.dumps(origin, ensure_ascii=False, indent=2), encoding='utf-8')
            del self.pending[ident]
            return {'folder': str(entry['folder']), 'label': entry['label'], 'count': len(entry['expected'])}

    def cancel(self, ident):
        with self.lock:
            entry = self.pending.get(ident)
            if entry is None:
                return {'cancelled': False}
            folder = entry['folder'].resolve()
            # Apenas nossa pasta temporária identificada: nunca um caminho recebido.
            if folder.parent != self.root.resolve() or folder.name != 'pasta_' + ident:
                raise ValueError('Pasta temporária inválida.')
            shutil.rmtree(folder)
            del self.pending[ident]
            return {'cancelled': True}
