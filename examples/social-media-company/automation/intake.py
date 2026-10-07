"""Create manual requests/templates in backlog; never activate or run agents."""
import argparse
import hashlib
import json
import re
from paperclip_api import API, records


def create_request(request_id, pedido, kind='content', format_name=None, campaign_id=None, template=False,
                   channel=None, source_content_id=None, source_revision=None, reuse_on_whatsapp_status=False):
    if not request_id.strip() or not pedido.strip():
        raise ValueError('request_id and pedido must be nonempty')
    if kind not in ('content', 'campaign'):
        raise ValueError('kind must be content or campaign')
    if format_name not in (None, 'static_post', 'carousel', 'story', 'status'):
        raise ValueError('format must be static_post, carousel, story or status')
    if channel is not None and (not isinstance(channel, str) or not re.fullmatch(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', channel)):
        raise ValueError('channel must be a lowercase slug; recording it does not approve that network')
    if (source_content_id is None) != (source_revision is None):
        raise ValueError('source_content_id and source_revision must be supplied together')
    if source_content_id is not None and any(not isinstance(value, str) or not value.strip()
                                             for value in (source_content_id, source_revision)):
        raise ValueError('source_content_id and source_revision must be nonempty strings')
    if type(reuse_on_whatsapp_status) is not bool:
        raise ValueError('reuse_on_whatsapp_status must be a boolean')
    if kind == 'campaign' and campaign_id:
        raise ValueError('campaign cannot be nested under another campaign')
    api = API()
    state = records()
    cid = state['company_id']
    editorial = state['agents']['editorial']['id']
    prefix = 'social-media:intake:' + hashlib.sha256(request_id.encode()).hexdigest()[:32]
    intent = {'request_id': request_id, 'pedido': pedido, 'kind': kind, 'format': format_name,
              'campaign_id': campaign_id, 'template': template}
    # Omit absent options so legacy descriptions/idempotency payloads stay identical.
    requested_options = {}
    if channel is not None:
        requested_options['channel'] = channel
    if source_content_id is not None:
        source = api.request('GET', f'/api/issues/{source_content_id}')
        if source['companyId'] != cid:
            raise ValueError('Source content belongs to another company')
        requested_options.update(source_content_id=source_content_id, source_revision=source_revision)
    if reuse_on_whatsapp_status:
        requested_options['reuse_on_whatsapp_status'] = True
    intent.update(requested_options)
    if campaign_id:
        parent = api.request('GET', f'/api/issues/{campaign_id}')
        if parent['companyId'] != cid:
            raise ValueError('Campaign belongs to another company')
    label = 'MODELO — ' if template else ''
    body = ('Demanda normalizada para Coordenação Editorial. ' +
            ('Modelo de configuração, sem tema ou marca real. Não produzir.\n\n' if template else '') +
            pedido + '\n\nContexto oficial e capacidades devem ser aprovados antes da admissão. '
            'A criação permanece no backlog e não habilita a empresa.\n\n```json\n' +
            json.dumps(intent, ensure_ascii=False, indent=2) + '\n```')
    issue = api.request('POST', f'/api/companies/{cid}/issues', {
        'idempotencyKey': prefix, 'title': label + ('Campanha' if kind == 'campaign' else 'Conteúdo') + ': ' + pedido[:170],
        'description': body, 'status': 'backlog', 'projectId': state['projects']['production']['id'],
        'parentId': campaign_id, 'assigneeAgentId': editorial,
        'blockedByIssueIds': [state['issues']['brand']['id'], state['issues']['activation']['id']]})
    # Existing requests must retain the original intent. Never silently reuse a key for new work.
    if issue.get('description') != body:
        raise ValueError('request_id already belongs to a different request')
    workflow_path = f"/api/issues/{issue['id']}/documents/workflow"
    try:
        existing = api.request('GET', workflow_path)
    except RuntimeError as error:
        if 'HTTP 404:' not in str(error):
            raise
        existing = None
    if existing:
        # A retry must not reset a workflow that has already advanced.
        return {'issue_id': issue['id'], 'identifier': issue['identifier'], 'replayed': True}
    tasks = {}
    if kind == 'content':
        prior = state['issues']['brand']['id']
        for stage, agent_key, title in [
            ('research', 'pesquisa', 'Pesquisa e evidências'), ('brief', 'editorial', 'Curadoria e pauta'),
            ('copy', 'copywriting', 'Copy, legenda e CTA'), ('design', 'design', 'Criativos e revisão final')]:
            payload = {
                'idempotencyKey': prefix + ':' + stage, 'title': label + title,
                'description': f"Etapa {stage} da peça {issue['identifier']}. Usar skill social-media-production, contexto canônico e revisões fixadas. "
                               'Submeter entrega completa ao gate; rejeições retornam à causa. ' +
                               ('Esta é uma estrutura modelo, não uma ordem de produção.' if template else ''),
                'status': 'backlog', 'projectId': state['projects']['production']['id'],
                'parentId': issue['id'], 'assigneeAgentId': state['agents'][agent_key]['id'],
                'blockedByIssueIds': [prior] + ([state['issues']['activation']['id']] if stage == 'research' else [])}
            if stage != 'brief':
                payload['executionPolicy'] = {'mode': 'normal', 'commentRequired': True,
                    'stages': [{'type': 'review', 'approvalsNeeded': 1,
                                'participants': [{'type': 'agent', 'agentId': editorial}]}]}
            task = api.request('POST', f'/api/companies/{cid}/issues', payload)
            tasks[stage] = {'id': task['id'], 'identifier': task['identifier'],
                            'executor_id': state['agents'][agent_key]['id']}
            prior = task['id']
    workflow = {
        'schema_version': '1.0', 'kind': 'intake_scaffold', 'request_id': request_id,
        'scope': kind, 'company_id': cid, 'content_id': issue['id'] if kind == 'content' else None,
        'campaign_id': issue['id'] if kind == 'campaign' else campaign_id,
        'stage': 'IDEA', 'operational_status': 'blocked', 'resume_stage': 'IDEA',
        'template_only': template, 'format': format_name, 'channel': None, 'brand_ref': None,
        'brand_issue_id': state['issues']['brand']['id'], 'tasks': tasks,
        'blockers': [{'code': 'admission_required', 'owner': 'editorial_and_brand_owner',
                      'resolution': 'Conferir contexto aprovado, objetivo/canal/formato, ferramentas, orçamento e política de aprovação antes de admitir a peça.'}],
        'handoffs': {}, 'decisions': [], 'required_content_ids': [],
        'notes': 'Scaffold de entrada. Após admissão, inicializar workflow validável conforme automation/README.md. '
                 'Se exigir humano, adicionar approval após review na tarefa Design antes de executar. '
                 'Campanha só conclui após todas as required_content_ids aprovadas.'}
    workflow.update(requested_options)
    if requested_options:
        workflow['notes'] += (' Canal/formato e reaproveitamento são pedidos, não aprovações. '
                              'Uma peça de WhatsApp Status exige admissão própria, objetivo, canal/perfil aprovado '
                              'e referências exatas da origem; conferir a revisão declarada antes de produzir. '
                              'A flag não cria nem publica automaticamente uma variante.')
    api.document(issue['id'], 'workflow', 'Workflow editorial — entrada pendente',
                 '```json\n' + json.dumps(workflow, ensure_ascii=False, indent=2) + '\n```\n')
    return {'issue_id': issue['id'], 'identifier': issue['identifier'], 'tasks': tasks, 'replayed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--pedido', required=True)
    parser.add_argument('--kind', choices=['content', 'campaign'], default='content')
    parser.add_argument('--format', choices=['static_post', 'carousel', 'story', 'status'])
    parser.add_argument('--channel', help='Requested channel slug; does not approve a new network')
    parser.add_argument('--campaign-id')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--source-content-id', help='Source issue ID, together with --source-revision')
    parser.add_argument('--source-revision', help='Exact source revision, together with --source-content-id')
    parser.add_argument('--reuse-on-whatsapp-status', action='store_true',
                        help='Record a reuse request; never create or publish a WhatsApp variant automatically')
    args = parser.parse_args()
    print(json.dumps(create_request(args.request_id, args.pedido, args.kind, args.format,
                                    args.campaign_id, args.template, args.channel, args.source_content_id,
                                    args.source_revision, args.reuse_on_whatsapp_status), ensure_ascii=False, indent=2))
