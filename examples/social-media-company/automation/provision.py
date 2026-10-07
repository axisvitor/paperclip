"""Prepare an inactive Social Media company. Safe to resume using saved receipts."""
import json
import re
from paperclip_api import API, ROOT, records, save_records

api = API()
state = records()

def company_config():
    config = json.loads((ROOT / 'company.json').read_text())
    if not isinstance(config, dict) or any(not isinstance(config.get(key), str) or not config[key].strip()
                                           for key in ('name', 'description')):
        raise ValueError('company.json requires nonempty name and description strings')
    return {key: config[key].strip() for key in ('name', 'description')}


def brand_context_body(company_id):
    source = (ROOT / 'CONTEXTO-MARCA.yaml').read_text()
    entries = re.findall(r'^  brand_id:.*$', source, flags=re.MULTILINE)
    resolved = f'  brand_id: {company_id}'
    if len(entries) != 1 or entries[0] not in ('  brand_id: null', resolved):
        raise ValueError('Brand template must contain one brand_id placeholder or this company ID')
    return ('Contexto inicial pendente de revisão e aprovação. Não habilita produção.\n\n```yaml\n' +
            source.replace(entries[0], resolved, 1) + '```\n')


def create_initial():
    config = company_config()
    if not state.get('company_id'):
        existing = [c for c in api.request('GET', '/api/companies')
                    if c['name'] == config['name'] and c.get('description') == config['description']]
        if existing:
            raise RuntimeError('Matching company already exists without local receipts; restore or reconcile receipts before continuing')
        company = api.request('POST', '/api/companies', config)
        state['company_id'] = company['id']
        save_records(state)
    cid = state['company_id']
    company = api.request('GET', f'/api/companies/{cid}')
    if company['status'] != 'paused' or not company.get('requireBoardApprovalForNewAgents'):
        if state.get('provisioned') and company['status'] != 'paused':
            raise RuntimeError('Company already activated; this setup must not pause it again')
        api.request('PATCH', f'/api/companies/{cid}', {
            'status': 'paused', 'requireBoardApprovalForNewAgents': True})
    state['board_user_id'] = company.get('defaultResponsibleUserId') or 'local-board'
    projects = state.setdefault('projects', {})
    for key, name, description in [
        ('governance', 'Governança da marca e operação', 'Contexto oficial, arquitetura, decisões e preparação das ferramentas.'),
        ('production', 'Produção de conteúdo', 'Demandas, campanhas e peças com pesquisa, pauta, copy, design e revisão.')]:
        if key not in projects:
            project = api.request('POST', f'/api/companies/{cid}/projects', {
                'idempotencyKey': f'social-media:v1:project:{key}',
                'name': name, 'description': description, 'status': 'planned'})
            projects[key] = {'id': project['id'], 'name': project['name']}
            save_records(state)
    issues = state.setdefault('issues', {})
    for key, title, description in [
        ('operations', 'Operações da empresa — arquitetura e decisões',
         'Registro da arquitetura proposta, organograma, playbook, instruções e decisões de implantação. Sem produção de conteúdo nesta tarefa.'),
        ('brand', 'Contexto oficial da marca — aguardando dados reais',
         'Preencher os campos pendentes da marca e publicar recibo de aprovação da revisão exata. O contexto inicial não é uma marca aprovada.'),
        ('activation', 'Preparar ferramentas e orçamento',
         'Validar autenticação no runtime de cada agente, web, geração/edição e inspeção de imagens, composição tipográfica, uploads e limites financeiros. Esta tarefa libera o piloto controlado; a validação do piloto é uma tarefa separada e libera a recorrência.')]:
        if key not in issues:
            issue = api.request('POST', f'/api/companies/{cid}/issues', {
                'idempotencyKey': f'social-media:v1:issue:{key}', 'title': title,
                'description': description, 'status': 'backlog',
                'projectId': projects['governance']['id'], 'priority': 'high'})
            issues[key] = {'id': issue['id'], 'identifier': issue['identifier']}
            save_records(state)
    docs = state.setdefault('documents', {})
    architecture = api.document(issues['operations']['id'], 'architecture', 'Arquitetura operacional',
                               (ROOT / 'ARQUITETURA.md').read_text(), lock=True)
    docs['architecture'] = architecture
    brand = api.document(issues['brand']['id'], 'brand-context', 'Contexto oficial da marca — rascunho protegido',
                         brand_context_body(cid), lock=True)
    docs['brand_context'] = brand
    save_records(state)
    print(json.dumps({'company_id': cid, 'projects': projects, 'issues': issues,
                      'document_shapes': {k: list(v) if isinstance(v, dict) else type(v).__name__ for k,v in docs.items()}}, ensure_ascii=False, indent=2))


