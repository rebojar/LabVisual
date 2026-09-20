"""Sequências visuais locais: decodificação, amostragem e encoder congelado."""
from pathlib import Path
import json, math, hashlib
import numpy as np
from PIL import Image
import engine

MAX_SECONDS = 60
MAX_FRAMES = 16

def inspect_media(path):
    path = Path(path)
    try:
        with Image.open(path) as im:
            if im.format != 'GIF':
                raise ValueError('Escolha um GIF ou um arquivo de vídeo.')
            count = im.n_frames
            if count > 20000 or im.width * im.height > 20_000_000:
                raise ValueError('GIF grande demais para este experimento.')
            durations = []
            fallback = 0
            for i in range(count):
                im.seek(i)
                ms = im.info.get('duration', 0)
                if ms <= 0:
                    ms = 100
                    fallback += 1
                durations.append(ms / 1000)
            return dict(kind='gif', width=im.width, height=im.height, frames=count,
                        duration=sum(durations), durations=durations,
                        timing_fallback_frames=fallback, audio_used=False)
    except (OSError, SyntaxError):
        pass
    import av
    with av.open(str(path)) as c:
        if not c.streams.video:
            raise ValueError('O arquivo não contém uma faixa de vídeo.')
        s = c.streams.video[0]
        duration = float(s.duration * s.time_base) if s.duration is not None else (c.duration or 0) / av.time_base
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('Não foi possível determinar a duração deste vídeo. Tente MP4 ou WebM.')
        if s.width * s.height > 20_000_000:
            raise ValueError('Use vídeo de até 20 milhões de pixels por quadro.')
        return dict(kind='video', width=s.width, height=s.height, duration=duration,
                    frames=s.frames or None, fps=float(s.average_rate) if s.average_rate else None,
                    audio_used=False)

def sample_frames(path, meta, start, end, count, background):
    if not all(math.isfinite(x) for x in (start, end)):
        raise ValueError('Informe tempos válidos.')
    if start < 0 or end <= start or end > meta['duration'] + .001:
        raise ValueError('O trecho deve estar dentro da duração do arquivo, com fim maior que início.')
    if end - start > MAX_SECONDS or end > 600:
        raise ValueError('Escolha até 60 segundos dentro dos primeiros 10 minutos.')
    if count < 2 or count > MAX_FRAMES or count % 2:
        raise ValueError('Escolha um número par de quadros, de 2 a 16.')
    # Intervalo [início, fim): nunca solicita um quadro além do final do arquivo.
    targets = np.linspace(start, end, count, endpoint=False).tolist()
    selected, timestamps, indices = [], [], []
    if meta['kind'] == 'gif':
        # GIF stores integer milliseconds; remove floating addition noise at boundaries.
        boundaries = np.round(np.cumsum([0] + meta['durations']), 9)
        wanted = np.clip(np.searchsorted(boundaries, targets, side='right') - 1, 0, meta['frames'] - 1)
        with Image.open(path) as im:
            for index in wanted:
                im.seek(int(index))
                selected.append(engine.compor_fundo(im.convert('RGBA'), background))
                timestamps.append(float(boundaries[index]))
                indices.append(int(index))
    else:
        import av
        with av.open(str(path)) as c:
            s = c.streams.video[0]
            origin = float((s.start_time or 0) * s.time_base)
            previous = None
            k = 0
            for i, frame in enumerate(c.decode(s)):
                if i > 100000:
                    raise ValueError('Vídeo longo demais para esta primeira versão.')
                if frame.time is None:
                    raise ValueError('O vídeo contém quadros sem marcação de tempo.')
                ts = max(0., float(frame.time) - origin)
                while k < count and targets[k] + 1e-9 < ts:
                    chosen, at, index = previous if previous is not None else (frame, ts, i)
                    selected.append(engine.compor_fundo(chosen.to_image().convert('RGBA'), background))
                    timestamps.append(at); indices.append(index); k += 1
                if k == count:
                    break
                previous = (frame, ts, i)
            while k < count and previous is not None:
                chosen, at, index = previous
                selected.append(engine.compor_fundo(chosen.to_image().convert('RGBA'), background))
                timestamps.append(at); indices.append(index); k += 1
        if len(selected) != count:
            raise ValueError('Não foi possível decodificar os quadros selecionados.')
    return selected, dict(requested_times=targets, timestamps=timestamps, frame_indices=indices,
                         repeated_samples=count-len(set(indices)), start=start, end=end)

