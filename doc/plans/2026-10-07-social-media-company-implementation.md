# Implantação do exemplo de empresa de Social Media

Este plano acompanha [examples/social-media-company](../../examples/social-media-company/README.md). Ele descreve como preparar uma empresa pausada em uma instalação Paperclip; não é um recibo de execução nem afirma que clonar o repositório cria agentes ou conexões.

O exemplo usa Agrisul canaa, os fatos fornecidos pelo usuário e quatro papéis: Coordenação Editorial, Pesquisa, Copywriting e Design. A [arquitetura](../../examples/social-media-company/ARQUITETURA.md) define entradas, handoffs, revisões e conclusão. O [contexto](../../examples/social-media-company/CONTEXTO-MARCA.yaml) mantém voz, pilares e objetivos sugeridos em `editorial_proposals`, sem aprovação de produção.

## Escopo e pré-requisitos

- Instância Paperclip acessível com autoridade de board para criar e configurar a empresa, agentes, documentos e tarefas. Os scripts usam o transporte definido em `automation/paperclip_api.py`; não importam credenciais de outra instalação.
- Python 3.10+ e o checkout completo. Confira os contratos da API e os adapters disponíveis na versão instalada antes de executar mutações.
- `company.json` com nome e descrição do exemplo ou da empresa que será preparada. Revisar o contexto antes de reutilizar o pacote para outra marca.
- Sem aprovação de marca, runtime de produção, ferramentas verificadas e orçamento, a empresa, os agentes e as rotinas permanecem pausados. `budget=0` não prova gratuidade nem substitui controle financeiro.

O pacote não inclui export de banco, recibos anteriores, credenciais, materiais internos ou documentos de outra instalação. Não copie IDs para reutilizar o exemplo; deixe o bootstrap resolvê-los.

## Sequência de preparação

Os comandos abaixo partem da raiz de `examples/social-media-company`. Eles criam ou atualizam objetos na instância configurada; não devem ser usados como um teste local sem API.

```sh
python3 automation/provision.py initial
python3 automation/provision.py team
python3 automation/configure_workflows.py
python3 automation/publish_playbook.py
python3 automation/verify_setup.py
```

1. **Base:** conferir instância e permissões; criar/reutilizar a empresa de forma rastreável, mantê-la pausada e preparar os projetos de governança e produção.
2. **Equipe:** preparar os quatro agentes, três relações `reportsTo`, instruções gerenciadas e skill compartilhado. Contratação/configuração não comprova autenticação no modelo, busca web ou geração de imagem. Os agentes permanecem pausados, sem timers nem despertar por demanda durante a preparação.
3. **Contexto:** publicar `architecture` e `implementation` na tarefa de operações; `brand-context` e `brand-publication` na tarefa da marca. O recibo de publicação nasce pendente, com revisão aprovada, responsável e data de aprovação vazios. Documento bloqueado não significa documento aprovado.
4. **Fluxo:** preparar modelos, dependências Pesquisa → Pauta → Copy → Design, gates de review do Editorial e rotinas pausadas. Aprovação humana final, quando exigida pela marca, entra depois do review de Design sobre o mesmo pacote.
5. **Playbook:** disponibilizar `social-media-production`, seu helper e referência de contratos. As keys `production-playbook` e `contract-reference` preservam as versões consultáveis na tarefa de operações.
6. **Conferência:** reler a configuração, versões e locks; conferir relações, instruções, skill, dependências, status e ausência de execuções disparadas pela preparação.

O diretório do pacote é resolvido a partir dos scripts. `SOCIAL_MEDIA_WORKSPACE` pode selecionar outra cópia completa do pacote. O recibo local padrão é `.runtime/paperclip-records.json`; `SOCIAL_MEDIA_RECORDS_PATH` permite outro destino. Workspaces dos agentes ficam em `.runtime/workspaces/`. Esses dados são próprios da instalação e não devem ser versionados. `CONTEXTO.md` é gerado para cada bundle com referências reais; ele não vem de uma instância anterior.

## Validação local e na instalação

As verificações locais do contrato não acessam a API:

```sh
python3 -m unittest discover -s automation -p 'test_*.py' -v
```

Elas devem cobrir transições, envelopes incompletos, falta de arquivos, revisão antiga, aprovação humana e retorno à etapa causal. O contrato executável e seus limites estão em [automation/README.md](../../examples/social-media-company/automation/README.md).

Na instalação preparada, conferir:

- Quatro agentes, hierarquia correta, empresa/agentes/rotinas pausados e instruções disponíveis.
- Contexto e recibo protegidos, com aprovação explicitamente pendente.
- Modelos de produção encadeados, com review das entregas especializadas e sem conteúdo fictício apresentado como pronto.
- Reexecução utilizando o mesmo recibo sem duplicar os objetos já registrados. Não tentar adivinhar IDs quando houver objetos semelhantes sem recibo.
- Nenhuma execução de modelo ou geração de criativo disparada pelo bootstrap.

Os resultados concretos pertencem ao recibo e ao relatório local da instalação. Passar nos testes unitários ou reler a API não prova funcionamento das integrações de produção.

## Ativação do piloto

Completar e aprovar a revisão da marca; confirmar identidade/asset, contato/CTA e catálogo aplicáveis; verificar adapter, pesquisa web, geração/edição, composição, inspeção visual e upload no runtime real; definir orçamento, volume e política de aprovação. Preparar a demanda manual com canal e formato aceitos e executar os cenários de [aceite da arquitetura](../../examples/social-media-company/ARQUITETURA.md#15-cenários-de-aceite-antes-da-ativação).

O piloto precisa entregar imagens reais, textos e manifesto e demonstrar uma correção causal e uma rejeição de versão antiga. Recorrência só deve ser habilitada depois da validação, com calendário e capacidade aprovados. Aprovar conteúdo significa preparar a entrega; não autoriza automaticamente publicação, anúncios ou mensagens.

## Limites

O helper é uma ferramenta explícita e não intercepta alterações diretas na API do Paperclip. Seu perfil cobre uma peça com exports PNG; ele não garante atomicidade entre várias issues, transações de campanha ou invalidação automática de todo o grafo. Revisões e arquivos precisam de CAS/recibos válidos, e a inspeção semântica e visual continua sendo responsabilidade dos agentes e revisores.

Os scripts não habilitam produção autônoma completa apenas por provisionar a estrutura. Recursos adicionais e testes do runtime são necessários antes de tratar o exemplo como uma empresa em produção.