def create_team():
    cid = state['company_id']
    if api.request('GET', f'/api/companies/{cid}')['status'] != 'paused':
        raise RuntimeError('Provisioning requires the company to remain paused')
    skills = api.request('GET', f'/api/companies/{cid}/skills')
    native = next(s for s in skills if s['slug'] == 'paperclip')
    existing = next((s for s in skills if s['slug'] == 'social-media-production'), None)
    skill = existing or api.request('POST', f'/api/companies/{cid}/skills', {
        'idempotencyKey': 'social-media:v1:skill:production',
        'name': 'social-media-production', 'slug': 'social-media-production',
        'description': 'Contratos, gates, handoffs e produção coordenada de Social Media.',
        'markdown': (ROOT / 'playbooks/SKILL.md').read_text(), 'sharingScope': 'company'})
    state['skills'] = {'paperclip': {'id': native['id'], 'key': native['key']},
                       'production': {'id': skill['id'], 'key': skill['key']}}
    save_records(state)
    context = ('# Referências oficiais desta empresa\n\n'
               f"Empresa: {cid}.\n\n"
               f"Arquitetura: issue {state['issues']['operations']['id']} ({state['issues']['operations']['identifier']}), documento `architecture`.\n\n"
               f"Contexto: issue {state['issues']['brand']['id']} ({state['issues']['brand']['identifier']}), documentos `brand-context` e `brand-publication`.\n\n"
               f"Prontidão e ferramentas: issue {state['issues']['activation']['id']} ({state['issues']['activation']['identifier']}).\n\n"
               'Leia esses documentos pela API autenticada do runtime e fixe as revisões aprovadas na demanda. '
               'O formulário protegido atual está pendente; lock não significa aprovação. '
               'Sem recibo aprovado e capacidades necessárias, não inicie produção. '
               'O workflow da demanda identifica os IDs das etapas e as revisões de todos os handoffs.\n\n'
               'Skills selecionadas: `paperclip` para API e coordenação; `social-media-production` para a operação. '
               f"Arquivos operacionais e validador: {ROOT / 'automation'}. "
               'O validador local auxilia contratos; não intercepta alterações diretas na API.\n')
    agents = state.setdefault('agents', {})
    specs = [
        ('editorial', 'Coordenação Editorial', 'cmo', 'Coordenador Editorial', 'target', 'Curadoria, coordenação, revisão cruzada, encaminhamento de correções e entrega.'),
        ('pesquisa', 'Pesquisa e Inteligência de Conteúdo', 'researcher', 'Analista de Pesquisa e Conteúdo', 'search', 'Pesquisa web, fontes, evidências, tendências, insights e pautas candidatas.'),
        ('copywriting', 'Copywriting', 'general', 'Copywriter', 'message-square', 'Hooks, headlines, narrativa, textos por slide, legendas e CTAs sustentados pelas evidências.'),
        ('design', 'Design e Direção Criativa', 'designer', 'Diretor de Arte e Designer', 'wand', 'Direção visual, criação e edição de imagens, composição, exportação e inspeção de criativos.')]
    for key, name, role, title, icon, capabilities in specs:
        if key not in agents:
            candidates = [a for a in api.request('GET', f'/api/companies/{cid}/agents') if a['name'] == name]
            if candidates:
                raise RuntimeError(f'Unrecorded agent {name}; reconcile before retrying a hire')
            cwd = ROOT / '.runtime' / 'workspaces' / key
            cwd.mkdir(parents=True, exist_ok=True)
            instruction = (ROOT / 'agents' / key / 'AGENTS.md').read_text().replace(
                ', em `../../playbooks/SKILL.md` neste pacote', ', instalada no runtime')
            instruction += '\nLeia também `CONTEXTO.md` deste bundle para resolver as referências oficiais.\n'
            result = api.request('POST', f'/api/companies/{cid}/agent-hires', {
                'name': name, 'role': role, 'title': title, 'icon': icon,
                'reportsTo': agents['editorial']['id'] if key != 'editorial' else None,
                'capabilities': capabilities, 'adapterType': 'codex_local',
                'adapterConfig': {'cwd': str(cwd), 'engine': 'cli',
                                  'dangerouslyBypassApprovalsAndSandbox': False,
                                  'search': key in ('pesquisa', 'editorial'),
                                  'extraArgs': ['--skip-git-repo-check'],
                                  'timeoutSec': 900, 'graceSec': 15},
                'instructionsBundle': {'entryFile': 'AGENTS.md', 'files': {'AGENTS.md': instruction, 'CONTEXTO.md': context}},
                'desiredSkills': [native['key'], skill['key']],
                'runtimeConfig': {'heartbeat': {'enabled': False, 'intervalSec': 0,
                                                'wakeOnDemand': False, 'maxConcurrentRuns': 1}},
                'permissions': {'canCreateAgents': False, 'canCreateSkills': False},
                'sourceIssueId': state['issues']['operations']['id']})
            agents[key] = {'id': result['agent']['id'], 'name': name, 'role': role,
                           'approval_id': (result.get('approval') or {}).get('id')}
            save_records(state)
        aid = agents[key]['id']
        current = api.request('GET', f'/api/agents/{aid}')
        if current['status'] == 'pending_approval':
            api.request('POST', f"/api/approvals/{agents[key]['approval_id']}/approve", {
                'decisionNote': 'Contratação aprovada pelo responsável que executou o provisionamento. Execução permanece pausada até marca, ferramentas e orçamento prontos.'})
        current = api.request('GET', f'/api/agents/{aid}')
        if current['status'] != 'paused':
            api.request('POST', f'/api/agents/{aid}/pause', {})
        print(name + ': paused')
    for project in state['projects'].values():
        api.request('GET', f"/api/projects/{project['id']}")
        api.request('PATCH', f"/api/projects/{project['id']}", {'leadAgentId': agents['editorial']['id']})
    for key in ('operations', 'brand', 'activation'):
        iid = state['issues'][key]['id']
        api.request('GET', f'/api/issues/{iid}')
        api.request('PATCH', f'/api/issues/{iid}', {'assigneeAgentId': agents['editorial']['id']})
    publication = {
        'schema_version': '1.0', 'record_kind': 'approved_brand_publication',
        'status': 'awaiting_brand_input', 'company_id': cid, 'brand_id': cid,
        'canonical_issue_id': state['issues']['brand']['id'],
        'canonical_document_id': state['documents']['brand_context']['id'],
        'canonical_document_key': 'brand-context',
        'draft_revision_id': state['documents']['brand_context']['latestRevisionId'],
        'approved_revision_id': None,
        'approved_by_user_id': None, 'approved_at': None,
        'canonical_document_lock_confirmed': True, 'approved_asset_refs': [],
        'change_summary': 'Rascunho protegido; nenhuma revisão da marca foi aprovada.'}
    state['documents']['brand_publication'] = api.document(state['issues']['brand']['id'], 'brand-publication',
        'Registro de publicação da marca — pendente', '```json\n' + json.dumps(publication, ensure_ascii=False, indent=2) + '\n```\n', lock=True)
    state['documents']['implementation'] = api.document(state['issues']['operations']['id'], 'implementation',
        'Implantação — instruções do pacote', (ROOT / 'README.md').read_text())
    state['documents']['playbook'] = api.document(state['issues']['operations']['id'], 'production-playbook',
        'Playbook da produção', (ROOT / 'playbooks/SKILL.md').read_text(), lock=True)
    save_records(state)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['initial', 'team'], default='initial', nargs='?')
    args = parser.parse_args()
    create_initial() if args.phase == 'initial' else create_team()
