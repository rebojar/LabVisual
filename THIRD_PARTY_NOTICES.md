# Créditos e componentes de terceiros

Este projeto utiliza o trabalho dos projetos abaixo. A referência a Qwen não implica vínculo oficial ou endosso de seus responsáveis.

## Escopo desta distribuição

O pacote contém o código da bancada, seus guias, testes e um caderno didático sem execuções salvas. Não inclui pesos, bibliotecas instaladas, binários, wheels, imagem Docker, fotografias, vídeos ou resultados experimentais. Os padrões geométricos de demonstração são gerados pelo próprio código.

O trabalho original da bancada é disponibilizado por Rebojar sob **AGPL-3.0-only**, conforme [LICENSE](LICENSE) e o aviso em [README.md](README.md). Essa escolha não substitui as licenças do checkpoint, das dependências ou dos arquivos que cada pessoa decide analisar. Este documento é um inventário de proveniência e termos identificados, não uma autorização para redistribuir qualquer componente sob uma licença única.

## Checkpoint

**Qwen/Qwen3.5-9B**, revisão `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, disponibilizado sob [Apache-2.0](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/LICENSE).

O usuário obtém os arquivos do repositório oficial. O extrator copia localmente os tensores `model.visual.*`, mantendo seus nomes e valores e registrando a origem. Essa separação de arquivos não torna os pesos um novo trabalho com licença própria da bancada. Para redistribuir pesos extraídos ou modificados, preserve os termos e avisos aplicáveis do checkpoint e identifique as alterações de empacotamento. Este pacote de código não redistribui esses pesos.

## Dependências diretas verificadas

As versões e declarações abaixo foram conferidas nos metadados e arquivos de licença das distribuições instaladas para o ensaio Windows de 20/09/2026. Os links apontam para os projetos responsáveis. Os avisos completos de cada distribuição continuam nos respectivos pacotes.

| Componente | Versão no ensaio | Licença identificada / observação | Uso |
|---|---|---|---|
| [PyAV](https://github.com/PyAV-Org/PyAV) | 18.1.0 | BSD-3-Clause para PyAV; FFmpeg e codecs têm termos próprios | Leitura de vídeo |
| [JupyterLab](https://github.com/jupyterlab/jupyterlab) | 4.6.3 | BSD-3-Clause; dependências incorporadas conservam seus avisos | Caderno interativo |
| [NumPy](https://github.com/numpy/numpy) | 2.5.2 | Distribuição declara `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | Vetores e matrizes |
| [Pillow](https://github.com/python-pillow/Pillow) | 12.3.0 | MIT-CMU | Imagens e GIFs |
| [Safetensors](https://github.com/huggingface/safetensors) | 0.8.0 | Apache-2.0 | Leitura dos pesos |
| [PyTorch](https://github.com/pytorch/pytorch) | 2.14.0+cpu | Distribuição declara `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT` | Inferência em CPU |
| [torchvision](https://github.com/pytorch/vision) | 0.29.0+cpu | BSD-3-Clause; distribuição binária pode incluir avisos adicionais | Dependência dos processadores visuais |
| [Transformers](https://github.com/huggingface/transformers) | 5.17.0 | Apache-2.0 | Arquitetura Qwen3.5 e processadores |

O interpretador Python é obtido separadamente e mantém os termos da [Python Software Foundation](https://docs.python.org/3/license.html). A bancada chama as APIs das bibliotecas; o pacote não incorpora cópias de suas implementações da arquitetura Qwen.

## Dependências transitivas e binários

As bibliotecas acima instalam outras dependências. O inventário privado do ambiente de validação registrou 116 distribuições, incluindo ferramentas do ambiente; todas tinham alguma evidência de licença em metadados ou arquivos de licença. Isso não significa que todos os componentes internos dos binários foram auditados nem que toda combinação futura foi aprovada.

Esta versão distribui código-fonte e instruções para que cada pessoa obtenha as bibliotecas separadamente. A tabela acima registra a proveniência e as licenças das dependências diretas verificadas para esta entrega; ela não pretende ser um inventário de binários que o projeto não está distribuindo.

Uma distribuição futura que inclua uma `.venv`, *wheels*, executável ou imagem Docker será outro artefato. Nesse caso, deverá ser produzido um inventário específico do pacote efetivamente distribuído, incluindo dependências incorporadas, avisos completos e eventuais obrigações de disponibilizar código-fonte. A revisão dessa entrega futura não está sendo apresentada como já concluída por este documento.

Em particular, a licença BSD do PyAV não resume os termos do FFmpeg. O FFmpeg informa LGPL-2.1-ou-posterior e componentes opcionais sob GPL que podem alterar a licença do conjunto compilado. As condições dependem da compilação distribuída. [Termos oficiais do FFmpeg](https://ffmpeg.org/legal.html).
