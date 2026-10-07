# Empresa de Social Media — Agrisul canaa

Pacote de arquitetura, contexto editorial em rascunho, instruções e automações para uma equipe de quatro agentes no Paperclip. O exemplo usa os fatos informados pelo responsável da Agrisul: irrigação, máquinas, implementos e ordenhadeiras; produtores rurais, fazendeiros e pecuaristas; Canaã dos Carajás e região; Instagram e reaproveitamento selecionado de Stories no WhatsApp.

**O bootstrap prepara uma empresa pausada.** Não autentica provedores, escolhe um LLM, conecta geração de imagens, executa modelos ou publica conteúdo. Os campos de aprovação, identidade visual, oferta atual e orçamento continuam pendentes. Propostas de voz e pilares estão identificadas como propostas.

## Organização e produção

| Agente | Responsabilidade |
|---|---|
| Coordenação Editorial | Admitir demandas, selecionar pautas, coordenar dependências, aceitar handoffs e revisar a cadeia |
| Pesquisa e Inteligência de Conteúdo | Investigar fontes, localizar evidências e sugerir oportunidades |
| Copywriting | Escrever os textos completos, legenda e CTA da pauta aceita |
| Design e Direção Criativa | Definir direção visual, produzir os arquivos e inspecionar a entrega |

`Pedido + contexto aprovado → pesquisa → curadoria → pauta → copy → direção criativa → criação visual → revisão → entrega`

Os três especialistas respondem ao Editorial. Revisão usa versões identificadas; um problema volta à etapa responsável, com critério violado e condição verificável de aceite. O validador local auxilia contratos e transições; não intercepta a API nem substitui inspeção visual ou decisões nativas.

## Arquivos

- [ARQUITETURA.md](ARQUITETURA.md): quatro papéis completos, contratos, estados, revisão, retrabalho e governança.
- [OPERACAO-AGRISUL.md](OPERACAO-AGRISUL.md): funcionamento aplicado à marca e demandas manuais.
- [CONTEXTO-MARCA.yaml](CONTEXTO-MARCA.yaml): fatos do responsável e campos pendentes, sem IDs de uma instância.
- [PROPOSTA-EDITORIAL.yaml](PROPOSTA-EDITORIAL.yaml): recomendações separadas da aprovação da marca.
- [Plano de implantação](../../doc/plans/2026-10-07-social-media-company-implementation.md): sequência e critérios de ativação.
- `agents/`: instruções de cada especialista; o bootstrap resolve os IDs oficiais em `CONTEXTO.md` gerenciado.
- [playbooks/SKILL.md](playbooks/SKILL.md): fluxo compartilhado instalado nos agentes.
- [automation/README.md](automation/README.md): contrato executável e seus limites.
- [company.json](company.json): nome e descrição usados ao criar a empresa.

Os documentos internos do Drive, PDFs, extrações integrais, dados de RH, banco, credenciais e recibos reais da implantação permanecem fora do Git. O estado operacional da empresa é armazenado pelo Paperclip; este pacote não é backup integral do banco ou dos arquivos da instância.

## Verificar sem alterar o Paperclip

Requer Python 3.10+; os scripts de operação e os testes usam a biblioteca padrão. Para editar/verificar os YAMLs com um parser, use PyYAML no seu ambiente de desenvolvimento.

Na raiz do repositório:

```bash
python3 -m unittest discover -s examples/social-media-company/automation -p 'test_*.py' -v
```

Os testes usam fixtures locais e API simulada. Não comprovam autenticação, disponibilidade de modelos, geração visual ou execução real de conteúdo.

## Preparar uma instância

1. Inicie o Paperclip conforme [DEVELOPING.md](../../doc/DEVELOPING.md), com acesso de board autorizado.
2. Revise `company.json`, contexto, propostas e instruções para a empresa pretendida.
3. Configure `PAPERCLIP_API_URL` se o serviço não estiver no endereço local padrão. Quando a implantação exigir autenticação, disponibilize `PAPERCLIP_API_KEY` pelo mecanismo seguro do ambiente; não a grave no pacote.
4. Execute as fases abaixo. `team` solicita e aprova as quatro contratações como ação do operador e deixa os agentes pausados. Nenhuma fase executa um modelo.

