#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the loopback-only Dictionary Repair Desk."""
import json
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from repair_desk import (DICTIONARY_ROOT, REPO_ROOT, RepairData,
                         DESK_JS, RepairDeskHandler, RepairDeskServer,
                         create_issue, create_issue_if_unique,
                         find_existing_issues)


class Completed:
    returncode = 0
    stdout = 'https://github.com/milluk/miluk.org/issues/99999\n'
    stderr = ''


class Result:
    def __init__(self, stdout='', stderr='', returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def candidate_body(story_id='t055-the-trickster-person-who-made-the-country',
                   line=622, state_schema='miluk-dictionary-correction-candidate/1',
                   source='corpus', field='miluk_ascii', before='old-ascii',
                   after='new-ascii'):
    candidate = {
        'schema': state_schema,
        'target': {
            'source': source,
            'story_id': story_id,
            'line': line,
            'field': field,
        },
        'before': {'miluk_ascii': before},
        'after': {'miluk_ascii': after},
    }
    return ('Issue prose\n\n### Structured candidate\n\n```json\n' +
            json.dumps(candidate) + '\n```\n')


def issue_record(number, body, state='OPEN'):
    return {
        'number': number,
        'title': 'Candidate {}'.format(number),
        'state': state,
        'url': 'https://github.com/milluk/miluk.org/issues/{}'.format(number),
        'updatedAt': '2026-08-31T12:34:56Z',
        'body': body,
    }


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
        self.assertIn('Existing correction candidates', javascript)
        self.assertIn('Checking GitHub Issues', javascript)
        self.assertIn('No existing correction candidate was found', javascript)
        self.assertIn("createButton.hidden = !lookupReady || lookupHasMatches", javascript)
        for credential_name in ('GITHUB_TOKEN', 'GH_TOKEN', 'Authorization:', 'gho_'):
            self.assertNotIn(credential_name, javascript)

    def test_lookup_with_no_match_succeeds_and_allows_creation(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return Result(stdout='[]')

        matches = find_existing_issues(
            self.data.context(
                't055-the-trickster-person-who-made-the-country', 622),
            'milluk/miluk.org', runner=runner)
        self.assertEqual(matches, [])
        self.assertEqual(calls[0][:3], ['gh', 'issue', 'list'])
        self.assertIn('--state', calls[0])
        self.assertIn('all', calls[0])
        self.assertNotIn('create', calls[0])

    def test_lookup_returns_open_match_metadata_and_ascii_values(self):
        calls = []
        record = issue_record(
            41, candidate_body(before='ha:<:: k!&s:<le', after='ha:<:: k!&e:<le'))

        def runner(command, **kwargs):
            calls.append(command)
            return Result(stdout=json.dumps([record]))

        context = self.data.context(
            't055-the-trickster-person-who-made-the-country', 622)
        matches = find_existing_issues(
            context,
            'milluk/miluk.org', runner=runner)
        self.assertEqual(matches, [{
            'number': 41,
            'title': 'Candidate 41',
            'state': 'open',
            'url': 'https://github.com/milluk/miluk.org/issues/41',
            'updated_at': '2026-08-31T12:34:56Z',
            'before_miluk_ascii': 'ha:<:: k!&s:<le',
            'after_miluk_ascii': 'ha:<:: k!&e:<le',
        }])
        with self.assertRaises(FileExistsError):
            create_issue_if_unique(
                context, 'ha:<:: k!&e:<le n@x;-he<mq!etc.',
                'milluk/miluk.org', runner=runner)
        self.assertTrue(all(command[:3] == ['gh', 'issue', 'list']
                            for command in calls))

    def test_lookup_returns_closed_match_and_blocks_creation(self):
        calls = []
        record = issue_record(42, candidate_body(), state='CLOSED')

        def runner(command, **kwargs):
            calls.append(command)
            return Result(stdout=json.dumps([record]))

        context = self.data.context(
            't055-the-trickster-person-who-made-the-country', 622)
        self.assertEqual(find_existing_issues(
            context, 'milluk/miluk.org', runner=runner)[0]['state'], 'closed')
        with self.assertRaises(FileExistsError):
            create_issue_if_unique(
                context, 'ha:<:: k!&e:<le n@x;-he<mq!etc.',
                'milluk/miluk.org', runner=runner)
        self.assertTrue(all(command[:3] == ['gh', 'issue', 'list']
                            for command in calls))

    def test_lookup_returns_all_exact_matches(self):
        records = [
            issue_record(43, candidate_body(before='a', after='b')),
            issue_record(44, candidate_body(before='a', after='c'), state='CLOSED'),
        ]

        def runner(command, **kwargs):
            return Result(stdout=json.dumps(records))

        matches = find_existing_issues(
            self.data.context(
                't055-the-trickster-person-who-made-the-country', 622),
            'milluk/miluk.org', runner=runner)
        self.assertEqual([item['number'] for item in matches], [43, 44])

    def test_lookup_ignores_malformed_unrelated_and_wrong_targets(self):
        records = [
            issue_record(50, '### Structured candidate\n\n```json\n{broken\n```'),
            issue_record(51, '```json\n' + json.dumps({
                'schema': 'miluk-dictionary-correction-candidate/1',
                'target': {'source': 'corpus',
                           'story_id': 't055-the-trickster-person-who-made-the-country',
                           'line': 622, 'field': 'miluk_ascii'},
            }) + '\n```'),
            issue_record(52, candidate_body(story_id='t054-wrong-story')),
            issue_record(53, candidate_body(line=621)),
            issue_record(54, candidate_body(state_schema='wrong-schema')),
            issue_record(55, candidate_body(source='dictionary')),
            issue_record(56, candidate_body(field='english')),
            issue_record(57, 'No structured data at all'),
        ]
        records[-1]['title'] = ('[Dictionary correction] t055 line 622: '
                                'looks like an exact match')

        def runner(command, **kwargs):
            return Result(stdout=json.dumps(records))

        matches = find_existing_issues(
            self.data.context(
                't055-the-trickster-person-who-made-the-country', 622),
            'milluk/miluk.org', runner=runner)
        self.assertEqual(matches, [])

    def test_lookup_failure_fails_closed_without_issue_create(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return Result(stderr='network unavailable', returncode=1)

        with self.assertRaisesRegex(RuntimeError, 'network unavailable'):
            create_issue_if_unique(
                self.data.context(
                    't055-the-trickster-person-who-made-the-country', 622),
                'ha:<:: k!&e:<le n@x;-he<mq!etc.',
                'milluk/miluk.org', runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ['gh', 'issue', 'list'])

    def test_issue_creation_is_unchanged_after_empty_lookup(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            if command[:3] == ['gh', 'issue', 'list']:
                return Result(stdout='[]')
            return Completed()

        url, body = create_issue_if_unique(
            self.data.context(
                't055-the-trickster-person-who-made-the-country', 622),
            'ha:<:: k!&e:<le n@x;-he<mq!etc.', 'milluk/miluk.org',
            summary='Correct the attested form.', runner=runner)
        self.assertEqual(url, Completed.stdout.strip())
        self.assertEqual(calls[0][0][:3], ['gh', 'issue', 'list'])
        self.assertEqual(calls[1][0][:3], ['gh', 'issue', 'create'])
        self.assertEqual(calls[1][1]['input'], body)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for browser asset tests')
    def test_browser_desk_is_enabled_by_the_loopback_server(self):
        harness = r'''const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');

function visit(href) {
  const current = new URL(href);
  const queued = [];
  const controls = {};
  function control() {
    return {value: '', disabled: false, textContent: '', className: '',
            addEventListener() {}, innerHTML: ''};
  }
  function element(tag) {
    const item = {tagName: tag, id: '', className: '', textContent: '',
                  innerHTML: '', open: false, children: [],
                  appendChild(child) {
                    this.children.push(child);
                    if (child.className === 'repair-queue') queued.push(child);
                  },
                  addEventListener() {},
                  showModal() { this.open = true; }, close() { this.open = false; },
                  querySelector(selector) {
                    if (tag === 'li' && selector === 'a.formlink') {
                      return {href: 'http://127.0.0.1:8000/dictionary/stories/t055-the-trickster-person-who-made-the-country.html#l622'};
                    }
                    if (!controls[selector]) controls[selector] = control();
                    return controls[selector];
                  }};
    return item;
  }
  const line = element('div'); line.id = 'l622';
  const form = element('li');
  const document = {
    head: element('head'), body: element('body'),
    createElement: element,
    querySelectorAll(selector) {
      if (selector === '#story .line') return [line];
      if (selector === '.formlist > li') return [form];
      return [];
    }
  };
  const sandbox = {
    URL, URLSearchParams, document, location: current,
    setTimeout() { return 1; }, clearTimeout() {}, fetch() {}, console
  };
  sandbox.window = sandbox;
  sandbox.window.DICTIONARY_REPAIR_DESK_CONFIG = {token: 'test-token'};
  vm.runInNewContext(source, sandbox);
  return queued.length;
}

const word = 'http://127.0.0.1:8000/dictionary/words/e0515-kele.html';
const story = 'http://127.0.0.1:8000/dictionary/stories/t055-the-trickster-person-who-made-the-country.html';
const results = [];
results.push(visit(word));
results.push(visit(story));
results.push(visit(word + '?view=full&desk=0&lang=miluk#forms'));
results.push(visit(story + '?view=full&desk=1&lang=miluk#l622'));
process.stdout.write(JSON.stringify(results));'''
        result = subprocess.run(
            ['node', '-e', harness, str(DESK_JS)], check=True,
            text=True, capture_output=True)
        visits = json.loads(result.stdout)

        self.assertEqual(visits, [1, 1, 1, 1])
        javascript = DESK_JS.read_text(encoding='utf-8')
        self.assertNotIn('sessionStorage', javascript)
        self.assertNotIn("searchParams.get('desk')", javascript)

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
            if command[:3] == ['gh', 'issue', 'list']:
                return Result(stdout='[]')
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

            lookup = Request(
                base + '/__repair/issues/lookup', method='POST',
                headers={
                    'Content-Type': 'application/json',
                    'Origin': base,
                    'X-Repair-Desk-Token': token,
                },
                data=json.dumps({
                    'story_id': 't055-the-trickster-person-who-made-the-country',
                    'line': 622,
                }).encode('utf-8'))
            with urlopen(lookup) as response:
                lookup_result = json.loads(response.read())
            self.assertTrue(lookup_result['can_create'])
            self.assertEqual(lookup_result['matches'], [])
            self.assertEqual(set(lookup_result), {'schema', 'matches', 'can_create'})

            forbidden_lookup = Request(
                base + '/__repair/issues/lookup', method='POST',
                headers={'Content-Type': 'application/json', 'Origin': base},
                data=b'{}')
            with self.assertRaises(HTTPError) as caught:
                urlopen(forbidden_lookup)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()

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
            self.assertEqual([command[:3] for command in calls], [
                ['gh', 'issue', 'list'],
                ['gh', 'issue', 'list'],
                ['gh', 'issue', 'create'],
            ])

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
