# Contratos editoriais locais — v1

`contracts.py` é uma ferramenta Python 3.10+ de biblioteca padrão. Agentes podem chamá-la explicitamente antes de entregar ou aceitar trabalho. Não é um quinto agente, serviço, integração instalada ou controle obrigatório do backend do Paperclip. Não faz chamadas de rede nem grava arquivos de estado.

Implementa um **subconjunto explícito** das seções 5, 7, 9 e 15 de `../ARQUITETURA.md`: envelopes, revisões, sequência de uma peça, aceites, decisões finais, devolução causal e verificação local de arquivos. O formato abaixo é o contrato efetivamente executado; o texto de arquitetura contém requisitos editoriais adicionais.

## Provisionamento opcional no Paperclip

Os comandos abaixo fazem alterações na API e exigem uma sessão com autoridade de board na instância escolhida. Revise `../company.json` e o pacote antes de executá-los. `provision.py team` cria e aprova as contratações em nome de quem executa o script; não aprova a marca nem ativa os agentes. Não execute a sequência automaticamente ao clonar o repositório.

```bash
cd examples/social-media-company
python automation/provision.py initial
python automation/provision.py team
python automation/configure_workflows.py
python automation/publish_playbook.py
python automation/verify_setup.py
```

Execute os blocos com `cd examples/social-media-company` a partir da raiz do repositório. Python 3.10+ é suficiente; não há dependências Python externas. A API precisa estar disponível previamente. `PAPERCLIP_API_URL` é a origem da API, sem `/api` ao final (padrão `http://127.0.0.1:3100`). `PAPERCLIP_API_KEY`, quando necessário, deve vir do ambiente seguro; não deve ser gravado nos arquivos deste pacote. Uma chave de agente comum não substitui a autorização de board necessária para contratar, bloquear documentos e configurar políticas.

| Configuração | Padrão e uso |
| --- | --- |
| `SOCIAL_MEDIA_WORKSPACE` | Raiz completa deste pacote, obtida pela localização dos scripts. Pode apontar para outra cópia com `company.json`, contexto, agentes, playbook e README. Um caminho relativo é resolvido a partir do diretório de execução. |
| `SOCIAL_MEDIA_RECORDS_PATH` | `.runtime/paperclip-records.json`, relativo à raiz acima; também aceita caminho absoluto. Recibos são gerados pela API da instância escolhida e não acompanham o repositório. |
| Workspaces de agentes | `.runtime/workspaces/<agente>` dentro da raiz configurada. O runtime local do Paperclip precisa acessar esses diretórios e o pacote no mesmo filesystem. |

Guarde os recibos para retomar o provisionamento; eles não são uma aprovação de marca. Use um workspace/recibo separado para cada empresa e instância. Não reutilize IDs de outra instalação. Sem recibos, uma empresa com o mesmo nome e descrição faz o script parar antes de alterá-la: restaure ou concilie os registros manualmente. As chamadas não têm retries de escrita automáticos; uma resposta perdida pode exigir essa conciliação. Não rode duas instâncias dos scripts sobre o mesmo recibo ao mesmo tempo.

O bootstrap deixa empresa, quatro agentes e duas rotinas pausados, timers e wake sob demanda desligados, modelo de LLM sem seleção explícita e templates em backlog. Resolve `identity.brand_id: null` para o ID da empresa apenas no corpo publicado, e registra `brand_id` e `draft_revision_id` no recibo canônico `brand-publication`; o arquivo-fonte continua portátil. Um ID de marca diferente é recusado. `approved_revision_id`, aprovador e data de aprovação continuam nulos. `configure_workflows.py` cria uma pergunta humana pendente com continuação desativada e uma policy que impede mutações de skills pelos agentes. `verify_setup.py` verifica especificamente esse estado inicial; não é um monitor de produção nem um teste de autenticação, geração de imagens ou orçamento.

`publish_playbook.py` atualiza a skill usando `expectedVersionId`. Para revisar um playbook canônico bloqueado, desbloqueia o documento, usa `baseRevisionId` na escrita e tenta restaurar o lock em `finally`, inclusive se a atualização falhar. Falha ao restaurar o lock interrompe o comando e exige conferir o documento na API. A publicação dos três arquivos da skill e do documento não é uma transação única. Os demais documentos canônicos não são desbloqueados automaticamente: alterações exigem revisão explícita do board. O documento `implementation` recebe o README do pacote, com os passos de implantação.

Demandas manuais também podem ser registradas sem iniciar execução, a partir do diretório do pacote:

