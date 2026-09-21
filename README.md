# LabVisual

💠 Ambiente local e aberto, com ferramentas para observar, experimentar, inspecionar e documentar representações visuais de modelos. 💠

## Primeira bancada

🔹 **Bancada Visual do Qwen3.5-9B:** ferramenta local para preparar imagens e sequências e explorar representações da torre visual do Qwen3.5-9B, com os pesos congelados.

A bancada executa **somente a torre visual** do checkpoint `Qwen/Qwen3.5-9B`. O encoder permanece congelado: **não houve treinamento, ajuste fino ou LoRA**. Os gráficos e vizinhos não são classes, interpretações semânticas nem medidas de compreensão.

Esta versão usa um checkpoint específico. A pasta dos pesos pode variar entre computadores, mas trocar por outro modelo ou encoder exige adaptar o código e validar novamente processador, arquitetura e resultados.

**Quer instalar e usar a bancada? [Vá direto para “Comece por aqui”.](#comece-por-aqui)**

**Quer conhecer antes de instalar? [Abra a demonstração pública no Rebojar.](https://rebojar.github.io/demonstracao-labvisual/)**

## Demonstração pública · interface sugerida

A [demonstração pública](https://rebojar.github.io/demonstracao-labvisual/) apresenta uma execução sintética pré-calculada em uma interface estática e interativa. Ela não executa o modelo, não recebe arquivos, não inicia um servidor local e não acessa o computador de quem a visita.

Essa página é uma **interface pública sugerida** para apresentar alguns resultados da bancada. Não é um módulo obrigatório do LabVisual, não substitui a bancada instalável e não reproduz todos os seus recursos. O [código da demonstração](https://github.com/rebojar/rebojar.github.io/tree/main/demonstracao-labvisual) fica no repositório do Rebojar e pode servir como referência para outras adaptações visuais.

## O que pertence a esta pasta

O código da interface, do servidor local, do extrator dos pesos visuais e do caderno `Experimento_visual.ipynb`, acompanhado dos guias e testes. Esse caderno combina explicações com células de código Python executáveis e abre no [JupyterLab](https://jupyterlab.readthedocs.io/en/stable/), uma aplicação local acessada pelo navegador. A instalação descrita em [INSTALL.md](INSTALL.md) instala o JupyterLab no ambiente do projeto; não é necessário tê-lo instalado previamente.

As entradas e saídas de experimentos são produzidas localmente em:
- `sessions/`,
- `batches/`,
- `videos/`
- e `imports/`.
Essas pastas não fazem parte do pacote. Este primeiro pacote de código também não inclui pesos, arquivos de imagem ou vídeo, resultados de experimentos, ambiente Python nem configuração local. Os arquivos destinados à demonstração pública do Rebojar formam uma seleção separada, com revisão própria.

Ao abrir o caderno, a bancada cria um **token temporário do Jupyter**: uma senha aleatória incluída na URL para restringir o acesso àquela execução local. Não é um token do modelo nem do Hugging Face, não representa os tokens visuais produzidos pelo encoder e não fica gravado neste repositório.

## Modelo e implementação exatos usados

- Modelo exato usado e validado: [Qwen/Qwen3.5-9B no Hugging Face](https://huggingface.co/Qwen/Qwen3.5-9B/tree/c202236235762e1c871ad0ccb60c8ee5ba337b9a), na revisão fixa `c202236235762e1c871ad0ccb60c8ee5ba337b9a`.
- Arquivos usados: `config.json`, `preprocessor_config.json`, `video_preprocessor_config.json` e `model.safetensors-00004-of-00004.safetensors`. O quarto shard oficial tem SHA-256 `b62b0c4cd7e44edee103ee8f4fe225f246d5e768e07bfd5f25b63a8aa1fdd0c6`.
- A implementação da arquitetura usada pela bancada vem da versão testada **Transformers 5.17.0**, especificamente do [módulo Qwen3.5 dessa versão](https://github.com/huggingface/transformers/blob/v5.17.0/src/transformers/models/qwen3_5/modeling_qwen3_5.py), não de código copiado do repositório de pesos.
- O checkpoint oficial declara [licença Apache 2.0](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/LICENSE). Os pesos conservam essa licença; o código da bancada é disponibilizado sob AGPLv3, conforme a seção abaixo.

> **Recorte visual e armazenamento:** o checkpoint completo ocupa aproximadamente **19,3 GB** e é distribuído em quatro arquivos grandes, chamados *shards*. Esta bancada baixa somente o quarto shard, de aproximadamente **3,33 GB**, porque é nele que estão os pesos da torre visual usados aqui.

O extrator confere esse arquivo oficial e copia, sem alterá-los, os 333 tensores cujos nomes começam por `model.visual.*` para um arquivo local menor chamado `Qwen3.5-9B-Vision-BF16.safetensors`, de aproximadamente **912 MB**. Isso é somente uma extração: não modifica nem treina os pesos. Durante a extração, o shard baixado e o arquivo extraído coexistem no disco; por isso, o guia recomenda reservar pelo menos 4,5 GB nessa pasta.

O arquivo de 912 MB é produzido localmente; ele não é um shard adicional para download. O recorte reduz o download necessário e evita carregar os pesos textuais não usados durante a execução. Por isso, não é preciso baixar os outros três shards: `model.safetensors-00001-of-00004.safetensors`, `model.safetensors-00002-of-00004.safetensors` e `model.safetensors-00003-of-00004.safetensors`.

## Comece por aqui

**Instalação validada com dependências novas em Windows nativo e Linux/Docker, na CPU.** Em cada ambiente passaram 51 verificações funcionais e 14 células do caderno. O Windows reutilizou um Python 3.12.14 x64 existente; isso não comprova a instalação do próprio Python ou de um sistema operacional novo. Veja as condições e os limites em [VALIDATION.md](VALIDATION.md).

Siga [INSTALL.md](INSTALL.md) para criar o ambiente, instalar as versões para CPU, obter os arquivos oficiais, extrair os pesos visuais e configurar o caminho. No Windows, use uma pasta curta: caminhos longos causaram falhas no ensaio. O guia também explica o caso em que `py` não é reconhecido, sem presumir que o Python esteja ausente.

Depois da preparação, abra **Abrir_bancada.cmd** no Windows ou execute `python launcher.py` com o ambiente preparado em outros sistemas. O serviço escuta em `127.0.0.1:8765`. Use primeiro o padrão geométrico gerado pela própria interface para conferir a instalação. Depois, escolha os arquivos que quiser analisar.

O caderno interativo usa Jupyter local. Enquanto ele estiver aberto, trate sua URL com o token temporário como uma senha e não a compartilhe. Para usar imagem, lote, vizinhos e vídeo/GIF, incluindo os limites da análise e dos gráficos, consulte o [guia de uso](GUIA_DE_USO.md) e o texto da própria interface. Fechar a aba não encerra o servidor nem apaga os experimentos.

No lote, o campo **Escolher pasta de imagens** usa a seleção do navegador, do mesmo tipo que imagem e vídeo/GIF. O navegador pede acesso à pasta e entrega os arquivos selecionados ao servidor local. A bancada preserva subpastas e bytes originais numa cópia em `imports/pasta_…`, para que as miniaturas e os lotes continuem disponíveis. Apenas JPG, JPEG, PNG, WEBP, BMP, TIF e TIFF são copiados: até 5.000 imagens, de até 20 MB cada.

A interface mostra o progresso e permite cancelar a cópia em andamento, preservando a seleção anterior. Escolher a pasta não executa o encoder. A opção **usar o caminho da pasta, sem copiar arquivos** continua disponível. O seletor não depende de uma janela Python nem do serviço legado de seleção de pastas. O servidor local ainda precisa estar em execução.

## Metodologia editável · versão 0.4

A interface separa três escolhas: **como resumir os tokens** (média, máximo ou mediana por coordenada), **como normalizar** (L2, L1, L∞ ou nenhuma) e **como comparar** (cosseno, distância euclidiana ou produto escalar). O padrão permanece média + L2 + cosseno. Essas operações pertencem à bancada e não alteram o merger aprendido nem os pesos do Qwen.

L1 divide pela soma dos valores absolutos; L2 pela raiz da soma dos quadrados; L∞ pelo maior valor absoluto. Essas divisões preservam a direção de vetores não nulos. Trocar apenas entre elas não muda matematicamente o cosseno, embora altere as barras; pequenas diferenças numéricas são possíveis. Distância euclidiana e produto escalar podem mudar. Nenhuma receita é universalmente melhor. Referências: [normas](https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html) e [cosseno](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html).

- **Imagem individual:** gráficos antes/depois do merger. A medida de comparação fica registrada; esse gráfico de uma imagem não é uma busca de vizinhos.
- **Vídeo/GIF:** a receita produz vetores da sequência e por par temporal. A tela mostra também a medida escolhida entre pares consecutivos, no mesmo estágio.
- **Recalcular análise:** imagem e vídeo preservam tokens completos. O botão os reutiliza sem executar o encoder. Alterar pixels, fundo, resolução ou amostragem temporal exige preparar e executar outra entrada.
- **Lote:** a receita é fixada antes de iniciar e vale para todas as imagens. Guardamos vetores agregados; outra agregação exige novo lote. Receita e identidade do encoder acompanham o arquivo. Divergências em relação ao registro impedem a consulta.
- **Vizinhos:** menor distância euclidiana fica primeiro; maior cosseno/produto escalar fica primeiro. A própria imagem é excluída e empates seguem a ordem original.

Conjuntos antigos continuam legíveis com a identificação “receita histórica presumida: média + L2 + cosseno”. Isso não cria retroativamente evidência de modelo/receita ausente nos registros. Consultar não converte nem sobrescreve arquivos antigos.

Os NPZ de imagem/vídeo preservam os campos históricos de média/L2 para cadernos existentes. Os campos `vetor_analise_antes`, `vetor_analise_depois` e `receita_json` identificam a análise atual. A parcela de uma coordenada na soma dos quadrados usa o comprimento real do vetor, inclusive com L1, L∞ ou nenhuma.

## Código comum e dados locais separados

Desenvolva em uma única cópia escolhida como fonte. `code_manifest.json` identifica os arquivos compartilhados por SHA-256. Dados, pesos, configuração local, logs e cadernos pessoais adicionais ficam fora da seleção. Após revisar/testar uma alteração, atualize o manifesto com `python tools/sync_code.py --refresh`.

Confira outra instalação com `python tools/sync_code.py --target CAMINHO_DA_INSTALACAO`. Só `--apply` copia. A ferramenta confere a fonte, bloqueia edições inesperadas no destino, preserva dados e guarda o código substituído em backup. A primeira migração de uma instalação modificada exige inventário anterior revisado (`--baseline`); não há opção de sobrescrever conflitos à força. `--backup-root` permite guardar os backups fora de uma pasta candidata a publicação.

`config-local.json` pode definir também `default_image_folder`, `python_executable` e `python_site_packages` para uma instalação existente. Esses valores não pertencem ao pacote público. Na instalação comum, o inicializador usa `.venv` desta pasta; o código e a interface são os mesmos. `QWEN35_PORT` permite testar em outra porta local; o padrão continua 8765.

Execute `python -B tests/test_analysis.py` para verificar propriedades matemáticas e a sincronização. Esses testes não substituem a execução real do encoder e da interface.
`python -B tests/test_folder_upload.py` confere preservação dos bytes, subpastas, limites e limpeza de cópias canceladas. O campo de pasta também deve ser testado no navegador de destino. `tests/test_picker.py` mantém verificações do seletor nativo legado, que já não é iniciado pela bancada.

## Verificação estática do pacote

Antes de preparar qualquer publicação, execute `python tools/check_publication_gate.py`. O verificador usa somente a biblioteca padrão e reprova a cópia se encontrar pesos, mídias, estado experimental, configuração local, caminhos pessoais, segredos literais, saídas salvas no notebook, Python inválido, dependências sem versão fixa ou serviços configurados fora do endereço local.

O verificador confere também o manifesto e seus hashes, arquivos fora da seleção, anexos e metadados do notebook, documentos obrigatórios e presença de licença definitiva. Os [testes do verificador](tests/test_publication_gate.py) incluem exemplos de conteúdo que precisa bloquear a preparação. A aprovação estática não substitui execução ponta a ponta, revisão do histórico Git, segurança dinâmica ou análise de licenças.

## Créditos, licença e contribuições

**Copyright © 2026 Rebojar.** O código original da bancada, seus testes, sua documentação e o caderno didático são disponibilizados sob a **GNU Affero General Public License, versão 3 somente (`AGPL-3.0-only`)**. O texto integral está em [LICENSE](LICENSE). O programa é fornecido sem garantia, nos termos dessa licença.

Você pode usar, estudar, modificar e redistribuir o programa, inclusive comercialmente. Ao distribuir versões abrangidas pela licença, cumpra suas condições de disponibilização do código-fonte correspondente aos destinatários. Se modificar o programa e permitir interação remota com essa versão pela rede, ofereça de forma visível a esses usuários acesso gratuito ao código-fonte correspondente, conforme a seção 13. Uma versão apenas acessível pelo navegador também pode estar sujeita a essa condição. Não é necessário enviar suas alterações a Rebojar nem usar o GitHub como local de disponibilização.

A licença da bancada não concede direitos sobre os pesos, dependências ou arquivos analisados. Usar o programa não torna suas imagens, notas e resultados automaticamente públicos ou sujeitos à AGPL. Consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) para os componentes externos, [CONTRIBUTING.md](CONTRIBUTING.md) para contribuir e [SECURITY.md](SECURITY.md) para os limites do uso local e a seleção de arquivos.

## Limites desta versão

O teste original foi com o Qwen3.5-9B indicado; a escolha do diretório é configurável, **não** a arquitetura do encoder. As representações antes/depois do *merger* são etapas de uma mesma inferência, não resultados de antes/depois de treinamento. O pacote de código não inclui resultados experimentais nem constitui evidência de funcionamento em todos os sistemas. As condições já verificadas estão registradas em [VALIDATION.md](VALIDATION.md).
