# Uso local e revisão dos arquivos

Esta bancada foi feita para uma pessoa executar experimentos no próprio computador. Seus servidores escutam em `127.0.0.1`; o Jupyter pode executar código Python com os mesmos acessos da conta que o iniciou. Esta versão não oferece isolamento entre visitantes de um serviço público.

Não transforme esta instalação em hospedagem pública apenas expondo suas portas. Autenticação, isolamento de arquivos, fila, retenção e proteção de recursos para vários visitantes exigem outro projeto de serviço e novos testes.

## Onde ficam os dados

Entradas, cópias de pastas e resultados permanecem nas pastas `sessions/`, `batches/`, `videos/` e `imports/` da instalação que está sendo executada **no computador da própria pessoa**. Configuração, logs e estado do Jupyter também são locais. 

Quando uma imagem, um vídeo ou uma pasta é escolhido pelo navegador, a página envia somente os arquivos selecionados ao servidor local em `127.0.0.1`. A seleção de uma pasta cria uma cópia dentro de `imports/`; o modo de caminho direto lê a pasta original. O conteúdo também pode permanecer temporariamente na memória da aba e aparecer em miniaturas enquanto a página ou o serviço estiver aberto. Alguém com acesso à mesma conta do computador ou à sessão aberta do navegador poderá potencialmente vê-lo.

Se o arquivo original estiver apenas num pendrive ou em outra mídia removível, escolhê-lo no modo comum deixa de mantê-lo somente nessa mídia: imagens individuais são copiadas para `sessions/`, vídeos para `videos/` e pastas enviadas pelo navegador para `imports/`. O modo de caminho direto evita copiar as entradas de um lote, mas resultados, registros e representações derivadas continuam sendo gravados localmente. Não use um computador compartilhado ou controlado por outra pessoa para analisar material sensível quando for necessário preservar uma única cópia ou impedir o acesso por quem administra a máquina.

O projeto não consegue proteger os dados contra alguém que já controle o computador, a conta do sistema ou uma instalação modificada da própria bancada. Para material sensível, use uma máquina sob seu controle e obtenha o código pelo repositório oficial.

Fechar a página não encerra os serviços nem apaga as cópias, resultados ou possíveis registros temporários do navegador e do sistema operacional. Em um computador compartilhado, encerre os serviços e remova conscientemente as pastas do experimento quando não quiser preservá-las. 

> A [demonstração estática](https://rebojar.github.io/demonstracao-labvisual/) publicada no [Rebojar](https://rebojar.github.io/) ([repositório da página](https://github.com/rebojar/rebojar.github.io)) é diferente: ela usa apenas exemplos e resultados previamente selecionados, não aceita arquivos da pessoa visitante e não cria essas pastas no computador dela.

Arquivos de registro exportados podem incluir nomes, caminhos, hashes, horários e observações de um experimento. Revise-os antes de compartilhar. Um vetor ou gráfico derivado de uma imagem também é um resultado desse experimento; não deve entrar automaticamente no pacote público.

## Antes de publicar ou abrir uma contribuição

Selecione somente os arquivos do manifesto. Confira que os hashes correspondem à revisão, que o notebook não tem saídas/anexos e que não há configurações pessoais, segredos, pesos, mídias ou resultados experimentais. O `.gitignore` evita inclusões acidentais comuns, mas não remove arquivos que já foram adicionados ao Git.

Revise também o histórico que será enviado. O verificador estático inspeciona a seleção atual, não todos os commits, dependências binárias ou o estado completo da máquina. Ele não é uma certificação de segurança.

Para relatar uma possível vulnerabilidade, não publique tokens, arquivos privados ou uma exploração contendo dados pessoais. Se o repositório estiver com o relato privado de vulnerabilidades habilitado, use esse canal. Caso ele ainda não esteja disponível, abra apenas uma *issue* curta solicitando um contato privado, sem incluir detalhes técnicos ou dados sensíveis.