```bash
python automation/intake.py --request-id campanha-exemplo-001 --kind campaign --pedido 'Crie uma campanha para este produto'
python automation/intake.py --request-id carrossel-exemplo-001 --format carousel --channel instagram --pedido 'Quero um carrossel educativo sobre este assunto'
```

Cada `request-id` identifica um pedido imutável. Esses comandos criam entradas em backlog com dependências e gates; não configuram a marca, não ligam os agentes e não publicam nas redes.

## Uso do validador local

```bash
cd examples/social-media-company
python -m unittest discover -s automation -p 'test_*.py' -v
python automation/contracts.py validate handoff.json
python automation/contracts.py snapshot workflow.json
python automation/contracts.py transition workflow.json event.json > workflow-candidate.json
```

`validate` imprime `{"errors": []}` e retorna código 0 quando os controles implementados passam; erros retornam código 1. `transition` imprime o próximo estado em JSON, ou um objeto `error` com código 1. Confira o código de saída: um arquivo redirecionado pode conter um erro, nunca o promova automaticamente. `snapshot` produz o objeto exato que uma decisão final deve copiar para `package`.

API Python:

```python
from contracts import validate_handoff, transition, package_snapshot

errors = validate_handoff(handoff)
next_workflow = transition(workflow, event)  # dict novo ou ValueError
```

Nenhuma dessas funções altera os argumentos. O chamador deve ler a revisão corrente do documento no Paperclip, validar e persistir o resultado usando o CAS nativo. `expected_revision` só evita revisão lógica velha dentro desta chamada; não resolve duas gravações concorrentes sem CAS no armazenamento. IDs ilustrativos abaixo **não são recibos reais**.

## Estado de uma peça

```json
{
  "schema_version": "1.0",
  "company_id": "company-id-real",
  "brand_id": "brand-id-real",
  "content_id": "content-id-real",
  "brand_ref": {"document_id": "canonical-brand-document-id", "revision": "approved-revision-id"},
  "actors": {
    "editorial": "editorial-agent-id",
    "research": "research-agent-id",
    "copy": "copy-agent-id",
    "design": "design-agent-id",
    "human": "brand-owner-user-id"
  },
  "human_approval_required": false,
  "revision": 0,
  "stage": "IDEA",
  "operational_status": "active",
  "artifacts": {},
  "acceptances": {},
  "approvals": {},
  "history": []
}
```

São quatro agentes e um responsável humano, com identidades distintas. O chamador resolve a marca pelo documento canônico e recibo de aprovação real antes de criar esse estado. A ferramenta não descobre esse documento, não verifica locks e não autentica o ator informado.

`stage` é editorial; nunca envie esses valores como `status` nativo do Paperclip. `operational_status` aceita `active`, `blocked`, `cancelled`. O histórico guarda eventos e entregas anteriores; correções invalidam os registros correntes sem apagar esse histórico.

## Envelope de handoff

Campos obrigatórios:

| Campos | Formato executado |
|---|---|
| `schema_version` | String `"1.0"` |
| `handoff_id`, `operation_id`, `artifact_revision` | Strings não vazias; uma revisão existente é imutável |
| `artifact_kind` | `research`, `brief`, `copy` ou `design` |
| `scope`, `company_id`, `brand_id` | Escopo e identidades |
| Identificador de escopo | `research_batch_id` em `brand_intelligence`; `campaign_id` em `campaign`; `content_id` em `content` |
| `source_issue_id`, `target_issue_id` | Strings; destino pode ser `null` explícito |
| `producer`, `intended_receiver` | IDs de atores; os eventos conferem com `actors` |
| `created_at` | Data/hora ISO 8601 com fuso |
| `brand_ref` | Exatamente `{"document_id": "…", "revision": "…"}` |
| `based_on` | Mapa com referências exatas `{"handoff_id": "…", "revision": "…"}` |
| `channel`, `format`, `locale`, `objective` | Strings não vazias; canal/formato podem ser `null` só fora de `content` |
| `payload_ref` | `document_id`, `revision`, `receipt_id` e `storage_confirmed: true`; revisão igual a `artifact_revision` |
| `payload` | Objeto inline com os campos abaixo; corresponde ao documento referenciado |
| `files` | Lista explícita; normalmente vazia antes de Design |
| `checklist` | Lista não vazia de `{"criterion": "…", "passed": true/false}` |
| `open_questions`, `blockers` | Listas explícitas, inclusive quando vazias |
| `proposed_next_stage` | `CURATING`, `COPY_IN_PROGRESS`, `DESIGN_IN_PROGRESS`, `REVIEW`, conforme o tipo |

`based_on` exige exatamente: pesquisa `{}`; pauta `{research}`; copy `{research, brief}`; design `{research, brief, copy}`. `validate_handoff` confere o formato; **a comparação com as revisões aceitas vigentes é feita por `transition`**. Não basta validar o arquivo isoladamente para provar que está atualizado.

