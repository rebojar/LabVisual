# Guia de uso da bancada visual

Este guia começa depois da instalação descrita em [INSTALL.md](INSTALL.md). A bancada tem quatro modos que trabalham juntos: uma imagem, lote de imagens, vizinhos e vídeo/GIF. Tudo é executado localmente com os pesos visuais congelados; não há treinamento nem uso do modelo de linguagem.

## Antes de começar

Abra a bancada e confirme, no rodapé, que o encoder local foi encontrado. Preparar uma entrada permite conferir exatamente o que será enviado ao encoder; a inferência só começa quando você aciona o botão de execução.

O painel **Escolha como analisar** define três operações sobre as saídas do encoder: agregação, normalização e medida de comparação. Essas escolhas não modificam os pesos nem o *merger* aprendido. Em imagem e vídeo/GIF, os tokens completos permitem recalcular a análise sem nova inferência. Em lote, a receita é fixada antes do início e outra agregação exige um novo lote.

## Uma imagem

1. Abra **Uma imagem** e escolha um arquivo de até 20 MB ou use o padrão geométrico de teste.
2. Defina o orçamento de pixels, a versão em cores ou cinza e o fundo aplicado à transparência. A hipótese é uma anotação local e não entra no encoder.
3. Clique em **Preparar imagem**. Confira o original, a entrada preparada e, quando necessário, a máscara de opacidade. As grades são sobreposições didáticas; não entram na rede.
4. Escolha a receita e clique em **Executar minha imagem**.
5. Examine os tokens antes e depois do *merger*, as coordenadas do vetor agregado, os registros e os arquivos para download.

Uma diferença entre vetores mostra sensibilidade às condições da entrada; sozinha, não prova compreensão, importância semântica ou reconhecimento de um objeto. A medida de comparação escolhida só ganha função comparativa ao trabalhar com um conjunto na aba **Vizinhos**.

A interface avisa, junto ao seletor, que preparar a imagem grava uma cópia local. Os arquivos deste modo ficam em `sessions/`. Mudar pixels, fundo, resolução ou versão da imagem exige preparar e executar outra entrada. Mudar apenas a receita pode reutilizar os tokens salvos.

## Lote de imagens

1. Abra **Lote de imagens**.
2. Escolha uma pasta pelo navegador ou informe seu caminho local. Um aviso junto ao seletor informa que a seleção pelo navegador cria uma cópia em `imports/`; o caminho direto lê os originais sem copiá-los.
3. Clique em **Conferir imagens da pasta** e revise nomes, formatos e miniaturas. Essa etapa não executa o encoder.
4. Defina resolução, cores ou cinza, fundo para transparência e receita de análise.
5. Inicie o lote e acompanhe o progresso. **Parar após a imagem atual** preserva os resultados já concluídos.
6. Ao final, baixe `embeddings.npz` e `registro.json` ou abra o conjunto em **Vizinhos**.

São aceitos JPG, JPEG, PNG, WEBP, BMP, TIF e TIFF, incluindo subpastas: até 5.000 imagens, com até 20 MB e 20 milhões de pixels por imagem. Todas as imagens válidas de um lote usam as mesmas condições. Os resultados ficam em `batches/`; cópias feitas pelo navegador ficam em `imports/`.

## Vizinhos

Esta aba compara imagens de um lote já executado, sem rodar o encoder novamente.

1. Escolha o conjunto de representações.
2. Selecione uma imagem na galeria.
3. Compare seus cinco vizinhos antes e depois do *merger*.
4. Clique em uma vizinha para investigá-la ou volte à galeria.
5. Registre observações e exporte a comparação quando quiser conservá-las fora do navegador.

A consulta respeita a receita salva com o lote. A própria imagem é excluída; arquivos diferentes com conteúdo duplicado continuam elegíveis. Menor distância euclidiana significa maior proximidade; para cosseno e produto escalar, valores maiores aparecem primeiro. Proximidade numérica não estabelece, por si só, uma categoria visual ou explicação semântica.

## Vídeo e GIF

### Preparar e observar

1. Abra **Vídeo / GIF** e escolha um arquivo de até 50 MB. Um aviso junto ao seletor informa que o arquivo será copiado para esta máquina. O áudio não é utilizado.
2. Defina início e fim em segundos. O fim não é incluído. Esta versão aceita trechos de até 60 segundos dentro dos primeiros 10 minutos do arquivo.
3. Escolha 2, 4, 8 ou 16 quadros e o orçamento de pixels por quadro. Comece com 4 ou 8 quadros.
4. Clique em **Preparar sequência**. A preparação seleciona quadros em instantes uniformemente espaçados e usa o processador do checkpoint sem executar o encoder.
5. Confira o quadro original com fundo aplicado, a entrada preparada, os tempos efetivos e eventuais repetições. A reprodução didática avança a 2 quadros por segundo e não representa necessariamente a velocidade original.

O GIF original pode continuar animado. A sequência preparada mostra somente os quadros enviados. GIFs sem duração válida usam 100 ms nos quadros afetados; isso fica registrado. A transparência é composta sobre a cor escolhida, e largura e altura se ajustam a múltiplos de 32.

### Executar e examinar

Escolha a receita e clique em **Executar esta sequência no encoder**. O resultado permite examinar a sequência inteira ou cada par temporal, antes ou depois do *merger*. A medida escolhida aparece na comparação entre pares consecutivos; isso não é uma avaliação de compreensão do movimento.

Downloads disponíveis:

- **Todos os tokens:** matrizes antes e depois do *merger*, campos históricos de média/L2 e vetores da receita atual.
- **Vetores por par temporal:** vetores, tempos e campos de compatibilidade de cada par.
- **Registro:** condições, índices e tempos dos quadros, dimensões, hash e observações.

Os arquivos ficam em `videos/`. PyAV faz a leitura de vídeo e Pillow, a de GIF. O player do navegador pode não reproduzir um codec que a bancada ainda consegue decodificar; nesse caso, confira as miniaturas e a entrada preparada. Se a preparação também falhar, examine a mensagem do leitor.

## Arquivos locais e encerramento

Fechar a aba não encerra os serviços nem apaga experimentos. Consulte [SECURITY.md](SECURITY.md) antes de trabalhar com arquivos sensíveis, mídia removível ou computadores compartilhados. Os registros podem conter nomes, caminhos, hashes, horários e observações; revise-os antes de compartilhar.
