from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import base64, json, io, threading, uuid, traceback, inspect, secrets, subprocess, sys, os, time, socket, hashlib
import engine, batching, video_engine, analysis
from folder_upload import FolderUploads

ROOT=Path(__file__).resolve().parent
SESSIONS=ROOT/'sessions'; SESSIONS.mkdir(exist_ok=True)
JOBS={}; LOCK=threading.Lock(); KEY=secrets.token_urlsafe(32)
FOLDER_UPLOADS=FolderUploads(ROOT)
VIDEO_JOBS={}
PORT=int(os.environ.get('QWEN35_PORT','8765')); NB_PORT=PORT+1; NB_TOKEN=secrets.token_urlsafe(32); NB_PROCESS=None

def save_analysis(job, result, video=False, reused=False):
    """Persiste a receita aplicada junto dos tokens e do registro da execução."""
    history=job.get('analysis_history',[])+[{'at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'recipe':result['analysis']['recipe'],'reused_tokens':reused}]
    engine.salvar_resultado(result,job['folder']/'representacoes.npz')
    record={'preparacao':job['prepared']['info'],'execucao':result['info'],
            'analysis':analysis.summary(result),'analysis_history':history,
            'hipotese':job.get('hypothesis',''),'notas':job.get('notes','')}
    if video:
        import numpy as np
        np.savez_compressed(job['folder']/'pares_temporais.npz',vetores=result['pair_vectors'],
            vetores_analise_antes=result['analysis_pairs']['before'],
            vetores_analise_depois=result['analysis_pairs']['after'],
            receita_json=np.asarray(analysis.recipe_json(result['analysis']['recipe'])),
            tempos=np.array(job['prepared']['info']['timestamps']).reshape(-1,2))
    (job['folder']/'registro.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    job.update(result=result,analysis_history=history,recipe=result['analysis']['recipe'])

def default_folder():
    try:
        config=json.loads((ROOT/'config-local.json').read_text(encoding='utf-8'))
        return str(config.get('default_image_folder') or Path.home())
    except FileNotFoundError:return str(Path.home())

def video_run(job):
    try:
        result=video_engine.execute(job['prepared'],lambda label,n:job.update(status=label,completed_blocks=n),job['recipe'])
        save_analysis(job,result,video=True)
        job.update(result=result,state='done',status='Sequência processada',completed_blocks=27)
    except Exception as e:
        job.update(state='error',status=str(e))
    finally: LOCK.release()

def uri(im):
    b=io.BytesIO(); im.save(b,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()

def job_run(job):
    def progress(label,n): job.update(status=label,completed_blocks=n)
    try:
        result=engine.executar_encoder(job['prepared'],progress,job['recipe'])
        save_analysis(job,result)
        job.update(state='done',status='Representações prontas',completed_blocks=27)
    except Exception as e:
        job.update(state='error',status=str(e),error=traceback.format_exc())
    finally: LOCK.release()

def notebook_url():
    global NB_PROCESS
    # Reutiliza o caderno após atualizar o serviço da interface, sem encerrar kernels.
    import urllib.request
    for f in (ROOT/'.runtime').glob('jpserver-*.json'):
        try:
            saved=json.loads(f.read_text(encoding='utf-8'))
            if saved.get('port')!=NB_PORT: continue
            token=saved.get('token','')
            req=urllib.request.Request(f'http://127.0.0.1:{NB_PORT}/api',headers={'Authorization':'token '+token})
            with urllib.request.urlopen(req,timeout=1):
                return f'http://127.0.0.1:{NB_PORT}/lab/tree/Experimento_visual.ipynb?token={token}'
        except Exception: pass
    if NB_PROCESS is None or NB_PROCESS.poll() is not None:
        env=os.environ.copy()
        env['JUPYTER_RUNTIME_DIR']=str(ROOT/'.runtime'); env['JUPYTER_CONFIG_DIR']=str(ROOT/'.jupyter')
        env['JUPYTER_DATA_DIR']=str(ROOT/'.jupyter-data')
        log=(ROOT/'.notebook.log').open('a',encoding='utf-8')
        NB_PROCESS=subprocess.Popen([sys.executable,'-m','jupyterlab','--no-browser','--ip=127.0.0.1',
           f'--port={NB_PORT}','--ServerApp.port_retries=0',f'--ServerApp.root_dir={ROOT}',
           f'--IdentityProvider.token={NB_TOKEN}'],cwd=ROOT,env=env,stdout=log,stderr=log,
           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1',NB_PORT),timeout=.2): break
        except OSError:
            if NB_PROCESS.poll() is not None: raise RuntimeError('O caderno não iniciou. Consulte .notebook.log.')
            time.sleep(.2)
    else: raise RuntimeError('O caderno está demorando para iniciar; tente novamente em alguns segundos.')
    return f'http://127.0.0.1:{NB_PORT}/lab/tree/Experimento_visual.ipynb?token={NB_TOKEN}'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('Pragma','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def send(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        route=urlparse(self.path).path
        if route=='/':
            raw=(ROOT/'dist/index.html').read_text(encoding='utf-8').replace('__LAB_KEY__',KEY).encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(raw)
        elif route in ('/video.js','/recipe.js','/recipe.css','/folder.js'):
            self.send_response(200); self.send_header('Content-Type',('text/css' if route.endswith('.css') else 'text/javascript')+'; charset=utf-8')
            self.end_headers();self.wfile.write((ROOT/'dist'/route[1:]).read_bytes())
        elif route.startswith('/api/video/job/'):
            job=VIDEO_JOBS.get(route.rsplit('/',1)[-1])
            if not job:return self.send({'error':'Envie o vídeo novamente.'},404)
            r=job.get('result')
            self.send({'state':job['state'],'status':job['status'],'completed_blocks':job.get('completed_blocks',0),
                       'info':r['info'] if r else None,'vector':r['analysis']['after'].tolist() if r else None,
                       'pairs':r['analysis_pairs']['after'].tolist() if r else None,
                       'vector_before':r['analysis']['before'].tolist() if r else None,
                       'pairs_before':r['analysis_pairs']['before'].tolist() if r else None,
                       'analysis':analysis.summary(r) if r else None,
                       'temporal_comparisons':r['temporal_comparisons'] if r else None})
        elif route.startswith('/video-file/'):
            parts=route.split('/')
            if len(parts)!=4 or parts[2] not in VIDEO_JOBS:return self.send({'error':'Não encontrado.'},404)
            name=parts[3];job=VIDEO_JOBS[parts[2]]
            allowed=name in ('representacoes.npz','registro.json','pares_temporais.npz') or name in job.get('frame_files',[])
            p=job['folder']/name
            if not allowed or not p.is_file():return self.send({'error':'Arquivo indisponível.'},404)
            self.send_response(200);self.send_header('Content-Type','image/png' if name.endswith('.png') else 'application/octet-stream')
            if not name.endswith('.png'):self.send_header('Content-Disposition',f'attachment; filename="video_{name}"')
            self.end_headers();self.wfile.write(p.read_bytes())
        elif route=='/api/info':
            self.send({'name':'Bancada visual','version':4,'release':'0.4.0-metodologia','busy':LOCK.locked(),
                'instance':hashlib.sha256(str(ROOT).encode()).hexdigest()[:16],
                'folder_picker':'browser',
              'default_folder':default_folder(),
              'model_available':(engine.MODEL_DIR/'Qwen3.5-9B-Vision-BF16.safetensors').exists(),
              'code':{n:inspect.getsource(getattr(engine,n)) for n in ['ler_rgba','compor_fundo','abrir_imagem','preparar_imagem','carregar_encoder','executar_encoder','salvar_resultado']}})
        elif route.startswith('/api/batch/'):
            try:
                ident=route.rsplit('/',1)[-1]
                job=batching.latest() if ident=='latest' else batching.get(ident)
                self.send(batching.public(job) if job else None)
            except Exception as e: self.send({'error':str(e)},404)
        elif route.startswith('/thumbnail/'):
            try:
                parts=route.split('/');im=batching.thumbnail(parts[2],int(parts[3]))
                b=io.BytesIO();im.save(b,format='PNG')
                self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write(b.getvalue())
            except Exception: self.send({'error':'Miniatura indisponível.'},404)
        elif route.startswith('/batch-download/'):
            try:
                _,_,ident,name=route.split('/')
                if name not in ('embeddings.npz','registro.json'): raise ValueError('Arquivo não permitido.')
                p=batching.get(ident)['_folder']/name
                raw=p.read_bytes()
                self.send_response(200);self.send_header('Content-Type','application/octet-stream')
                self.send_header('Content-Disposition',f'attachment; filename="lote_{ident[:8]}_{name}"')
                self.end_headers();self.wfile.write(raw)
            except Exception as e: self.send({'error':str(e)},404)
        elif route.startswith('/api/job/'):
            job=JOBS.get(route.rsplit('/',1)[-1])
            if not job: return self.send({'error':'Experimento não encontrado.'},404)
            result=job.get('result')
            self.send({'state':job['state'],'status':job['status'],'completed_blocks':job.get('completed_blocks',0),
             'info':result['info'] if result else None,'values':result['analysis']['after'][:48].tolist() if result else None,
             'all_values':result['analysis']['after'].tolist() if result else None,
             'all_before':result['analysis']['before'].tolist() if result else None,
             'analysis':analysis.summary(result) if result else None,
             'before_sample':result['antes'][:4,:8].tolist() if result else None,
             'after_sample':result['depois'][:4,:8].tolist() if result else None,'error':job.get('error')})
        elif route.startswith('/download/'):
            parts=route.split('/')
            if len(parts)!=4 or parts[2] not in JOBS or parts[3] not in ('representacoes.npz','registro.json'): return self.send({'error':'Não encontrado.'},404)
            p=JOBS[parts[2]]['folder']/parts[3]
            if not p.exists(): return self.send({'error':'Execute a imagem primeiro.'},404)
            self.send_response(200);self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Disposition',f'attachment; filename="{p.name}"');self.end_headers();self.wfile.write(p.read_bytes())
        else: self.send({'error':'Não encontrado.'},404)
    def do_POST(self):
        if self.headers.get('X-Lab-Key')!=KEY: return self.send({'error':'Reabra a página da bancada.'},403)
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return self.send({'error':'Origem não permitida.'},403)
        n=int(self.headers.get('Content-Length','0'))
        if n>70_000_000: return self.send({'error':'Use um arquivo de até 50 MB (20 MB para imagem).'},413)
        try:
            data=json.loads(self.rfile.read(n) or b'{}');route=urlparse(self.path).path
            if route in ('/api/reanalyze','/api/video/reanalyze'):
                video=route=='/api/video/reanalyze'
                job=(VIDEO_JOBS if video else JOBS).get(data.get('id'))
                recipe=analysis.recipe(data.get('recipe'))
                if not job or job.get('state')!='done' or 'result' not in job:
                    return self.send({'error':'Execute o encoder primeiro para obter os tokens completos.'},409)
                if not LOCK.acquire(blocking=False):return self.send({'error':'Aguarde a operação atual.'},409)
                try:
                    result=(video_engine.reanalyze(job['result'],job['prepared'],recipe) if video
                            else engine.reanalisar(job['result'],recipe))
                    save_analysis(job,result,video=video,reused=True)
                    job['status']='Análise recalculada com os tokens salvos; o encoder não executou novamente.'
                    self.send({'ok':True,'reused_tokens':True,'analysis':analysis.summary(result)})
                finally:LOCK.release()
            elif route=='/api/video/upload':
                raw=base64.b64decode(data['file'].split(',',1)[1],validate=True)
                if len(raw)>50_000_000:raise ValueError('Use um vídeo ou GIF de até 50 MB.')
                ident=uuid.uuid4().hex;folder=ROOT/'videos'/ident;folder.mkdir(parents=True)
                source=folder/'original.media';source.write_bytes(raw)
                meta=video_engine.inspect_media(source)
                VIDEO_JOBS[ident]={'folder':folder,'source':source,'meta':meta,'state':'uploaded','status':'Arquivo lido'}
                self.send({'id':ident,'meta':meta})
            elif route=='/api/video/prepare':
                if not LOCK.acquire(blocking=False):return self.send({'error':'Aguarde a operação atual do encoder.'},409)
                try:
                    job=VIDEO_JOBS.get(data['id'])
                    if not job:raise ValueError('Envie o vídeo novamente.')
                    job.pop('prepared',None);job.pop('result',None);job.update(state='uploaded',status='Preparando sequência')
                    prepared=video_engine.prepare(job['source'],job['meta'],data)
                    frame_files=[]
                    for tag in ('original','prepared'):
                        for i,im in enumerate(prepared[tag+'_frames']):
                            name=f'{tag}_{i:02d}.png';im.save(job['folder']/name);frame_files.append(name)
                    job.update(prepared=prepared,frame_files=frame_files,state='prepared',status='Sequência preparada')
                    (job['folder']/'preparacao.json').write_text(json.dumps(prepared['info'],ensure_ascii=False,indent=2),encoding='utf-8')
                    self.send({'id':data['id'],'info':prepared['info'],
                               'originals':[f'/video-file/{data["id"]}/original_{i:02d}.png' for i in range(len(prepared['original_frames']))],
                               'frames':[f'/video-file/{data["id"]}/prepared_{i:02d}.png' for i in range(len(prepared['prepared_frames']))]})
                finally:LOCK.release()
            elif route=='/api/video/run':
                job=VIDEO_JOBS.get(data['id'])
                if not job or 'prepared' not in job:raise ValueError('Prepare a sequência antes de executar.')
                recipe=analysis.recipe(data.get('recipe'))
                if not LOCK.acquire(blocking=False):return self.send({'error':'Aguarde a operação atual do encoder.'},409)
                job.pop('result',None);job.update(state='running',status='Iniciando encoder',completed_blocks=0,recipe=recipe,notes=str(data.get('notes',''))[:5000])
                threading.Thread(target=video_run,args=(job,),daemon=True).start();self.send({'ok':True})
            elif route=='/api/prepare':
                if not LOCK.acquire(blocking=False): return self.send({'error':'Aguarde a operação atual do encoder.'},409)
                try: self.prepare(data)
                finally: LOCK.release()
            elif route=='/api/folder/start':
                self.send(FOLDER_UPLOADS.start(data['label'],data['files']))
            elif route=='/api/folder/file':
                raw=base64.b64decode(data['file'].split(',',1)[1],validate=True)
                self.send(FOLDER_UPLOADS.put(data['id'],data['path'],raw))
            elif route=='/api/folder/finish':
                self.send(FOLDER_UPLOADS.finish(data['id']))
            elif route=='/api/folder/cancel':
                self.send(FOLDER_UPLOADS.cancel(data['id']))
            elif route=='/api/batch/scan':
                self.send(batching.scan(str(data['folder'])))
            elif route=='/api/batch/start':
                self.send(batching.begin(data['scan_id'],data,LOCK))
            elif route=='/api/batch/stop':
                self.send(batching.stop(data['id']))
            elif route=='/api/run':
                job=JOBS.get(data['id'])
                if not job: raise ValueError('Prepare a imagem antes.')
                recipe=analysis.recipe(data.get('recipe'))
                if not LOCK.acquire(blocking=False): return self.send({'error':'Aguarde a operação atual do encoder.'},409)
                job.pop('result',None);job.pop('error',None)
                job.update(state='running',status='Iniciando o encoder',completed_blocks=0,
                           recipe=recipe,hypothesis=str(data.get('hypothesis',job.get('hypothesis','')))[:5000])
                threading.Thread(target=job_run,args=(job,),daemon=True).start();self.send({'ok':True})
            elif route=='/api/notebook':
                if not LOCK.acquire(blocking=False): return self.send({'error':'Aguarde a execução para abrir o caderno.'},409)
                try:
                    engine.liberar_encoder()
                    self.send({'url':notebook_url()})
                finally: LOCK.release()
            else: self.send({'error':'Rota inexistente.'},404)
        except Exception as e: self.send({'error':str(e),'details':traceback.format_exc()},400)

    def prepare(self,data):
                raw=base64.b64decode(data['image'].split(',',1)[1],validate=True)
                if len(raw)>20_000_000: raise ValueError('Use um arquivo de até 20 MB.')
                ident=uuid.uuid4().hex; folder=SESSIONS/ident;folder.mkdir()
                source=folder/'entrada.png'; source.write_bytes(raw)
                prepared=engine.preparar_imagem(source,int(data.get('limit',256)),data.get('variant','original'),data.get('background','#ffffff'))
                # Canônico RGB para leitura explícita no caderno; o arquivo de entrada mantém seus bytes originais.
                prepared['original'].save(folder/'original_rgb.png')
                prepared['original_rgba'].save(folder/'original_rgba.png')
                prepared['alpha'].save(folder/'alpha.png')
                prepared['preparada'].save(folder/'preparada.png')
                JOBS[ident]={'folder':folder,'prepared':prepared,'state':'prepared','status':'Imagem preparada',
                             'hypothesis':str(data.get('hypothesis',''))[:5000]}
                (SESSIONS/'latest.json').write_text(json.dumps({'image':str(source),'limit':int(data.get('limit',256)),
                   'variant':data.get('variant','original'),'background':data.get('background','#ffffff')},ensure_ascii=False),encoding='utf-8')
                self.send({'id':ident,'info':prepared['info'],'original':uri(prepared['original_rgba']),
                           'alpha':uri(prepared['alpha']),
                           'prepared':uri(prepared['preparada']),'pixel_sample':prepared['normalizada'][:,0,0].tolist()})

if __name__=='__main__':
    (ROOT/'.servidor.pid').write_text(str(os.getpid()),encoding='ascii')
    print(f'LAB_URL=http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