Pesquisa compartilhada pode ter escopo de marca ou campanha e ser referenciada por uma peça; não se inventa `content_id` para ela. Os outros tipos exigem escopo `content`. Esta ferramenta não coordena a conclusão de várias peças de uma campanha.

### Payload efetivamente validado

Todos os campos listados são obrigatórios. Listas podem ser vazias, salvo as explicitamente não vazias. O editor continua responsável por avaliar a qualidade e se um item é suficiente para a demanda.

| Tipo | Campos |
|---|---|
| Pesquisa | `summary`; listas `sources` (não vazia), `claims`, `insights` (não vazia), `candidate_topics` (não vazia), `gaps`, `source_conflicts`, `used_references`, `rejected_recommendations` |
| Pauta | Strings `audience`, `pain`, `message`, `benefit`, `angle`, `allowed_promise`, `cta`, `deadline`; listas `allowed_claim_ids`, `restrictions`, `intended_metrics`, `structure`; inteiros positivos `slide_count`, `width`, `height` |
| Copy | Strings `message`, `hook`, `headline`, `caption`, `cta`, `reading_notes`, `space_limits`; listas `slides` (não vazia), `claim_ids`, `requested_variants` |
| Design | Strings `direction`, `rationale`, `reproduction_recipe`, `tool_provenance`; listas `applied_text` (não vazia), `assets`, `prompts`, `limitations` |

Cada fonte tem `source_id`, `url`, `title`, `organization`, `source_type`, `reliability`, `evidence_location`, `read_confirmed: true`, `accessed_at` com fuso e `published_at` presente (pode ser `null`). `read_confirmed` é uma declaração a ser auditada pelo Editorial, não prova de navegação.

Cada claim tem `claim_id`, `statement`, `evidence_location`, `limits`, `validity`, `classification` (`fact`, `interpretation`, `hypothesis`) e `source_ids` não vazia referenciando fontes presentes. IDs de fontes e claims são únicos. Insights e pautas candidatas são listas de conteúdo editorial; sua estrutura interna é deliberadamente livre nesta v1.

Cada slide da copy tem `slide_index`, `text` e `narrative_function`; Design fornece `applied_text` com exatamente `slide_index` e `text`. Índices começam em 1 e são consecutivos. O número de slides, dimensões dos exports, canal, formato, idioma e objetivo são comparados à pauta. Claims da copy devem estar permitidos pela pauta, e os claims da pauta devem existir na pesquisa.

Cada asset externo declarado no Design tem `asset_id`, `origin`, `permission`. Listas vazias só são adequadas se nenhum asset externo foi utilizado. A ferramenta exige o registro, mas não comprova licença nem detecta omissão.

### Arquivos reais de Design

`files` precisa conter um ou mais itens `role: "final"`, em ordem, e exatamente um `role: "preview"`. Cada item exige:

```text
attachment_id, receipt_id, storage_confirmed=true,
name, local_path, mime_type="image/png",
width, height, byte_size, sha256, role, alt_text
```

Itens finais também exigem `slide_index`. Os IDs de anexos são únicos. `local_path` deve ser um arquivo regular acessível na máquina atual: baixe uma cópia do anexo quando necessário. O validador lê os bytes, compara tamanho/SHA-256 e verifica assinatura/cabeçalho PNG e dimensões. Nesta v1 só PNG é aceito. Um preview pode apontar para uma cópia local do mesmo conteúdo de um post único, mantendo seu próprio registro no manifesto.

O manifesto retém tanto a cópia local verificável quanto o recibo de armazenamento informado; caminho local sozinho não passa. Prompts sem finais e preview também não passam. A verificação não decodifica completamente o PNG e não realiza OCR, inspeção visual ou prova de que `applied_text` aparece na imagem: Design e Editorial devem abrir os exports e conferir isso.

## Eventos e transições

Todo evento exige `event_id`, `operation_id`, `company_id`, `content_id`, `type`, `actor_id`, `created_at` com fuso e `expected_revision` inteiro igual a `workflow.revision`. Um reenvio idêntico é idempotente; reaproveitar ID com conteúdo diferente é erro. `decision_id` e `correction_id` não podem ser reaproveitados por eventos diferentes.

