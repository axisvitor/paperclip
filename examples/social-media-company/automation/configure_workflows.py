"""Prepare native governance, paused routine and non-executing workflow templates."""
import json
from paperclip_api import API, records, save_records
from intake import create_request

api = API()
state = records()
cid = state['company_id']
if api.request('GET', f'/api/companies/{cid}')['status'] != 'paused':
    raise RuntimeError('Workflow setup requires the company to remain paused')

policy_path = f'/api/companies/{cid}/skill-policy'
policy = api.request('GET', policy_path)
rule = {'id': 'social-media-skills-board-only', 'priority': -1000, 'effect': 'deny',
        'subject': {'type': 'all_agents'},
        'actions': ['skills.create', 'skills.import', 'skills.install', 'skills.edit',
                    'skills.update', 'skills.test', 'skills.reset', 'skills.remove']}
if not any(r['id'] == rule['id'] for r in policy['rules']):
    api.request('PUT', policy_path, {'schemaVersion': 1, 'expectedRevision': policy['revision'],
                                    'defaultEffect': policy['defaultEffect'], 'rules': policy['rules'] + [rule]})

brand = state['issues']['brand']['id']
if not state.get('brand_interaction_id'):
    interaction = api.request('POST', f'/api/issues/{brand}/interactions', {
        'kind': 'ask_user_questions', 'title': 'Contexto inicial da marca',
        'summary': 'Dados reais para preparar a revisão oficial do contexto compartilhado.',
        'idempotencyKey': 'social-media:v1:brand-intake', 'resolverPolicy': 'human_only',
        'continuationPolicy': 'none',
        'payload': {'version': 1, 'questionSet': {'schema': 'paperclip.question_set.v1', 'questions': [
            {'id': 'brand_context', 'answerMode': 'text', 'required': True,
             'prompt': 'Revise os dados já registrados no documento brand-context desta tarefa, incluindo marca/empresa, nicho, público, produtos/serviços e canais. Informe apenas correções ou campos pendentes: posicionamento, objetivos, fontes oficiais, identidade visual, paleta, tipografia, tom, referências e restrições disponíveis. Declare o que ainda não estiver definido; não envie senhas ou chaves.'},
            {'id': 'operation_limits', 'answerMode': 'text', 'required': True,
             'prompt': 'Informe responsável pela marca, aprovação editorial ou editorial seguida de aprovação humana, orçamento mensal com moeda e volume/prazos iniciais. Declare itens pendentes.'}
        ]}}})
    state['brand_interaction_id'] = interaction['id']
    save_records(state)
    api.request('GET', f'/api/issues/{brand}')
    # This is staged onboarding, not an active review. A paused company plus
    # continuationPolicy=none is not a live review path for native recovery.
    # Keep the human question pending and the existing assignee in backlog.
    api.request('PATCH', f'/api/issues/{brand}', {'status': 'backlog',
        'comment': 'Configuração em backlog, aguardando a interação Contexto inicial da marca. A pergunta permanece pendente e o responsável é preservado. Resposta prepara uma revisão; não aprova automaticamente a marca nem retoma empresa/agentes. A produção será admitida após verificar os pré-requisitos.'})

routines = state.setdefault('routines', {})
for key, title, description, variables in [
    ('manual', 'Nova demanda de conteúdo',
     'Pedido: {{pedido}}\nUsar social-media-production. Resolver contexto aprovado e normalizar campanha ou peça. Criar workflow, etapas com dependências e gates, respeitando capacidade e orçamento. Não inventar dados ausentes.',
     [{'name': 'pedido', 'label': 'Demanda de conteúdo', 'type': 'textarea', 'required': True}]),
    ('intelligence', 'Rodada de inteligência editorial',
     'Consultar marca aprovada, fontes e objetivos; coordenar Pesquisa para oportunidades e pautas. Editorial seleciona as pautas; abrir produção apenas dentro do calendário, canais, capacidade e orçamento configurados. Sem agenda definida, manter pausada.', [])]:
    if key not in routines:
        existing = [r for r in api.request('GET', f'/api/companies/{cid}/routines') if r['title'] == title]
        if len(existing) > 1:
            raise RuntimeError('Multiple matching routines; reconcile before proceeding')
        routine = existing[0] if existing else api.request('POST', f'/api/companies/{cid}/routines', {
            'title': title, 'description': description, 'projectId': state['projects']['production']['id'],
            'assigneeAgentId': state['agents']['editorial']['id'], 'status': 'paused',
            'concurrencyPolicy': 'coalesce_if_active', 'catchUpPolicy': 'skip_missed',
            'variables': variables})
        routines[key] = {'id': routine['id'], 'title': title}
        save_records(state)

templates = state.setdefault('templates', {})
for key, request_id, pedido, kind, fmt in [
    ('carousel', 'social-media-v1-template-carousel', 'Carrossel educativo sobre tema a definir', 'content', 'carousel'),
    ('campaign', 'social-media-v1-template-campaign', 'Campanha para produto a definir', 'campaign', None)]:
    result = create_request(request_id, pedido, kind, fmt, template=True)
    templates[key] = result
    save_records(state)
if 'pilot' not in state['issues']:
    issue = api.request('POST', f'/api/companies/{cid}/issues', {
        'idempotencyKey': 'social-media:v1:issue:pilot',
        'title': 'Validar piloto antes de habilitar recorrência',
        'description': 'Após contexto e ferramentas prontos, executar post e carrossel reais e os cenários de aceite. Registrar evidências de fontes, arquivos, gates e correções. A validação do piloto libera a recorrência; não bloqueia a preparação das próprias peças do piloto.',
        'status': 'backlog', 'projectId': state['projects']['governance']['id'],
        'assigneeAgentId': state['agents']['editorial']['id'],
        'blockedByIssueIds': [state['issues']['brand']['id'], state['issues']['activation']['id']]})
    state['issues']['pilot'] = {'id': issue['id'], 'identifier': issue['identifier']}
state['provisioned'] = True
save_records(state)
print(json.dumps({'routines': routines, 'templates': templates,
                  'brand_interaction_id': state['brand_interaction_id']}, ensure_ascii=False, indent=2))
