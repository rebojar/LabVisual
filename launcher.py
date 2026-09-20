"""Abre a bancada local. Use Abrir_bancada.cmd com dois cliques."""
from pathlib import Path
import subprocess, sys, urllib.request, json, time, webbrowser, os, hashlib

ROOT = Path(__file__).resolve().parent
PORT=int(os.environ.get('QWEN35_PORT','8765'))
URL = f'http://127.0.0.1:{PORT}'

def disponivel():
    try:
        with urllib.request.urlopen(URL+'/api/info',timeout=2) as r:
            info=json.load(r)
            if info.get('instance') != hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]:
                raise RuntimeError('Há outra bancada nesta porta. Feche-a ou escolha outra porta com QWEN35_PORT.')
            return info.get('name') == 'Bancada visual'
    except RuntimeError:raise
    except Exception:
        return False

def iniciar(abrir=True):
    # A pasta é escolhida pelo navegador, assim como imagens e vídeos.
    # O seletor Python legado não precisa iniciar uma janela separada.
    iniciar_vizinhos()
    if not disponivel():
        log=(ROOT/'.servidor.log').open('a',encoding='utf-8')
        processo=subprocess.Popen([sys.executable,str(ROOT/'server.py')],cwd=ROOT,
            stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (ROOT/'.servidor.pid').write_text(str(processo.pid),encoding='ascii')
        for _ in range(60):
            if disponivel(): break
            if processo.poll() is not None:
                raise RuntimeError('O serviço não iniciou. Consulte .servidor.log nesta pasta.')
            time.sleep(.5)
        else: raise RuntimeError('O serviço demorou para iniciar. Tente abrir novamente.')
    if abrir: webbrowser.open(URL)
    print(URL)

def iniciar_seletor():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT+3}/health',timeout=2) as r:
            if json.load(r).get('name')=='Seletor de pastas da bancada':return
    except Exception: pass
    # A interface pode ser servida por uma sessão sem desktop. O seletor deve
    # nascer quando o inicializador é aberto na sessão interativa da pessoa.
    from picker_dialog import interactive_desktop
    if not interactive_desktop(): return
    log=(ROOT/'.seletor.log').open('a',encoding='utf-8')
    p=subprocess.Popen([sys.executable,str(ROOT/'picker_service.py')],cwd=ROOT,
        stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (ROOT/'.seletor.pid').write_text(str(p.pid),encoding='ascii')

def iniciar_vizinhos():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT+4}/health',timeout=2) as r:
            if json.load(r).get('name')=='Explorador de vizinhos da bancada':return
    except Exception:pass
    log=(ROOT/'.vizinhos.log').open('a',encoding='utf-8')
    p=subprocess.Popen([sys.executable,str(ROOT/'neighbors_service.py')],cwd=ROOT,
        stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (ROOT/'.vizinhos.pid').write_text(str(p.pid),encoding='ascii')

if __name__ == '__main__':
    iniciar(abrir='--sem-navegador' not in sys.argv)
