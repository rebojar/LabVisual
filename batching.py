"""Lotes locais: leitura sequencial, resultados por imagem e interrupção cooperativa."""
from pathlib import Path
import json, uuid, time, threading, numpy as np
import engine, analysis

ROOT=Path(__file__).resolve().parent
BATCH_DIR=ROOT/'batches'
SCANS={}; BATCHES={}
EXTENSIONS={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}

def scan(folder):
    source=Path(folder).expanduser().resolve()
    if not source.is_dir(): raise ValueError('A pasta não foi encontrada. Confira o caminho.')
    files=sorted(p for p in source.rglob('*') if p.is_file() and not p.is_symlink()
                 and p.suffix.lower() in EXTENSIONS and p.resolve().is_relative_to(source))
    if not files: raise ValueError('Não encontrei imagens nos formatos aceitos nessa pasta.')
    if len(files)>5000: raise ValueError('Escolha uma pasta com até 5.000 imagens por lote.')
    ident=uuid.uuid4().hex
    SCANS[ident]={'source':source,'files':files}
    return {'id':ident,'folder':str(source),'count':len(files),
            'files':[{'index':i,'name':str(p.relative_to(source)),'bytes':p.stat().st_size} for i,p in enumerate(files)]}

def thumbnail(ident,index):
    s=SCANS[ident]; path=s['files'][index]
    image=engine.ler_rgba(path);image.thumbnail((100,80))
    return image

def save(job):
    data={k:v for k,v in job.items() if not k.startswith('_')}
    temp=job['_folder']/'registro.tmp'
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(job['_folder']/'registro.json')

def public(job):
    return {k:v for k,v in job.items() if not k.startswith('_')}

def get(ident):
    if ident in BATCHES: return BATCHES[ident]
    if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident): raise ValueError('Lote desconhecido.')
    folder=BATCH_DIR/ident
    job=json.loads((folder/'registro.json').read_text(encoding='utf-8'))
    job['_folder']=folder
    if job['state'] in ('running','stopping'):
        job['state']='interrupted';job['status']='O serviço foi encerrado. Os arquivos já salvos permanecem na pasta do lote.'
    return job

def latest():
    candidates=list(BATCH_DIR.glob('*/registro.json'))
    return get(max(candidates,key=lambda p:p.stat().st_mtime).parent.name) if candidates else None

def begin(scan_id, options, lock):
    s=SCANS.get(scan_id)
    if not s: raise ValueError('Confira a pasta novamente antes de iniciar.')
    # Valida antes de reservar o encoder ou criar saídas.
    limit=int(options.get('limit',256));variant=options.get('variant','original');background=options.get('background','#ffffff')
    if limit not in (0,256,384,512) or variant not in ('original','cinza'): raise ValueError('Condições inválidas.')
    engine.compor_fundo(engine.Image.new('RGBA',(1,1)),background)
    recipe = analysis.recipe(options.get('recipe'))
    if not lock.acquire(blocking=False): raise ValueError('Aguarde a operação atual antes de iniciar um lote.')
    try:
        ident=uuid.uuid4().hex;folder=BATCH_DIR/ident;folder.mkdir(parents=True)
        job={'id':ident,'state':'running','status':'Iniciando lote','folder_source':str(s['source']),
             'total':len(s['files']),'completed':0,'succeeded':0,'failed':0,'current':'',
             'completed_blocks':0,'options':{'limit':limit,'variant':variant,'background':background},
             'recipe':recipe, 'representation_schema':2,
             'started_at':time.strftime('%Y-%m-%dT%H:%M:%S'),'records':[],
             '_folder':folder,'_files':s['files'],'_stop':threading.Event()}
        BATCHES[ident]=job;save(job)
        threading.Thread(target=run,args=(job,lock),daemon=True).start()
        return public(job)
    except Exception:
        lock.release();raise

def run(job, lock):
    before=[];after=[];names=[]
    try:
        for index,path in enumerate(job['_files']):
            if job['_stop'].is_set(): break
            name=str(path.relative_to(Path(job['folder_source'])))
            job.update(current=name,status='Preparando imagem',completed_blocks=0)
            try:
                if path.stat().st_size>20_000_000: raise ValueError('Arquivo maior que 20 MB.')
                opts=job['options']
                prep=engine.preparar_imagem(path,opts['limit'],opts['variant'],opts['background'])
                def progress(label,n): job.update(status=label,completed_blocks=n)
                result=engine.executar_encoder(prep,progress,job['recipe'])
                vb=result['analysis']['before'];va=result['analysis']['after']
                if 'encoder' not in job:job['encoder']=result['info']['encoder']
                elif job['encoder'] != result['info']['encoder']:raise ValueError('O encoder mudou durante o lote.')
                np.savez_compressed(job['_folder']/f'imagem_{index+1:05d}.npz',
                   antes_merger=vb,depois_merger=va,receita_json=np.asarray(analysis.recipe_json(job['recipe'])))
                if prep['info']['tem_transparencia']:
                    prep['alpha'].save(job['_folder']/f'alpha_{index+1:05d}.png')
                before.append(vb);after.append(va);names.append(name)
                job['records'].append({'index':index,'name':name,'state':'ok','preparacao':prep['info'],
                                       'execucao':result['info'],'analysis':analysis.summary(result)})
                job['succeeded']+=1
                del prep,result
            except Exception as error:
                job['records'].append({'index':index,'name':name,'state':'error','error':str(error)})
                job['failed']+=1
            job['completed']+=1;save(job)
        if names:
            np.savez_compressed(job['_folder']/'embeddings.npz',
                arquivos=np.asarray(names),embedding_antes_merger=np.stack(before),
                embedding_depois_merger=np.stack(after),
                receita_json=np.asarray(analysis.recipe_json(job['recipe'])),
                encoder_json=np.asarray(json.dumps(job['encoder'],sort_keys=True)))
        stopped=job['_stop'].is_set() and job['completed']<job['total']
        job.update(state='stopped' if stopped else 'done',current='',
                   status='Interrompido após a imagem atual; resultados parciais salvos.' if stopped else 'Lote concluído.',
                   finished_at=time.strftime('%Y-%m-%dT%H:%M:%S'))
    except Exception as error:
        job.update(state='error',status=str(error))
    finally:
        try: save(job)
        finally: lock.release()

def stop(ident):
    job=BATCHES.get(ident)
    if not job or job['state'] not in ('running','stopping'): raise ValueError('Este lote não está em execução.')
    job['_stop'].set();job['state']='stopping';job['status']='Vai parar depois da imagem atual.'
    return public(job)
