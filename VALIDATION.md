# Validação e condições de reprodução

Registro resumido de 20/09/2026 para a versão `0.4.0-metodologia`. Os relatórios privados de execução, com caminhos locais e cadernos executados, ficam fora deste pacote.

## Ambientes realmente testados

| Verificação | Linux em Docker | Windows nativo |
|---|---|---|
| Ambiente | Debian Bookworm, Python 3.12.14 | Windows 11 build 26200, Python 3.12.14 x64 existente |
| Dependências novas | Sim, dentro da imagem | Sim, em `.venv` nova, sem pacotes globais |
| Dispositivo | CPU; container com 2 CPUs e limite de 6 GiB | CPU no notebook de validação |
| Dependências coerentes | `pip check` aprovado | `pip check` aprovado; 9 importações verificadas no ambiente novo |
| Extração | 333 tensores idênticos à referência | 333 tensores idênticos à referência |
| Contratos matemáticos/pasta | 15 testes aprovados | 15 testes aprovados |
| Fluxos com encoder real | 51 verificações aprovadas | 51 verificações aprovadas |
| Caderno | 14 células executadas | 14 células executadas com kernel do ambiente novo |
| Inicializador `.cmd` | Não se aplica | Aprovado |
| Navegador | Não exercitado no container | Controles principais conferidos |
| Duração do roteiro automático | 236,587 s | 249,328 s |
| Pico de memória medido | 3,04 GiB no container | Sem medição equivalente |

Os tempos não incluem downloads/instalação ou inspeção manual da interface. As medições descrevem o conjunto sintético do ensaio, não um limite de memória ou uma promessa de desempenho para qualquer arquivo. Lotes, resoluções e amostragens maiores podem exigir mais recursos.

As versões diretas foram: PyTorch 2.14.0+cpu, torchvision 0.29.0+cpu, Transformers 5.17.0, NumPy 2.5.2, Pillow 12.3.0, Safetensors 0.8.0, PyAV 18.1.0 e JupyterLab 4.6.3. As dependências transitivas não foram integralmente fixadas: repetir `requirements.txt` em outra data pode resolver versões transitivas diferentes. Isso não é uma distribuição hermética.

## O que foi comparado

O roteiro verificou preparação separada da inferência, valores finitos, média/máximo/mediana, normas e medidas de comparação, recálculo sem nova inferência, preservação dos tokens, equivalência individual/lote sob a mesma receita, vizinhos, cópia/cancelamento de pasta, GIF, MP4 e rejeição de receita inválida.

Os pesos extraídos foram comparados por nome, forma, tipo e bytes de cada tensor. Arquivos Safetensors podem ter cabeçalhos de metadados diferentes e ainda conter os mesmos tensores. A comparação não estabelece equivalência com um mmproj GGUF quantizado.

O teste de interface incluiu imagem, pasta com seis imagens sintéticas, lote, seleção de vizinhos, GIF, duração/amostragem, gráficos, rolagem das barras até a última coordenada, exportação e abertura do JupyterLab. Os seletores foram acionados por automação do navegador; isso não é inspeção visual da janela nativa do Explorer.

## Vídeo no navegador

O MP4 sintético com MPEG-4 Part 2 foi decodificado e processado pelo encoder. Sua reprodução no player original falhou no navegador integrado usado na automação. Posteriormente foi confirmado que a prévia funcionava em outro navegador do mesmo computador; navegador e versão não foram registrados. Essa confirmação é evidência de uso, não uma garantia de suporte a todos os codecs.

## Limites da evidência

Não foram testados: instalação nova do próprio Python no Windows, Windows recém-instalado, macOS, GPU, outros encoders, novo download dos pesos nesse ensaio, todos os navegadores e codecs, serviço público com múltiplos visitantes. No Docker, a execução do container de teste usou `--network none` e `--pull=never`. No Windows foram usados arquivos locais e configurações offline das bibliotecas, sem isolamento de rede do sistema operacional.

Os arquivos do motor, do inicializador e da interface validados nos ensaios foram preservados nesta revisão documental. As verificações do pacote devem ser repetidas sobre o manifesto final. O verificador automático da seleção pública confere arquivos, hashes e padrões de risco; ele não repete os 51 testes funcionais nem constitui uma garantia completa de segurança.
