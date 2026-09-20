"""Motor compartilhado pela tela e pelo caderno. Somente inferência local."""
from pathlib import Path
import json, hashlib, time, gc, re, os
import numpy as np
from PIL import Image, ImageOps
import analysis

ROOT = Path(__file__).resolve().parent

def diretorio_modelo():
    """Lê uma escolha local; o modelo nunca faz parte do pacote de código."""
    local = ROOT / 'config-local.json'
    valor = os.environ.get('QWEN35_MODEL_DIR')
    if not valor and local.exists():
        valor = json.loads(local.read_text(encoding='utf-8')).get('model_dir')
    return Path(valor).expanduser().resolve() if valor else ROOT / 'modelo-nao-configurado'

MODEL_DIR = diretorio_modelo()
_model = None
_identity = None

def identidade_modelo():
    """Registra a identidade dos arquivos sem incluir caminhos pessoais."""
    global _identity
    if _identity is None:
        hashes = {}
        for name in ('config.json', 'preprocessor_config.json', 'video_preprocessor_config.json',
                     'Qwen3.5-9B-Vision-BF16.safetensors'):
            h = hashlib.sha256()
            with (MODEL_DIR/name).open('rb') as source:
                for block in iter(lambda: source.read(8*1024*1024), b''):
                    h.update(block)
            hashes[name] = h.hexdigest()
        _identity = {'adapter': 'qwen3.5-9b-v1', 'checkpoint': 'Qwen/Qwen3.5-9B', 'files_sha256': hashes}
    return _identity

def ler_rgba(caminho):
    """Preserva a opacidade original, inclusive transparência de imagens indexadas."""
    with Image.open(caminho) as im:
        if im.width * im.height > 20_000_000:
            raise ValueError('Use uma imagem de até 20 milhões de pixels neste primeiro teste.')
        im = ImageOps.exif_transpose(im)
        return im.convert('RGBA')

def compor_fundo(rgba, fundo='#ffffff'):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', fundo):
        raise ValueError('Escolha uma cor de fundo no formato #RRGGBB.')
    return Image.alpha_composite(Image.new('RGBA',rgba.size,fundo),rgba).convert('RGB')

def abrir_imagem(caminho, fundo='#ffffff'):
    """Abre em RGB compondo a transparência sobre a cor de fundo escolhida."""
    return compor_fundo(ler_rgba(caminho),fundo)

