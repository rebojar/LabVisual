"""Confere ou sincroniza somente o código compartilhado, preservando dados locais.

Sem --apply, apenas informa diferenças. Uma edição local posterior à última
sincronização bloqueia a cópia. --baseline aceita um inventário previamente
revisado para a primeira migração; nunca equivale a sobrescrever à força.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, time, uuid

ROOT=Path(__file__).resolve().parents[1]
FILES=(
    '.gitignore','.github/FUNDING.yml','Abrir_bancada.cmd','README.md','GUIA_DE_USO.md','Experimento_visual.ipynb',
    'requirements.txt','config-local.example.json','analysis.py','engine.py','batching.py',
    'neighbors.py','neighbors_service.py','server.py','video_engine.py','launcher.py',
    'picker_dialog.py','picker_service.py','dist/index.html','dist/video.js','dist/recipe.js','dist/recipe.css',
    'tools/extract_visual.py','tools/inspect_visual.py','tools/check_publication_gate.py','tools/sync_code.py',
    'tests/test_analysis.py','tests/test_picker.py','folder_upload.py','tests/test_folder_upload.py','dist/folder.js',
    'INSTALL.md','VALIDATION.md','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md','SECURITY.md',
    'tests/test_publication_gate.py','LICENSE',
)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def safe_path(root,name):
    path=root/name
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Caminho fora da pasta selecionada.')
    return path

def refresh():
    files={name:digest(safe_path(ROOT,name)) for name in FILES}
    if None in files.values():raise ValueError('Há arquivos de código ausentes; o manifesto não será atualizado.')
    manifest={'release':'0.4.0-metodologia','files':files}
    (ROOT/'code_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return manifest

def synchronize(target,apply=False,baseline=None,backup_root=None):
    target=Path(target).resolve()
    if target==ROOT:raise ValueError('Origem e destino são a mesma pasta.')
    manifest=json.loads((ROOT/'code_manifest.json').read_text(encoding='utf-8'))
    if set(manifest['files'])!=set(FILES):raise ValueError('Lista de arquivos incompatível com o sincronizador.')
    for name,h in manifest['files'].items():
        if digest(safe_path(ROOT,name))!=h:raise ValueError('O código fonte mudou. Revise e atualize o manifesto antes de sincronizar: '+name)
    wanted={**manifest['files'],'code_manifest.json':digest(ROOT/'code_manifest.json')}
    stamp=target/'.code-sync.json'
    previous=json.loads(Path(baseline).read_text(encoding='utf-8')) if baseline else (json.loads(stamp.read_text(encoding='utf-8')) if stamp.exists() else {'files':{}})
    changes=[];conflicts=[]
    for name,h in wanted.items():
        current=digest(safe_path(target,name))
        if current==h:continue
        changes.append(name)
        if current is not None and previous.get('files',{}).get(name)!=current:conflicts.append(name)
    result={'release':manifest['release'],'differences':changes,'conflicts':conflicts,'applied':False}
    if apply:
        if conflicts:raise ValueError('Edições locais não sincronizadas: '+', '.join(conflicts))
        target.mkdir(parents=True,exist_ok=True)
        backup_base=Path(backup_root).resolve() if backup_root else safe_path(target,'.code-backups')
        backup=safe_path(backup_base,time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
        for name in changes:
            destination=safe_path(target,name)
            if destination.exists():
                saved=safe_path(backup,name);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(safe_path(ROOT,name),destination)
        stamp.write_text(json.dumps({'release':manifest['release'],'files':wanted},indent=2),encoding='utf-8')
        result['applied']=True
        result['verified']=all(digest(safe_path(target,n))==h for n,h in wanted.items())
        if not result['verified']:raise RuntimeError('A verificação após a cópia falhou.')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Atualiza o manifesto após revisar alterações no código fonte.')
    parser.add_argument('--target',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--backup-root',type=Path)
    args=parser.parse_args()
    if args.refresh:
        if args.target or args.apply or args.baseline:parser.error('--refresh é uma operação separada.')
        result={'release':refresh()['release'],'manifest_updated':True}
    else:
        if not args.target:parser.error('Informe --target ou --refresh.')
        result=synchronize(args.target,args.apply,args.baseline,args.backup_root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
