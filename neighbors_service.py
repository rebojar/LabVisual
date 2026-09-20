"""Explorador local independente: consulta resultados sem ocupar o encoder."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
import io,json,re,secrets,urllib.request,os
import neighbors

BASE_PORT=int(os.environ.get('QWEN35_PORT','8765'))
PORT=BASE_PORT+4
ORIGINS={f'http://127.0.0.1:{BASE_PORT}',f'http://localhost:{BASE_PORT}'}
MEDIA_KEY=secrets.token_urlsafe(24)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def cors(self):
        origin=self.headers.get('Origin')
        if origin in ORIGINS:self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
    def send(self,data,status=200):
        self.send_response(status);self.cors();self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(json.dumps(data,ensure_ascii=False,allow_nan=False).encode())
    def authorized(self):
        if self.headers.get('Origin') not in ORIGINS:return False
        with urllib.request.urlopen(f'http://127.0.0.1:{BASE_PORT}/',timeout=4) as r:
            key=re.search(r"const key='([^']+)'",r.read().decode()).group(1)
        return secrets.compare_digest(self.headers.get('X-Lab-Key',''),key)
    def do_OPTIONS(self):
        if self.headers.get('Origin') not in ORIGINS:return self.send({'error':'Origem não permitida.'},403)
        self.send_response(204);self.cors();self.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','X-Lab-Key');self.end_headers()
    def do_GET(self):
        try:
            parts=urlparse(self.path);q=parse_qs(parts.query)
            if parts.path=='/health':return self.send({'name':'Explorador de vizinhos da bancada'})
            if parts.path=='/thumbnail':
                if not secrets.compare_digest(q.get('key',[''])[0],MEDIA_KEY):return self.send({'error':'Não autorizado.'},403)
                im=neighbors.thumbnail(q['dataset'][0],int(q['index'][0]));b=io.BytesIO();im.save(b,format='PNG')
                self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Cache-Control','private, max-age=600');self.send_header('Referrer-Policy','no-referrer');self.end_headers();return self.wfile.write(b.getvalue())
            if not self.authorized():return self.send({'error':'Atualize a página da bancada.'},403)
            if parts.path=='/datasets':return self.send({'datasets':[{'id':s['id'],'label':s['label']} for s in neighbors.sources()],'media_key':MEDIA_KEY})
            if parts.path=='/dataset':return self.send(neighbors.public_dataset(neighbors.dataset(q['id'][0])))
            if parts.path=='/compare':return self.send(neighbors.compare(q['id'][0],int(q['index'][0])))
            return self.send({'error':'Rota inexistente.'},404)
        except (ValueError,KeyError,FileNotFoundError,IndexError) as error:self.send({'error':str(error)},400)
        except Exception:self.send({'error':'Não foi possível consultar o conjunto salvo.'},500)

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
