"""Auxiliar local para o seletor nativo. Não executa nem modifica o encoder."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,re,subprocess,sys,threading,urllib.request,os,logging
from picker_dialog import interactive_desktop,DESKTOP_MESSAGE

ROOT=Path(__file__).resolve().parent
BASE_PORT=int(os.environ.get('QWEN35_PORT','8765'))
PORT=BASE_PORT+3
ORIGINS={f'http://127.0.0.1:{BASE_PORT}',f'http://localhost:{BASE_PORT}'}
LOCK=threading.Lock()

def choose(initial):
    if not interactive_desktop(): raise RuntimeError(DESKTOP_MESSAGE)
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    proc=subprocess.run([sys.executable,str(ROOT/'picker_dialog.py'),initial],
        capture_output=True,text=True,encoding='utf-8',env=env,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if proc.returncode:
        logging.error('Falha no seletor de pastas (saída %s): %s',proc.returncode,proc.stderr.strip())
        raise RuntimeError('Não foi possível abrir o seletor de pastas. Tente novamente ou informe o caminho manualmente. O detalhe foi registrado no log local do seletor.')
    result=json.loads(proc.stdout)
    if not result['cancelled'] and not Path(result['folder']).is_dir():
        raise ValueError('A pasta escolhida não está disponível.')
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def cors(self):
        origin=self.headers.get('Origin')
        if origin in ORIGINS:
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
    def send(self,data,status=200):
        self.send_response(status);self.cors()
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.end_headers()
        self.wfile.write(json.dumps(data,ensure_ascii=False).encode())
    def do_OPTIONS(self):
        if self.headers.get('Origin') not in ORIGINS:return self.send({'error':'Origem não permitida.'},403)
        self.send_response(204);self.cors()
        self.send_header('Access-Control-Allow-Methods','POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type, X-Lab-Key')
        self.end_headers()
    def do_GET(self):
        if self.path=='/health':self.send({'name':'Seletor de pastas da bancada','interactive':interactive_desktop()})
        else:self.send({'error':'Rota inexistente.'},404)
    def do_POST(self):
        if self.path!='/choose':return self.send({'error':'Rota inexistente.'},404)
        if self.headers.get('Origin') not in ORIGINS:return self.send({'error':'Origem não permitida.'},403)
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{BASE_PORT}/',timeout=5) as response:
                key=re.search(r"const key='([^']+)'",response.read().decode()).group(1)
            if self.headers.get('X-Lab-Key')!=key:return self.send({'error':'Atualize a página da bancada.'},403)
            length=int(self.headers.get('Content-Length','0'))
            if length>16384:raise ValueError('Caminho inválido.')
            data=json.loads(self.rfile.read(length) or b'{}')
            if not LOCK.acquire(blocking=False):return self.send({'error':'Já existe uma janela para escolher a pasta.'},409)
            try:self.send(choose(str(data.get('initial',''))))
            finally:LOCK.release()
        except Exception as error:self.send({'error':str(error)},400)

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