| Evento | Ator, condição e dados adicionais |
|---|---|
| `start_research` | Editorial em IDEA; `request_ref`, `objective`, `audience`; vai para RESEARCHING |
| `submit` | Produtor da etapa; `handoff`; pesquisa/pauta/copy/design vão para RESEARCHED/BRIEF_READY/COPY_READY/DESIGN_READY |
| `accept` | Destinatário da entrega pronta; `artifact_kind`, `artifact_ref`, `brand_ref`, `decision_id`, `reason`; pesquisa → CURATING, pauta → COPY_IN_PROGRESS, copy → DESIGN_IN_PROGRESS, design → REVIEW |
| `approve` | Editorial em REVIEW; humano só depois do Editorial; `decision_id`, `reason`, `package` exatamente igual a `snapshot`; APPROVED somente com todos os gates e decisões exigidas |
| `reject` | Editorial; `cause` (`research`, `brief`, `copy`, `design`) e feedback abaixo; volta à etapa causal |
| `block` | Ator conhecido, trabalho ativo não aprovado; `reason`, `resolution_owner`, `resume_condition`; preserva etapa e grava `resume_stage` |
| `resume` | Editorial sobre bloqueio; `resolution_evidence`; recupera operação ativa na mesma etapa |
| `cancel` | Editorial ou humano; `reason`; cancela e limpa aprovações |
| `brand_change` | Humano configurado; `previous_brand_ref`, novo `brand_ref`, `decision_id`, `publication_receipt_id`, `impact_reason`; invalida toda cadeia e retorna à Pesquisa |

Pauta é produzida pelo Editorial e aceita pela Copy. Pesquisa, Copy e Design são aceitos pelo Editorial. Nenhum especialista aprova sua própria saída. Todos os checklists devem passar e os blockers devem estar vazios para aceite/finalização; perguntas abertas são tratadas como não impeditivas apenas se o editor as classificou corretamente.

Exemplo de evento inicial:

```json
{
  "event_id": "event-id-real",
  "operation_id": "operation-id-real",
  "company_id": "company-id-real",
  "content_id": "content-id-real",
  "type": "start_research",
  "actor_id": "editorial-agent-id",
  "created_at": "2026-10-06T15:00:00-03:00",
  "expected_revision": 0,
  "request_ref": "issue-or-request-id-real",
  "objective": "Objetivo aprovado da peça",
  "audience": "Público aprovado"
}
```

Uma reprovação exige `reviewed_package` igual ao snapshot corrente, `correction_id`, `criterion`, `location`, `evidence`, `change_requested`, `acceptance_condition`, `priority`, `deadline`, `responsible_actor_id` da etapa causal e `affected_artifacts` com os tipos presentes a partir da causa, em ordem. Exemplo: erro de copy em um pacote completo exige `["copy", "design"]`.

A reprovação invalida a entrega causal e todas as posteriores, remove os aceites correspondentes e limpa aprovações finais. Um erro visual preserva pesquisa/pauta/copy aceitas. A correção deve criar nova `artifact_revision`, atualizar as referências e percorrer os gates novamente. Mesmo sem mudança nos bytes de uma saída dependente, esta v1 exige uma nova revisão com novo aceite; não oferece atalho de revalidação seletiva.

Mudança de marca é conservadora: exige análise de impacto e aprovação declaradas, preserva histórico e invalida toda cadeia. Otimização para preservar saídas não afetadas por uma mudança de marca não está implementada. Essa limitação evita aprovar silenciosamente uma peça na revisão antiga.

## Limites e integração real

- Recebimentos, ator e revisão de marca são fornecidos pelo chamador. A ferramenta não autentica usuários, consulta anexos remotos, verifica a correspondência do payload inline com um documento remoto, nem atesta a autenticidade de um recibo. O agente/integração deve consultar a API e usar as respostas reais.
- O estado inicial e o histórico devem vir de armazenamento confiável. Quem pode editar arbitrariamente o JSON pode fabricar uma narrativa de aprovação; este helper não é uma fronteira de segurança nem assinatura digital.
- Não há monitoramento em segundo plano: a verificação de bytes ocorre durante validação, submissão, aceite e aprovação. A integridade de uma entrega já aprovada exige retenção imutável dos anexos ou nova conferência.
- O helper não cria issues, dependências, reviews, interações humanas, uploads ou wakeups e não marca tarefas done. O Editorial deve aplicar os gates nativos e persistir resultados com CAS. Se a marca exige humano, configurar também o approval nativo `human_only`; `human_approval_required` não substitui esse controle.
- Não cobre limites financeiros, rotinas/coalescência, capacidade dos adapters, licença real, qualidade/veracidade editorial, alterações do contexto bloqueado, campanhas multipeças ou publicação em redes.

Os testes usam PNGs mínimos e recibos fictícios explicitamente identificados, sem rede. Eles comprovam apenas os controles locais descritos. Não comprovam a operação real dos quatro agentes, autenticação, geração de imagens ou publicação.
