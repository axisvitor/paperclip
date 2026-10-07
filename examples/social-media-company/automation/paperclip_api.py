"""Small explicit Paperclip API client; no automatic write retries or secret output."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('SOCIAL_MEDIA_WORKSPACE') or PACKAGE_ROOT).expanduser().resolve()
_records_path = Path(os.environ.get('SOCIAL_MEDIA_RECORDS_PATH') or '.runtime/paperclip-records.json').expanduser()
RECEIPTS = (_records_path if _records_path.is_absolute() else ROOT / _records_path).resolve()


class API:
    def __init__(self):
        self.base = os.environ.get('PAPERCLIP_API_URL', 'http://127.0.0.1:3100').rstrip('/')
        self.key = os.environ.get('PAPERCLIP_API_KEY')

    def request(self, method, path, payload=None):
        headers = {'Accept': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            # API error bodies can include submitted values; caller gets no secrets.
            detail = json.loads(error.read() or b'{}')
            raise RuntimeError(f'{method} {path}: HTTP {error.code}: {detail.get("error", "request rejected")}') from None

    def document(self, issue_id, key, title, body, lock=False):
        path = f'/api/issues/{issue_id}/documents/{key}'
        try:
            current = self.request('GET', path)
        except RuntimeError as error:
            if 'HTTP 404:' not in str(error):
                raise
            current = None
        # GET/upsert return the document's fields directly in this Paperclip version.
        if current and current.get('body') == body:
            result = current
        else:
            if current and current.get('lockedAt'):
                raise RuntimeError(f'Canonical document {key} is locked; explicit board revision required')
            result = self.request('PUT', path, {
                'title': title, 'format': 'markdown', 'body': body,
                'baseRevisionId': current.get('latestRevisionId') if current else None,
                'changeSummary': 'Publicação do pacote operacional pelo responsável que executou o script',
            })
        if lock:
            result = self.request('POST', path + '/lock', {})
        return result


def records():
    return json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else {'schema_version': '1.0'}


def save_records(data):
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    temp = RECEIPTS.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(RECEIPTS)
