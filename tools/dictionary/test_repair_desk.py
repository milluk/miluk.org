#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the loopback-only Dictionary Repair Desk."""
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from repair_desk import (DICTIONARY_ROOT, REPO_ROOT, RepairData,
                         DESK_JS, RepairDeskHandler, RepairDeskServer, create_issue)


class Completed:
    returncode = 0
    stdout = 'https://github.com/milluk/miluk.org/issues/99999\n'
    stderr = ''


class RepairDeskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = RepairData()

    def test_t055_line_622_suggests_documented_candidate(self):
        context = self.data.context(
            't055-the-trickster-person-who-made-the-country', 622,
            'e0515-kele', 25)
        self.assertEqual(
            context['current']['miluk_ascii'],
            'ha:<:: k!&s:<le n@x;-he<mq!etc.')
        self.assertEqual(
            context['proposed']['miluk_ascii'],
            'ha:<:: k!&e:<le n@x;-he<mq!etc.')
        self.assertEqual(context['related_dictionary'][0]['entry_id'], 'e0515-kele')
        self.assertEqual(
            context['related_dictionary'][0]['selected_form']['ascii'],
            'k!&s:<le')
        self.assertEqual(
            context['proposed']['miluk'],
            'há··· k̯̓ɛ́·lɛ nəx̣-hɛ́mq̓ɛtc.')

    def test_browser_asset_has_explicit_controls_and_no_github_credential(self):
        javascript = DESK_JS.read_text(encoding='utf-8')
        self.assertIn('Queue correction', javascript)
        self.assertIn('Create GitHub Issue', javascript)
        for credential_name in ('GITHUB_TOKEN', 'GH_TOKEN', 'Authorization:', 'gho_'):
            self.assertNotIn(credential_name, javascript)

    def test_issue_is_structured_and_uses_gh_without_shell(self):
        context = self.data.context(
            't055-the-trickster-person-who-made-the-country', 622,
            'e0515-kele', 25)
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return Completed()

        protected = [
            REPO_ROOT / 'dictionary/data/corpus.json',
            REPO_ROOT / 'dictionary/data/dictionary.json',
            REPO_ROOT / 'dictionary/data/correction-ledger.json',
            REPO_ROOT / '_config.yml',
            REPO_ROOT / 'tools/dictionary/PUBLICATION_HOLD.md',
        ]
        before = {path: path.read_bytes() for path in protected}
        url, body = create_issue(
            context, 'ha:<:: k!&e:<le n@x;-he<mq!etc.',
            'milluk/miluk.org', 'Correct k!&s:<le to k!&e:<le.',
            'Focused review candidate.', runner=runner)
        after = {path: path.read_bytes() for path in protected}

        self.assertEqual(url, Completed.stdout.strip())
        self.assertEqual(before, after)
        self.assertEqual(len(calls), 1)
        command, kwargs = calls[0]
        self.assertEqual(command[:3], ['gh', 'issue', 'create'])
        self.assertIn('--body-file', command)
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['input'], body)
        self.assertIn('miluk-dictionary-correction-candidate/1', body)
        self.assertIn('"status": "candidate"', body)
        self.assertIn('"story_id": "t055-the-trickster-person-who-made-the-country"', body)
        self.assertIn('"line": 622', body)
        self.assertIn('"miluk_ascii": "ha:<:: k!&s:<le n@x;-he<mq!etc."', body)
        self.assertIn('"miluk_ascii": "ha:<:: k!&e:<le n@x;-he<mq!etc."', body)

    def test_loopback_server_injects_desk_without_changing_generated_page(self):
        page = (DICTIONARY_ROOT / 'stories' /
                't055-the-trickster-person-who-made-the-country.html')
        page_before = page.read_bytes()
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return Completed()

        token = 'unit-test-session-token'
        server = RepairDeskServer(
            ('127.0.0.1', 0), RepairDeskHandler, self.data, token,
            'milluk/miluk.org', issue_runner=runner)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:{}'.format(server.server_port)
        try:
            with urlopen(base + '/dictionary/stories/' + page.name) as response:
                served = response.read().decode('utf-8')
            self.assertIn('<script src="/__repair/desk.js"></script>', served)
            self.assertNotIn('/__repair/desk.js', page_before.decode('utf-8'))

            with urlopen(base + '/__repair/context?story_id=' +
                         't055-the-trickster-person-who-made-the-country&line=622') as response:
                context = json.loads(response.read())
            self.assertEqual(context['story']['line'], 622)

            request = Request(
                base + '/__repair/issues', method='POST',
                headers={
                    'Content-Type': 'application/json',
                    'Origin': base,
                    'X-Repair-Desk-Token': token,
                },
                data=json.dumps({
                    'story_id': 't055-the-trickster-person-who-made-the-country',
                    'line': 622,
                    'entry_id': 'e0515-kele',
                    'form_index': 25,
                    'proposed_ascii': 'ha:<:: k!&e:<le n@x;-he<mq!etc.',
                    'summary': 'Correct k!&s:<le to k!&e:<le.',
                }).encode('utf-8'))
            with urlopen(request) as response:
                created = json.loads(response.read())
            self.assertEqual(created['issue_url'], Completed.stdout.strip())
            self.assertEqual(calls[0][:3], ['gh', 'issue', 'create'])

            forbidden = Request(
                base + '/__repair/issues', method='POST',
                headers={'Content-Type': 'application/json', 'Origin': base},
                data=b'{}')
            with self.assertRaises(HTTPError) as caught:
                urlopen(forbidden)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(page.read_bytes(), page_before)


if __name__ == '__main__':
    unittest.main()