```bash
cd examples/social-media-company
python3 automation/provision.py initial
python3 automation/provision.py team
python3 automation/configure_workflows.py
python3 automation/publish_playbook.py
python3 automation/verify_setup.py
```

Essas fases escrevem configuração na API. O bootstrap salva IDs/revisões em `.runtime/paperclip-records.json`, ignorado pelo Git; as pastas de trabalho também ficam em `.runtime/`. Preserve os recibos para retomar a mesma implantação. Sem recibos, uma empresa já existente com o mesmo nome/descrição exige conciliação: o bootstrap não deve adotá-la e pausá-la silenciosamente.

`SOCIAL_MEDIA_WORKSPACE` seleciona outra raiz completa deste pacote. `SOCIAL_MEDIA_RECORDS_PATH` seleciona um arquivo de recibos, absoluto ou relativo à raiz. Esses seletores não concedem acesso à API nem tornam IDs portáteis entre instâncias. Para uma empresa já configurada, use os recibos correspondentes e confira os documentos atuais; não reaplique formulários iniciais sobre uma marca que já evoluiu.

O contexto e o recibo canônicos ficam protegidos, mas **lock não significa aprovação**. A autoridade da marca precisa publicar uma revisão concreta com os dados necessários e registrar seu aceite. A pergunta nativa solicita apenas o que estiver pendente; rotinas e agentes permanecem pausados.

## Demandas manuais

Depois de preparar os recibos, a entrada pode registrar pedidos no backlog:

```bash
python3 automation/intake.py \
  --request-id carrossel-irrigacao-001 \
  --pedido 'Quero um carrossel educativo sobre informações para solicitar orçamento de irrigação' \
  --channel instagram --format carousel

python3 automation/intake.py \
  --request-id story-ordenhadeiras-001 \
  --pedido 'Story sobre ordenhadeiras com reaproveitamento no WhatsApp' \
  --channel instagram --format story --reuse-on-whatsapp-status
```

O `request-id` estável evita duplicação e não pode ser reutilizado com outro pedido. Campanhas usam `--kind campaign`; suas peças podem referenciar `--campaign-id`. Cada peça é admitida pelo Editorial após verificar contexto, capacidade e dependências.

A flag de reaproveitamento registra uma escolha; não cria nem publica automaticamente a variante. Quando houver uma origem aceita, a versão WhatsApp usa `--channel whatsapp --format status --source-content-id ID_REAL --source-revision REVISAO_REAL`. O helper confere a empresa; o Editorial confere a validade da revisão e revisa CTA, leitura e elementos do destino. Outras redes podem ser solicitadas, mas só entram após definir seus formatos e critérios.

## Modelos e APIs por agente

O exemplo usa `codex_local`, engine CLI, sem um modelo específico fixado. Escolha modelo/conexão por agente em **Agents → agente → Harness / Runtime → Adapter**. O catálogo exibido não comprova acesso pela conta; verifique o runtime antes do piloto.

O Design pode usar um LLM para planejamento e uma API separada para gerar/editar imagens. Essa API entra como ferramenta por conector compatível ou integração MCP, com acesso concedido ao Design em **Tools**. O campo `Model` escolhe o LLM; não instala uma ferramenta visual. Autenticação, registro de arquivos e consumo da API externa precisam ser verificados na integração real.

## Ativação

Complete os dados mínimos da marca, aprove o contexto e a política de revisão, configure orçamento e autenticação, comprove pesquisa web e as ferramentas visuais e execute um piloto controlado. O piloto verifica arquivos reais, handoffs, correções e aprovações. Só depois configure recorrência com calendário, fuso e volume compatíveis com a capacidade. `APPROVED` significa conteúdo pronto para entregar; publicação e envio de mensagens exigem escopo próprio.
