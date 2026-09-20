"""Escolhas analíticas da bancada, independentes dos pesos do encoder.

Agregação atua no eixo dos tokens; normalização atua no vetor resultante.
O merger aprendido pertence ao modelo e nunca é alterado por este módulo.
"""
import json
import numpy as np

DEFAULT = {'version': 1, 'pooling': 'mean', 'normalization': 'l2', 'metric': 'cosine'}
POOLING = {'mean': 'Média', 'max': 'Máximo', 'median': 'Mediana'}
NORMALIZATION = {'l2': 'L2', 'l1': 'L1', 'linf': 'L∞', 'none': 'Sem normalização'}
METRICS = {'cosine': 'Cosseno', 'euclidean': 'Distância euclidiana', 'dot': 'Produto escalar'}


def recipe(value=None):
    if value is None:
        return dict(DEFAULT)
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        raise ValueError('Receita inválida: use as escolhas disponíveis no painel.')
    result = {**DEFAULT, **value}
    if type(result['version']) is not int or result['version'] != 1:
        raise ValueError('Versão de receita não suportada.')
    for field, choices in [('pooling', POOLING), ('normalization', NORMALIZATION), ('metric', METRICS)]:
        if not isinstance(result[field], str) or result[field] not in choices:
            raise ValueError(f'Escolha de {field} não suportada.')
    return result


def description(value=None):
    r = recipe(value)
    return f"{POOLING[r['pooling']]} → {NORMALIZATION[r['normalization']]} → {METRICS[r['metric']]}"


def recipe_json(value):
    return json.dumps(recipe(value), sort_keys=True, ensure_ascii=False)


def aggregate(tokens, method='mean'):
    a = np.asarray(tokens)
    if a.ndim != 2 or 0 in a.shape or not np.issubdtype(a.dtype, np.number) or not np.isfinite(a).all():
        raise ValueError('São necessários todos os tokens finitos desta representação.')
    if method == 'mean':
        result = a.mean(axis=0)
    elif method == 'max':
        result = a.max(axis=0)
    elif method == 'median':
        result = np.median(a, axis=0)
    else:
        raise ValueError('Agregação desconhecida.')
    if not np.isfinite(result).all():
        raise ValueError('A agregação produziu valores não finitos.')
    return result


def normalize(vector, method='l2'):
    a = np.asarray(vector)
    if a.ndim != 1 or not a.size or not np.isfinite(a).all():
        raise ValueError('O vetor precisa ser finito e unidimensional.')
    if method == 'none':
        return a.copy(), 1.0
    if method not in ('l1', 'l2', 'linf'):
        raise ValueError('Normalização desconhecida.')
    # A precisão da extração é preservada; o divisor é calculado em float64.
    divisor = float(np.linalg.norm(a.astype(np.float64), ord={'l1': 1, 'l2': 2, 'linf': np.inf}[method]))
    if not np.isfinite(divisor) or divisor == 0:
        raise ValueError('Vetor nulo: não é possível normalizar seu comprimento.')
    result = a / divisor
    if not np.isfinite(result).all():
        raise ValueError('A normalização produziu valores não finitos.')
    return result, divisor


def represent(tokens, value=None):
    r = recipe(value)
    raw = aggregate(tokens, r['pooling'])
    vector, divisor = normalize(raw, r['normalization'])
    if r['metric'] == 'cosine' and not np.any(vector):
        raise ValueError('O cosseno não é definido para vetor nulo. Escolha outra receita.')
    return raw, vector, divisor


def analyze(before, after, value=None):
    r = recipe(value)
    b, vb, db = represent(before, r)
    a, va, da = represent(after, r)
    return {'recipe': r, 'before': vb, 'after': va, 'raw_before': b, 'raw_after': a,
            'divisors': {'before': db, 'after': da}}


def summary(result):
    a = result['analysis']
    return {'recipe': a['recipe'], 'description': description(a['recipe']),
            'dimensions': {'before': len(a['before']), 'after': len(a['after'])},
            'divisors': a['divisors'], 'comparison_scope': 'mesmo conjunto e mesmo estágio',
            'token_source': 'saídas completas do encoder; pesos preservados'}


def ranking(vectors, index, metric='cosine', k=5):
    a = np.asarray(vectors, dtype=np.float64)
    if a.ndim != 2 or 0 in a.shape or not np.isfinite(a).all() or not 0 <= index < len(a):
        raise ValueError('Conjunto de vetores inválido.')
    if metric == 'cosine':
        norms = np.linalg.norm(a, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError('Este conjunto contém vetor nulo; cosseno indisponível.')
        a = a / norms
        scores = np.clip(a @ a[index], -1, 1)
    elif metric == 'euclidean':
        scores = np.linalg.norm(a - a[index], axis=1)
    elif metric == 'dot':
        scores = a @ a[index]
    else:
        raise ValueError('Medida de comparação desconhecida.')
    if not np.isfinite(scores).all():
        raise ValueError('A comparação produziu valores não finitos.')
    eligible = np.flatnonzero(np.arange(len(a)) != index)
    order = scores if metric == 'euclidean' else -scores
    ranked = eligible[np.argsort(order[eligible], kind='stable')][:k]
    valid = scores[eligible]
    return {'neighbors': [{'index': int(i), 'similarity': float(scores[i]), 'score': float(scores[i])} for i in ranked],
            'metric': metric, 'label': METRICS[metric], 'higher_is_closer': metric != 'euclidean',
            'statistics': {'min': float(valid.min()), 'median': float(np.median(valid)),
                           'max': float(valid.max()), 'count': len(valid)} if len(valid) else None}


def squared_share(vectors, coordinate):
    a = np.asarray(vectors, dtype=np.float64)
    totals = np.square(a).sum(axis=-1)
    return np.divide(np.square(a[..., coordinate]), totals, out=np.zeros_like(totals), where=totals != 0)
