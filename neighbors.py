"""Consulta de vetores salvos. Não carrega o encoder nem modifica representações."""
from pathlib import Path
import json, re, numpy as np
import analysis
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parent
CACHE={}

def sources():
    found=[]
    for kind,base in [('terminal',ROOT/'imports'),('batch',ROOT/'batches')]:
        for p in sorted(base.glob('*/embeddings.npz'),key=lambda p:p.stat().st_mtime,reverse=True):
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',p.parent.name):continue
            record=p.parent/'registro.json'
            if not record.exists():continue
            meta=json.loads(record.read_text(encoding='utf-8'))
            found.append({'id':kind+'_'+p.parent.name,'label':meta.get('label',f"Lote da interface · {meta.get('succeeded','?')} imagens · {meta.get('started_at','').replace('T',' ')}"),'path':p,'meta':meta,'kind':kind})
    return found

def dataset(ident):
    entry=next((s for s in sources() if s['id']==ident),None)
    if entry is None:raise ValueError('Conjunto não encontrado. Atualize a lista.')
    stamp=(entry['path'].stat().st_mtime_ns,(entry['path'].parent/'registro.json').stat().st_mtime_ns)
    cached=CACHE.get(ident)
    if cached and cached['stamp']==stamp:return cached
    with np.load(entry['path'],allow_pickle=False) as saved:
        names=saved['arquivos'].tolist()
        if not names or len(set(names))!=len(names):raise ValueError('Nomes ausentes ou repetidos no conjunto.')
        legacy=entry['meta'].get('representation_schema',1)==1
        r=analysis.recipe(entry['meta'].get('recipe'))
        if legacy and r != analysis.DEFAULT:raise ValueError('Receita ausente ou incompatível no conjunto antigo.')
        if not legacy:
            if entry['meta'].get('representation_schema') != 2:raise ValueError('Formato de lote desconhecido.')
            if 'receita_json' not in saved or analysis.recipe(json.loads(str(saved['receita_json'].item()))) != r:
                raise ValueError('A receita dos vetores difere do registro. Não é seguro comparar este conjunto.')
            if 'encoder_json' not in saved or json.loads(str(saved['encoder_json'].item())) != entry['meta'].get('encoder'):
                raise ValueError('A identidade do encoder difere do registro do lote.')
        arrays=[]
        for key,dim in [('embedding_antes_merger',1152),('embedding_depois_merger',4096)]:
            a=np.array(saved[key],dtype=np.float64)
            if a.ndim!=2 or a.shape[0]!=len(names) or a.shape[1]==0 or not np.isfinite(a).all():raise ValueError('Formato de vetores inválido.')
            if legacy and a.shape[1]!=dim:raise ValueError('O conjunto antigo não corresponde ao Qwen esperado.')
            arrays.append(a)
        if not legacy:
            expected={'before':arrays[0].shape[1],'after':arrays[1].shape[1]}
            records=[item for item in entry['meta'].get('records',[]) if item.get('state')=='ok']
            if len(records)!=len(names) or any(item.get('analysis',{}).get('recipe')!=r or item.get('analysis',{}).get('dimensions')!=expected for item in records):
                raise ValueError('O conjunto mistura receitas ou dimensões incompatíveis.')
    source=Path(entry['meta']['folder_source']).resolve()
    paths=[]
    for name in names:
        p=(source/name).resolve()
        if not p.is_relative_to(source):raise ValueError('Nome de imagem fora da pasta do conjunto.')
        paths.append(p)
    cached={**entry,'stamp':stamp,'names':names,'paths':paths,'before':arrays[0],'after':arrays[1],
            'recipe':r,'legacy':legacy}
    CACHE[ident]=cached
    return cached

def public_dataset(d):
    if d['kind']=='terminal':conditions=d['meta']['conditions']
    else:
        opts=d['meta']['options'];limit=opts['limit']
        conditions=f"Resolução: {'limites do checkpoint' if limit==0 else str(limit*limit)+' pixels de orçamento'} · {'cores originais' if opts['variant']=='original' else 'tons de cinza'} · fundo {opts['background']}."
    peak=None
    if d['after'].shape[1]>3994:
        v=d['after'][:,3994]
        peak={'coordinate':3995,'count':int((abs(d['after']).argmax(axis=1)==3994).sum()),
              'min':float(v.min()),'median':float(np.median(v)),'max':float(v.max()),
              'median_squared_share':float(np.median(analysis.squared_share(d['after'],3994)))}
    return {'id':d['id'],'label':d['label'],'count':len(d['names']),'names':d['names'],'conditions':conditions,
        'peak':peak,'recipe':d['recipe'],'legacy':d['legacy'],
        'dimensions':{'before':d['before'].shape[1],'after':d['after'].shape[1]},
        'method':analysis.description(d['recipe'])+'. Comparação em float64 sobre os vetores salvos; não recupera precisão perdida. A própria imagem é excluída; empates exatos seguem a ordem dos arquivos.'+(' Receita histórica presumida: este conjunto foi criado antes do registro de metodologia.' if d['legacy'] else '')}

def ranking(vectors,index,k=5,metric='cosine'):
    return analysis.ranking(vectors,index,metric,k)

def compare(ident,index):
    d=dataset(ident)
    if not 0<=index<len(d['names']):raise ValueError('Escolha uma imagem válida na galeria.')
    before=ranking(d['before'],index,metric=d['recipe']['metric']);after=ranking(d['after'],index,metric=d['recipe']['metric'])
    common=sorted(set(x['index'] for x in before['neighbors'])&set(x['index'] for x in after['neighbors']))
    for result in (before,after):
        for row in result['neighbors']:row.update(name=d['names'][row['index']],common=row['index'] in common)
    v=float(d['after'][index,3994]) if d['after'].shape[1]>3994 else None
    share=float(analysis.squared_share(d['after'][index],3994)) if v is not None else None
    return {'dataset':ident,'index':index,'name':d['names'][index],'before':before,'after':after,'common':common,
            'coordinate3995':v,'squared_share3995':share,'recipe':d['recipe'],'legacy':d['legacy']}

def thumbnail(ident,index):
    d=dataset(ident)
    if not 0<=index<len(d['names']):raise ValueError('Imagem inexistente.')
    with Image.open(d['paths'][index]) as im:
        if im.width*im.height>20_000_000:raise ValueError('Imagem grande demais para miniatura.')
        im=ImageOps.exif_transpose(im).convert('RGBA')
        # Mostra a mesma composição RGB das condições do lote quando conhecidas.
        if d['kind']=='batch':
            opts=d['meta']['options'];im=Image.alpha_composite(Image.new('RGBA',im.size,opts['background']),im).convert('RGB')
            if opts['variant']=='cinza':im=ImageOps.grayscale(im).convert('RGB')
        else:im=im.convert('RGB')
        im.thumbnail((560,420))
        return im
