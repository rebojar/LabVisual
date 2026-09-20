# Como contribuir

Sugestões sobre clareza das explicações, acessibilidade, cálculos e reprodução dos experimentos são bem-vindas. Descreva o comportamento esperado e o observado, com o menor exemplo sintético que reproduza o problema.

## Código e dados

Trabalhe numa cópia separada, seguindo [INSTALL.md](INSTALL.md). Mantenha pesos e configurações locais fora da seleção pública. Não inclua fotografias pessoais, lotes, notas, logs completos, URLs do Jupyter com token, nem resultados derivados de arquivos de outras pessoas.

O notebook distribuído deve permanecer sem saídas, contagens de execução ou anexos. Para explorar, crie uma cópia local com outro nome. Antes de enviar uma contribuição, revise também os commits: excluir um arquivo da pasta não o elimina do histórico.

## Verificações proporcionais à mudança

- Textos: confira links locais e a fidelidade das afirmações aos testes registrados.
- Cálculos ou formato de representações: execute `tests/test_analysis.py` e os fluxos reais afetados. Preserve compatibilidade ou documente a migração.
- Seleção de pastas: execute `tests/test_folder_upload.py` e confira o seletor no navegador.
- Motor e processamento: mantenha o checkpoint, a precisão, a receita e os dados de teste explícitos ao comparar resultados.
- Pacote público: execute `tests/test_publication_gate.py` e `tools/check_publication_gate.py`. Uma aprovação estática é somente uma parte da revisão.

Use o Python do ambiente criado no projeto. `python -B` evita criar arquivos de bytecode dentro da seleção. Os testes leves não baixam o modelo nem fazem treinamento.

## Manifesto e sincronização

O manifesto lista os arquivos compartilhados. Ao adicionar um arquivo público, inclua-o na seleção de `tools/sync_code.py`. Depois da revisão, execute `python -B tools/sync_code.py --refresh` e confira o gate estático. Atualizar hashes não substitui revisar o conteúdo.

Para levar uma atualização a outra instalação local, use primeiro o modo de conferência de `tools/sync_code.py --target CAMINHO`. A opção `--apply` copia somente a seleção e bloqueia conflitos; mantenha os backups fora da pasta que será publicada. Os dados de experimentos não são sincronizados.

## Licença das contribuições

O projeto é disponibilizado sob **AGPL-3.0-only**; consulte [LICENSE](LICENSE) e o aviso de autoria em [README.md](README.md). Ao propor uma contribuição para incorporação ao projeto, disponibilize seu trabalho sob essa mesma licença e preserve os avisos de autoria e licença existentes. Não envie material de terceiros sem os direitos necessários; identifique sua origem e seus termos para revisão. A autoria das contribuições permanece com seus respectivos titulares.