def prepare(path, meta, options):
    import torch
    from transformers import Qwen3VLVideoProcessor
    count = int(options.get('count', 8))
    limit = int(options.get('limit', 192))
    if limit not in (128, 192, 256):
        raise ValueError('Resolução não permitida.')
    background = options.get('background', '#ffffff')
    frames, sampling = sample_frames(path, meta, float(options.get('start', 0)),
                                    float(options.get('end', min(meta['duration'], 4))), count, background)
    processor = Qwen3VLVideoProcessor.from_pretrained(str(engine.MODEL_DIR), local_files_only=True)
    video = torch.from_numpy(np.stack([np.asarray(f) for f in frames])).permute(0, 3, 1, 2)
    out = processor(videos=[video], do_sample_frames=False, return_tensors='pt',
                    size={'shortest_edge':4096, 'longest_edge':count*limit*limit},
                    cap_pixels_per_frame=False)
    pixels = out['pixel_values_videos']
    grid = out['video_grid_thw']
    t, h, w = grid[0].tolist()
    p, m, temporal = processor.patch_size, processor.merge_size, processor.temporal_patch_size
    if (p, m, temporal) != (16, 2, 2) or t * 2 != count:
        raise ValueError('Configuração temporal inesperada; verifique o processador.')
    # Inversão exata do patchify: mostra os pixels que realmente entram, em ordem temporal.
    normalized = pixels.reshape(t,h//m,w//m,m,m,3,temporal,p,p).permute(0,6,5,1,3,7,2,4,8).reshape(count,3,h*p,w*p)
    mean = torch.tensor(processor.image_mean)[None,:,None,None]
    std = torch.tensor(processor.image_std)[None,:,None,None]
    rgb = ((normalized*std+mean)*255).round().clamp(0,255).byte().permute(0,2,3,1).numpy()
    previews = [Image.fromarray(a) for a in rgb]
    info = dict(type='video', source=meta, **sampling, sampled_frames=count, temporal_pairs=t,
                prepared_wh=[w*p,h*p], pixel_values_shape=list(pixels.shape), grid_thw=[t,h,w],
                processor=processor.__class__.__name__, background=background,
                pixel_budget_per_frame=limit*limit, sampling='uniforme no tempo; quadro ativo em cada instante',
                input_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                note='Sequência amostrada; não contém áudio. Cada par reúne dois quadros selecionados.',
                expected_after_tokens=t*h*w//4)
    return {'inputs':{'pixel_values':pixels,'image_grid_thw':grid},'info':info,
            'original_frames':frames,'prepared_frames':previews}

def execute(prepared, progress=None, recipe=None):
    result = engine.executar_encoder(prepared, progress, recipe)
    return reanalyze(result, prepared, recipe)

def reanalyze(result, prepared, recipe=None):
    import analysis
    result = engine.reanalisar(result, recipe)
    t, h, w = prepared['info']['grid_thw']
    means = result['depois'].reshape(t,h*w//4,-1).mean(axis=1)
    norms = np.linalg.norm(means,axis=1,keepdims=True)
    # Saída histórica preservada para cadernos existentes.
    result['pair_vectors'] = means / np.maximum(norms,1e-12)
    r = result['analysis']['recipe']
    result['analysis_pairs'] = {}
    result['temporal_comparisons'] = {}
    for stage, key, count in [('before','antes',h*w), ('after','depois',h*w//4)]:
        pairs = result[key].reshape(t,count,-1)
        vectors = np.stack([analysis.represent(pair,r)[1] for pair in pairs])
        result['analysis_pairs'][stage] = vectors
        result['temporal_comparisons'][stage] = [
            analysis.ranking(vectors[i:i+2],0,r['metric'],1)['neighbors'][0]['score'] for i in range(t-1)]
    result['info']['temporal_pairs'] = t
    return result
