"""Read-only checks of the configured company; policy evaluation does not mutate."""
import hashlib
import json
from urllib.parse import quote
from paperclip_api import API, ROOT, records

api = API()
state = records()
cid = state['company_id']
checks = []


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    checks.append(message)


company = api.request('GET', f'/api/companies/{cid}')
check(company['status'] == 'paused', 'Empresa pausada')
check(company['requireBoardApprovalForNewAgents'], 'Governança de contratação preservada')
agents = api.request('GET', f'/api/companies/{cid}/agents')
check(len(agents) == 4, 'Exatamente quatro agentes')
editorial = state['agents']['editorial']['id']
for key, record in state['agents'].items():
    agent = next(a for a in agents if a['id'] == record['id'])
    check(agent['status'] == 'paused' and agent['role'] == record['role'], f'{key}: papel correto e pausado')
    check(agent.get('reportsTo') == (None if key == 'editorial' else editorial), f'{key}: hierarquia correta')
    config = api.request('GET', f"/api/agents/{agent['id']}/configuration")
    hb = config['runtimeConfig']['heartbeat']
    check(hb['enabled'] is False and hb['wakeOnDemand'] is False and hb['maxConcurrentRuns'] == 1,
          f'{key}: timers/wake desligados, concorrência 1')
    ac = config['adapterConfig']
    check(config['adapterType'] == 'codex_local' and ac['engine'] == 'cli' and
          ac['dangerouslyBypassApprovalsAndSandbox'] is False, f'{key}: adapter explícito sem bypass')
    approval = api.request('GET', f"/api/approvals/{record['approval_id']}")
    check(approval['status'] == 'approved', f'{key}: contratação aprovada')
    decision = api.request('POST', f'/api/companies/{cid}/skill-policy/evaluate', {
        'principal': {'agentId': agent['id']}, 'action': 'skills.edit',
        'resource': {'skillId': state['skills']['production']['id']}})
    check(decision['allowed'] is False, f'{key}: edição de skill impedida por policy')

brand_context_revision = None
for issue_key, keys in [('operations', ['architecture', 'production-playbook']), ('brand', ['brand-context', 'brand-publication'])]:
    for key in keys:
        doc = api.request('GET', f"/api/issues/{state['issues'][issue_key]['id']}/documents/{key}")
        check(bool(doc['lockedAt']) and bool(doc['latestRevisionId']), f'{key}: documento versionado e bloqueado')
        if key == 'brand-context':
            brand_context_revision = doc['latestRevisionId']
        if key == 'brand-publication':
            publication = json.loads(doc['body'].split('```json\n', 1)[1].split('```', 1)[0])
            check(publication['status'] == 'awaiting_brand_input' and publication['approved_revision_id'] is None,
                  'Contexto pendente não declarado aprovado')
            check(publication['brand_id'] == cid and
                  publication['draft_revision_id'] == brand_context_revision ==
                  state['documents']['brand_context']['latestRevisionId'],
                  'Marca e revisão de rascunho resolvidas para esta empresa')

sid = state['skills']['production']['id']
for source, target in [('playbooks/SKILL.md', 'SKILL.md'), ('automation/contracts.py', 'scripts/contracts.py'),
                       ('automation/README.md', 'references/contracts.md')]:
    detail = api.request('GET', f'/api/companies/{cid}/skills/{sid}/files?path=' + quote(target, safe=''))
    check(detail['content'] == (ROOT / source).read_text(), f'Skill contém versão exata de {target}')

root = state['templates']['carousel']['issue_id']
doc = api.request('GET', f'/api/issues/{root}/documents/workflow')
workflow = json.loads(doc['body'].split('```json\n', 1)[1].split('```', 1)[0])
check(workflow['template_only'] and workflow['stage'] == 'IDEA', 'Carrossel identificado como modelo')
prior = state['issues']['brand']['id']
for stage in ('research', 'brief', 'copy', 'design'):
    entry = workflow['tasks'][stage]
    issue = api.request('GET', f"/api/issues/{entry['id']}")
    check(issue['status'] == 'backlog' and issue['parentId'] == root and issue['assigneeAgentId'] == entry['executor_id'],
          f'{stage}: subtarefa atribuída sem admissão')
    check(prior in [b['id'] for b in issue['blockedBy']], f'{stage}: dependência nativa correta')
    if stage != 'brief':
        gate = issue['executionPolicy']['stages'][0]
        check(gate['type'] == 'review' and gate['participants'][0]['agentId'] == editorial,
              f'{stage}: revisão editorial configurada')
    prior = issue['id']

routines = api.request('GET', f'/api/companies/{cid}/routines')
check(len(routines) == 2 and all(r['status'] == 'paused' and r['concurrencyPolicy'] == 'coalesce_if_active'
                               and r['catchUpPolicy'] == 'skip_missed' for r in routines),
      'Duas rotinas pausadas com coalescência e sem recuperação de períodos perdidos')
brand_issue = api.request('GET', f"/api/issues/{state['issues']['brand']['id']}")
check(brand_issue['status'] == 'backlog' and not brand_issue.get('activeRecoveryAction'),
      'Entrada da marca em espera intencional sem recuperação ativa')
check(api.request('GET', f'/api/companies/{cid}/heartbeat-runs') == [], 'Nenhuma execução de agente iniciada')
check(api.request('GET', f'/api/companies/{cid}/live-runs') == [], 'Nenhuma execução ativa')

print(json.dumps({'passed': len(checks), 'checks': checks}, ensure_ascii=False, indent=2))