def preparar_imagem(caminho, limite=256, variante='original', fundo='#ffffff'):
    """Usa o processador local do checkpoint. Limite é a raiz do orçamento de pixels."""
    import torch
    from transformers import AutoImageProcessor
    if limite not in (0, 256, 384, 512):
        raise ValueError('Limite permitido: 0 (checkpoint), 256, 384 ou 512.')
    if variante not in ('original', 'cinza'):
        raise ValueError('Variante desconhecida.')
    rgba = ler_rgba(caminho)
    alpha = rgba.getchannel('A')
    opacidade = np.asarray(alpha)
    original = compor_fundo(rgba,fundo)
    usada = ImageOps.grayscale(original).convert('RGB') if variante == 'cinza' else original.copy()
    processor = AutoImageProcessor.from_pretrained(str(MODEL_DIR), local_files_only=True)
    # O limite de pixels é explícito. Não é um recorte nem força uma imagem quadrada.
    limites = {'min_pixels':256*256,'max_pixels':limite*limite} if limite else {}
    inputs = processor(images=usada, return_tensors='pt', **limites)
    config_pre = json.loads((MODEL_DIR/'preprocessor_config.json').read_text(encoding='utf-8'))
    minimo = limites.get('min_pixels',config_pre['size']['shortest_edge'])
    maximo = limites.get('max_pixels',config_pre['size']['longest_edge'])
    pixels = inputs['pixel_values']
    temporal, gh, gw = inputs['image_grid_thw'][0].tolist()
    p, m, t = processor.patch_size, processor.merge_size, processor.temporal_patch_size
    if temporal != 1 or p != 16 or m != 2 or t != 2:
        raise ValueError('O formato do processador mudou; a reconstrução visual precisa ser revisada.')
    # Desfaz somente a organização dos patches para mostrar a entrada real em RGB.
    # A imagem estática foi repetida no eixo temporal. Exibimos a primeira cópia.
    blocos = pixels.reshape(gh//m, gw//m, m, m, 3, t, p, p)
    normalizada = blocos[:, :, :, :, :, 0, :, :].permute(4,0,2,5,1,3,6).reshape(3,gh*p,gw*p)
    media = torch.tensor(processor.image_mean)[:,None,None]
    desvio = torch.tensor(processor.image_std)[:,None,None]
    rgb = ((normalizada*desvio+media)*255).round().clamp(0,255).byte().permute(1,2,0).numpy()
    preparada = Image.fromarray(rgb)
    return {'original':original, 'original_rgba':rgba, 'alpha':alpha,
            'preparada':preparada, 'inputs':inputs,
            'normalizada':normalizada, 'info':{
                'original_wh':list(original.size), 'preparada_wh':list(preparada.size),
                'pixel_values_shape':list(pixels.shape), 'grid_thw':[temporal,gh,gw],
                'patch_size':p, 'merge_size':m, 'temporal_patch_size':t,
                'dtype':str(pixels.dtype), 'intervalo':[float(pixels.min()),float(pixels.max())],
                'image_mean':processor.image_mean, 'image_std':processor.image_std,
                'processor':processor.__class__.__name__, 'max_pixels':maximo,
                'min_pixels':minimo, 'variante':variante, 'fundo_rgb':fundo.lower(),
                'perfil_resolucao':'checkpoint' if limite==0 else 'orcamento',
                'pixels_preparados':preparada.width*preparada.height,
                'tem_transparencia':bool((opacidade<255).any()),
                'percentual_transparente':round(float((opacidade==0).mean()*100),4),
                'percentual_semitransparente':round(float(((opacidade>0)&(opacidade<255)).mean()*100),4),
                'alpha_enviado_ao_encoder':False,
                'input_sha256':hashlib.sha256(Path(caminho).read_bytes()).hexdigest()}}

def carregar_encoder(progresso=None):
    """Reconstrói só a torre visual; carrega TODOS os pesos com strict=True."""
    global _model
    if _model is not None:
        return _model
    import torch
    from transformers import Qwen3_5VisionConfig, Qwen3_5VisionModel
    from safetensors.torch import load_file
    torch.set_num_threads(4)
    cfg = json.loads((MODEL_DIR/'config.json').read_text(encoding='utf-8'))['vision_config']
    if progresso: progresso('Montando a torre visual na CPU',0)
    # FP32 na CPU. O arquivo BF16 permanece intacto; valores BF16 cabem exatamente em FP32.
    modelo = Qwen3_5VisionModel(Qwen3_5VisionConfig(**cfg))
    if progresso: progresso('Carregando os 333 tensores',0)
    pesos = load_file(str(MODEL_DIR/'Qwen3.5-9B-Vision-BF16.safetensors'), device='cpu')
    pesos = {k.removeprefix('model.visual.'):v for k,v in pesos.items()}
    modelo.load_state_dict(pesos, strict=True)
    del pesos
    modelo.eval()
    modelo.requires_grad_(False)
    _model = modelo
    return modelo

def executar_encoder(preparacao, progresso=None, receita=None):
    """Executa uma imagem, sem gradientes e sem atualizar nenhum peso."""
    receita = analysis.recipe(receita)
    import torch, transformers, safetensors
    inicio = time.perf_counter()
    modelo = carregar_encoder(progresso)
    carregado = time.perf_counter()
    entradas = preparacao['inputs']
    hooks = []
    if progresso:
        for i,bloco in enumerate(modelo.blocks):
            hooks.append(bloco.register_forward_hook(lambda _m,_i,_o,n=i+1: progresso(f'Bloco visual {n} de 27 concluído',n)))
    try:
        with torch.inference_mode():
            saida = modelo(hidden_states=entradas['pixel_values'].to(dtype=modelo.dtype),
                           grid_thw=entradas['image_grid_thw'])
    finally:
        for h in hooks: h.remove()
    antes = saida.last_hidden_state.detach().float().cpu().numpy()
    depois = saida.pooler_output.detach().float().cpu().numpy()
    if not np.isfinite(antes).all() or not np.isfinite(depois).all():
        raise ValueError('A saída contém valores não finitos; não será apresentada como um teste válido.')
    # Esta média é uma ESCOLHA DA BANCADA, não uma classificação nem uma saída textual.
    vetor = depois.mean(axis=0)
    norma = float(np.linalg.norm(vetor))
    unitario = vetor/norma if norma else np.zeros_like(vetor)
    result = {'antes':antes, 'depois':depois, 'vetor_medio':vetor, 'vetor_unitario':unitario,
            'info':{'antes_shape':list(antes.shape),'depois_shape':list(depois.shape),
                    'vetor_shape':list(vetor.shape),'norma_media':norma,
                    'parametros':sum(p.numel() for p in modelo.parameters()),
                    'dtype_execucao':str(modelo.dtype),'dispositivo':'cpu',
                    'gradientes':False,'treinamento':False,'pesos_ausentes':0,'pesos_inesperados':0,
                    'encoder':identidade_modelo(),
                    'tempo_carregamento_s':round(carregado-inicio,3),
                    'tempo_inferencia_s':round(time.perf_counter()-carregado,3),
                    'versoes':{'torch':torch.__version__,'transformers':transformers.__version__,
                               'safetensors':safetensors.__version__}}}
    return reanalisar(result, receita)

def reanalisar(resultado, receita=None):
    """Reutiliza os tokens completos; não prepara pixels nem executa o encoder."""
    return {**resultado, 'analysis': analysis.analyze(resultado['antes'], resultado['depois'], receita)}

def liberar_encoder():
    global _model
    _model = None
    gc.collect()

def salvar_resultado(resultado, destino):
    """Salva todos os tokens e os dois vetores; não só o gráfico da tela."""
    a = resultado['analysis']
    np.savez_compressed(destino, antes_merger=resultado['antes'], depois_merger=resultado['depois'],
                        media_depois_merger=resultado['vetor_medio'], unitario_depois_merger=resultado['vetor_unitario'],
                        agregado_analise_antes=a['raw_before'], agregado_analise_depois=a['raw_after'],
                        vetor_analise_antes=a['before'], vetor_analise_depois=a['after'],
                        receita_json=np.asarray(analysis.recipe_json(a['recipe'])),
                        proveniencia_json=np.asarray(json.dumps(resultado['info'], ensure_ascii=False)))
