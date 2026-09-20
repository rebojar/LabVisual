# Instalação local

Este guia instala a bancada para **CPU**. Não é necessário instalar CUDA ou executar um modelo de linguagem. O checkpoint e as bibliotecas são obtidos separadamente do código.

## 1. Escolha uma pasta curta e confira o Python

Extraia o código em uma pasta curta, por exemplo `D:\lab-qwen`. Evite várias subpastas dentro de diretórios sincronizados: duas tentativas de validação falharam pelo comprimento dos caminhos de dependências no Windows. A instalação funcionou ao encurtar a pasta, sem alterar o registro do sistema.

Use **Python 3.12 de 64 bits**. Os ensaios usaram 3.12.14; instalar o próprio Python do zero não fez parte dos testes. Para obter um interpretador, consulte a [distribuição oficial do Python](https://www.python.org/downloads/windows/). Não instale vários interpretadores para tentar corrigir uma biblioteca ausente.

No Windows, abra um CMD dentro da pasta do código e confira:

```bat
py -3.12 --version
py -3.12 -c "import struct; print(struct.calcsize('P') * 8)"
```

O segundo comando deve mostrar `64`. Se `py` não existir, isso pode significar que o lançador não está instalado. Confira `python --version` e, se for 3.12, use `python` no lugar de `py -3.12` nas duas verificações e na criação do ambiente abaixo. Outra opção é usar o caminho completo do `python.exe` instalado. O erro de `py` sozinho não prova que o Python está ausente.

## 2. Instale as bibliotecas no ambiente do projeto

Windows / CMD:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip --isolated install --no-cache-dir --only-binary=:all: --no-compile --index-url https://download.pytorch.org/whl/cpu torch==2.14.0+cpu torchvision==0.29.0+cpu
.venv\Scripts\python.exe -m pip --isolated install --no-cache-dir --only-binary=:all: --no-compile --index-url https://pypi.org/simple -r requirements.txt
.venv\Scripts\python.exe -m pip check
```

Não é preciso ativar o ambiente: cada comando usa seu executável explicitamente. Instalar a variante `+cpu` primeiro evita baixar uma variante voltada a outro dispositivo. As versões base em `requirements.txt` aceitam essa variante local. Os downloads exigem internet; a inferência usa os pesos locais.

Linux, com Python 3.12 e suporte a `venv` já disponíveis:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip --isolated install --no-cache-dir --only-binary=:all: --no-compile --index-url https://download.pytorch.org/whl/cpu torch==2.14.0+cpu torchvision==0.29.0+cpu
.venv/bin/python -m pip --isolated install --no-cache-dir --only-binary=:all: --no-compile --index-url https://pypi.org/simple -r requirements.txt
.venv/bin/python -m pip check
```

O Linux foi validado em container Debian Bookworm, em CPU. O uso de uma distribuição Linux de desktop é uma extrapolação desse ensaio, não outro teste já realizado. macOS, GPU e outras versões de Python não foram validados. Para outras variantes, consulte o [PyTorch](https://pytorch.org/get-started/locally/) e faça uma nova validação.

## 3. Obtenha somente os arquivos necessários do modelo

Crie uma pasta **fora do código**, por exemplo `D:\modelos\qwen35-visual`. Na revisão fixa `c202236235762e1c871ad0ccb60c8ee5ba337b9a` do repositório oficial, baixe:

- [config.json](https://huggingface.co/Qwen/Qwen3.5-9B/resolve/c202236235762e1c871ad0ccb60c8ee5ba337b9a/config.json)
- [preprocessor_config.json](https://huggingface.co/Qwen/Qwen3.5-9B/resolve/c202236235762e1c871ad0ccb60c8ee5ba337b9a/preprocessor_config.json)
- [video_preprocessor_config.json](https://huggingface.co/Qwen/Qwen3.5-9B/resolve/c202236235762e1c871ad0ccb60c8ee5ba337b9a/video_preprocessor_config.json)
- [model.safetensors-00004-of-00004.safetensors](https://huggingface.co/Qwen/Qwen3.5-9B/resolve/c202236235762e1c871ad0ccb60c8ee5ba337b9a/model.safetensors-00004-of-00004.safetensors)

Guarde também a [licença dos pesos](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/LICENSE) junto dessa pasta. Os quatro arquivos técnicos bastam para a extração; os outros shards do modelo textual não são usados.

O shard ocupa aproximadamente 3,33 GB. A extração cria mais cerca de 912 MB de pesos visuais: reserve pelo menos 4,5 GB nessa pasta, além do ambiente Python, dos downloads e dos seus experimentos. RAM e espaço em disco são medidas diferentes. Consulte as condições medidas em [VALIDATION.md](VALIDATION.md).

No CMD, a partir da pasta do código:

```bat
.venv\Scripts\python.exe tools\extract_visual.py "D:\modelos\qwen35-visual"
```

No Linux, use `.venv/bin/python tools/extract_visual.py /caminho/da/pasta/do/modelo`.

O extrator valida o SHA-256 do shard e copia os 333 tensores visuais byte a byte. Ele cria `Qwen3.5-9B-Vision-BF16.safetensors` e `verificacao_encoder_visual.json`, sem alterar os pesos de origem. Não sobrescreve um resultado ou arquivo parcial já existente; se houver uma tentativa anterior, examine-a antes de repetir a extração.

## 4. Configure a pasta dos pesos

Copie `config-local.example.json` para `config-local.json` na pasta do código. Edite apenas o valor de `model_dir`, por exemplo:

```json
{
  "model_dir": "D:/modelos/qwen35-visual"
}
```

As barras `/` evitam a necessidade de duplicar barras invertidas no JSON. Salve em UTF-8 sem BOM. O arquivo é local e ignorado pelo Git. A variável `QWEN35_MODEL_DIR`, se definida, tem prioridade sobre ele.

## 5. Abra e faça o primeiro experimento

No Windows, dê dois cliques em **Abrir_bancada.cmd**. No Linux, execute `.venv/bin/python launcher.py`. Abra o endereço local mostrado, normalmente `http://127.0.0.1:8765/`.

1. Na aba **Uma imagem**, escolha **Usar padrão geométrico de teste**.
2. Clique em **Preparar imagem**. Confira imagem e patches: essa etapa não executa o encoder.
3. Clique em **Executar minha imagem**. Aguarde as representações antes e depois do merger.
4. Abra o caderno pela própria interface, quando desejar. Evite inferências simultâneas na interface e no caderno.

Não há pesos, fotografias ou resultados privados no pacote. Os padrões didáticos são gerados pelo código. O primeiro carregamento pode demorar mais. Use imagens pequenas antes de testar lotes ou vídeos longos.

## Problemas comuns

| Situação | O que verificar |
|---|---|
| `Python local indisponivel` | A criação de `.venv` terminou? O executável deve existir em `.venv\Scripts\python.exe`. O atalho não instala Python ou bibliotecas. |
| Erro de arquivo/caminho durante a instalação | Encurte a pasta e recrie o ambiente nela. Não mova uma `.venv` já criada: ambientes virtuais dependem de caminhos locais. |
| Não encontrou o encoder | Confira `config-local.json`, a variável de ambiente e o nome do arquivo extraído. |
| Conexão recusada | O servidor está encerrado ou falhou ao iniciar. Reabra o atalho e consulte `.servidor.log` localmente. |
| Porta ocupada por outra bancada | Encerre a outra instância ou defina `QWEN35_PORT` antes de iniciar. São usadas também as portas base + 1 (caderno) e base + 4 (vizinhos). |
| Vídeo original não reproduz, mas os quadros aparecem | O suporte do player depende do navegador e do codec. A preparação usa o leitor Python; veja o [guia de uso](GUIA_DE_USO.md#vídeo-e-gif). |

Fechar a aba não encerra os processos do servidor. Para uso com encerramento explícito, execute o servidor em um terminal e finalize-o com Ctrl+C; o serviço de vizinhos e um Jupyter já aberto são processos separados. Não encerre todos os processos Python do computador indiscriminadamente.

Os dados de experimentos permanecem em disco até serem removidos por você. Não publique a pasta de uso cotidiano inteira: siga [CONTRIBUTING.md](CONTRIBUTING.md) e [SECURITY.md](SECURITY.md).
