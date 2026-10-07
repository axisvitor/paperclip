"""Publish the local playbook and validator using a board-authorized API session."""
import hashlib
from urllib.parse import quote
from paperclip_api import API, ROOT, records, save_records


def publish_playbook_document(api, state):
    iid = state['issues']['operations']['id']
    docpath = f'/api/issues/{iid}/documents/production-playbook'
    doc = api.request('GET', docpath)
    body = (ROOT / 'playbooks/SKILL.md').read_text()
    if doc['body'] == body:
        return
    was_locked = bool(doc.get('lockedAt'))
    try:
        if was_locked:
            api.request('POST', docpath + '/unlock', {})
        # API.document reads the current revision and performs a CAS upsert.
        api.document(iid, 'production-playbook', 'Playbook da produção', body)
    finally:
        # Also attempt restoration when the unlock/update response is uncertain.
        # A relock failure propagates; it must never be reported as a publication.
        if was_locked:
            locked = api.request('POST', docpath + '/lock', {})
    if not was_locked:
        locked = api.request('POST', docpath + '/lock', {})
    state['documents']['playbook'] = locked
    save_records(state)


def main():
    api = API()
    state = records()
    cid = state['company_id']
    sid = state['skills']['production']['id']
    path = f'/api/companies/{cid}/skills/{sid}'
    for source, target in [('playbooks/SKILL.md', 'SKILL.md'),
                           ('automation/contracts.py', 'scripts/contracts.py'),
                           ('automation/README.md', 'references/contracts.md')]:
        content = (ROOT / source).read_text()
        current = api.request('GET', path)
        if any(f['path'] == target for f in current['fileInventory']):
            existing = api.request('GET', path + '/files?path=' + quote(target, safe=''))
            if existing['content'] == content:
                continue
        api.request('PATCH', path + '/files', {
            'path': target, 'content': content,
            'expectedVersionId': current['currentVersionId'],
            'idempotencyKey': 'social-media:file:' + target + ':' + hashlib.sha256(content.encode()).hexdigest()[:20]})

    publish_playbook_document(api, state)
    api.document(state['issues']['operations']['id'], 'contract-reference', 'Contrato executável v1 e limites',
                 (ROOT / 'automation/README.md').read_text())
    print('Playbook, validator and reference published with version checks.')


if __name__ == '__main__':
    main()
