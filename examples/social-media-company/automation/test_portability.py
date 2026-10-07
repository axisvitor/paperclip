"""Offline regressions for isolated receipts, safe reuse, and canonical locks."""
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock, call, patch

import provision
import publish_playbook


CLIENT_PATH = Path(__file__).with_name('paperclip_api.py')


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        network = patch('urllib.request.urlopen', side_effect=AssertionError('Tests must remain offline'))
        network.start()
        self.addCleanup(network.stop)

    def client(self, workspace='', receipts=''):
        with patch.dict(os.environ, {'SOCIAL_MEDIA_WORKSPACE': workspace,
                                     'SOCIAL_MEDIA_RECORDS_PATH': receipts}):
            return runpy.run_path(str(CLIENT_PATH))

    def test_default_paths_are_relative_to_package_not_current_directory(self):
        client = self.client()
        expected = CLIENT_PATH.resolve().parents[1]
        self.assertEqual(client['ROOT'], expected)
        self.assertEqual(client['RECEIPTS'], expected / '.runtime/paperclip-records.json')

    def test_selected_workspace_and_relative_receipts_create_parents(self):
        client = self.client(str(self.root / 'copied-package'), '.runtime/nested/records.json')
        self.assertEqual(client['records'](), {'schema_version': '1.0'})
        state = {'schema_version': '1.0', 'company_id': 'fixture-company'}
        client['save_records'](state)
        path = self.root / 'copied-package/.runtime/nested/records.json'
        self.assertEqual(json.loads(path.read_text()), state)
        self.assertEqual(client['records'](), state)
        self.assertFalse(path.with_suffix('.tmp').exists())

    def test_absolute_receipts_remain_outside_selected_workspace(self):
        path = self.root / 'separate-state/records.json'
        client = self.client(str(self.root / 'copied-package'), str(path))
        client['save_records']({'company_id': 'fixture-company'})
        self.assertEqual(client['RECEIPTS'], path)
        self.assertTrue(path.is_file())
        self.assertFalse((self.root / 'copied-package').exists())

    def test_existing_company_without_receipts_is_never_adopted_or_paused(self):
        config = {'name': 'Fixture company', 'description': 'Fixture description'}
        (self.root / 'company.json').write_text(json.dumps(config))
        api = Mock()
        api.request.return_value = [{**config, 'id': 'existing-company', 'status': 'active'}]
        with patch.object(provision, 'ROOT', self.root), patch.object(provision, 'api', api), \
                patch.object(provision, 'state', {'schema_version': '1.0'}), \
                patch.object(provision, 'save_records') as save:
            with self.assertRaisesRegex(RuntimeError, 'without local receipts'):
                provision.create_initial()
        self.assertEqual(api.request.call_args_list, [call('GET', '/api/companies')])
        api.document.assert_not_called()
        save.assert_not_called()

    def test_brand_placeholder_resolves_repeatably_without_changing_template(self):
        path = self.root / 'CONTEXTO-MARCA.yaml'
        source = 'identity:\n  brand_id: null\n  company_name: Fixture\n'
        path.write_text(source)
        with patch.object(provision, 'ROOT', self.root):
            body = provision.brand_context_body('fixture-company')
            self.assertEqual(provision.brand_context_body('fixture-company'), body)
            self.assertEqual(path.read_text(), source)
            path.write_text(source.replace('brand_id: null', 'brand_id: fixture-company'))
            self.assertEqual(provision.brand_context_body('fixture-company'), body)
        self.assertIn('  brand_id: fixture-company\n', body)
        self.assertIn('pendente de revisão e aprovação', body)

    def test_foreign_or_duplicate_brand_ids_are_rejected(self):
        path = self.root / 'CONTEXTO-MARCA.yaml'
        with patch.object(provision, 'ROOT', self.root):
            for source in ('identity:\n  brand_id: other-company\n',
                           'identity:\n  brand_id: null\n  brand_id: null\n',
                           'identity:\n  company_name: Fixture\n'):
                with self.subTest(source=source):
                    path.write_text(source)
                    with self.assertRaisesRegex(ValueError, 'brand_id placeholder'):
                        provision.brand_context_body('fixture-company')


class PlaybookLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / 'playbooks').mkdir()
        (root / 'playbooks/SKILL.md').write_text('Updated fixture playbook')
        root_patch = patch.object(publish_playbook, 'ROOT', root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        records_patch = patch.object(publish_playbook, 'save_records')
        self.save = records_patch.start()
        self.addCleanup(records_patch.stop)
        network = patch('urllib.request.urlopen', side_effect=AssertionError('Tests must remain offline'))
        network.start()
        self.addCleanup(network.stop)
        self.state = {'issues': {'operations': {'id': 'fixture-operations'}}, 'documents': {}}
        self.path = '/api/issues/fixture-operations/documents/production-playbook'
        self.old = {'body': 'Old fixture playbook', 'lockedAt': 'fixture-lock'}
        self.locked = {'body': 'Updated fixture playbook', 'lockedAt': 'new-lock', 'latestRevisionId': 'new-revision'}
        self.api = Mock()
        self.api.request.side_effect = [self.old, {}, self.locked]

    def test_write_failure_restores_lock_and_does_not_save_success(self):
        self.api.document.side_effect = RuntimeError('CAS conflict')
        with self.assertRaisesRegex(RuntimeError, 'CAS conflict'):
            publish_playbook.publish_playbook_document(self.api, self.state)
        self.assertEqual(self.api.request.call_args_list[-1], call('POST', self.path + '/lock', {}))
        self.assertEqual(self.state['documents'], {})
        self.save.assert_not_called()

    def test_uncertain_unlock_response_still_attempts_lock_restoration(self):
        self.api.request.side_effect = [self.old, RuntimeError('Unlock response lost'), self.locked]
        with self.assertRaisesRegex(RuntimeError, 'Unlock response lost'):
            publish_playbook.publish_playbook_document(self.api, self.state)
        self.assertEqual(self.api.request.call_args_list[-1], call('POST', self.path + '/lock', {}))
        self.api.document.assert_not_called()
        self.save.assert_not_called()

    def test_relock_failure_is_not_reported_as_success(self):
        self.api.request.side_effect = [self.old, {}, RuntimeError('Relock failed')]
        with self.assertRaisesRegex(RuntimeError, 'Relock failed'):
            publish_playbook.publish_playbook_document(self.api, self.state)
        self.assertEqual(self.state['documents'], {})
        self.save.assert_not_called()

    def test_success_receipt_uses_relocked_revision(self):
        publish_playbook.publish_playbook_document(self.api, self.state)
        self.assertEqual(self.state['documents']['playbook'], self.locked)
        self.save.assert_called_once_with(self.state)
        self.assertEqual(self.api.request.call_args_list,
                         [call('GET', self.path), call('POST', self.path + '/unlock', {}),
                          call('POST', self.path + '/lock', {})])


if __name__ == '__main__':
    unittest.main()
