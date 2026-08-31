#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loopback-only review desk for queuing dictionary correction candidates.

This server deliberately keeps candidate corrections out of the repository.
It reads the generated dictionary and its canonical inputs, then creates a
GitHub Issue through the authenticated local ``gh`` process only in response to
the desk's explicit Create Issue request.
"""
import argparse
import html
import ipaddress
import json
import mimetypes
from pathlib import Path
import re
import secrets
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit


TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]
DICTIONARY_ROOT = REPO_ROOT / 'dictionary'
DESK_JS = TOOL_DIR / 'repair_desk.js'

sys.path.insert(0, str(TOOL_DIR / 'pipeline'))
from anderson import convert as _render_ascii_piece  # noqa: E402


# Review suggestions are local affordances, not accepted corrections. The
# GitHub Issue remains the sole candidate queue; accepted changes still need a
# separate ledger-backed change and tests.
SUGGESTIONS = {
    ('t055-the-trickster-person-who-made-the-country', 622): {
        'before': 'ha:<:: k!&s:<le n@x;-he<mq!etc.',
        'after': 'ha:<:: k!&e:<le n@x;-he<mq!etc.',
        'summary': 'Correct k!&s:<le to k!&e:<le.',
    },
}


def render_miluk(value):
    """Render independently delimited source pieces without crossing spaces.

    The recovered converter searches backward when applying postfix marks. A
    space must therefore be a hard boundary so a stacked mark such as ``k!&``
    cannot attach to a letter in the preceding word.
    """
    return re.sub(r'\S+', lambda match: _render_ascii_piece(match.group(0)), value)


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def repository_slug(repo_root=REPO_ROOT):
    result = subprocess.run(
        ['git', 'config', '--get', 'remote.origin.url'], cwd=repo_root,
        text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError('cannot determine the GitHub repository from remote.origin.url')
    remote = result.stdout.strip()
    match = re.search(r'(?:github\.com[/:])([^/]+/[^/]+?)(?:\.git)?$', remote)
    if not match:
        raise RuntimeError('remote.origin.url is not a GitHub repository')
    return match.group(1)


class RepairData:
    """Read-only view of corpus and dictionary context used by the desk."""

    def __init__(self, data_dir=DICTIONARY_ROOT / 'data'):
        corpus = load_json(Path(data_dir) / 'corpus.json')
        dictionary = load_json(Path(data_dir) / 'dictionary.json')
        self.stories = {story['story_id']: story for story in corpus['stories']}
        self.entries = {entry['entry_id']: entry for entry in dictionary['entries']}

    def context(self, story_id, line_number, entry_id=None, form_index=None):
        story = self.stories.get(story_id)
        if story is None:
            raise ValueError('unknown story')
        try:
            line_number = int(line_number)
        except (TypeError, ValueError):
            raise ValueError('line must be an integer') from None
        line = next((item for item in story['lines'] if item['line'] == line_number), None)
        if line is None:
            raise ValueError('unknown story line')

        selected_form = None
        selected_entry = None
        if entry_id:
            selected_entry = self.entries.get(entry_id)
            if selected_entry is None:
                raise ValueError('unknown dictionary entry')
            if form_index is not None:
                try:
                    form_index = int(form_index)
                    selected_form = selected_entry['forms'][form_index]
                except (TypeError, ValueError, IndexError):
                    raise ValueError('unknown attested form') from None

        related_ids = list(line.get('entries', []))
        if selected_entry and entry_id not in related_ids:
            related_ids.insert(0, entry_id)
        related = []
        for related_id in related_ids:
            entry = self.entries.get(related_id)
            if entry is None:
                continue
            item = {
                'entry_id': entry['entry_id'],
                'headword_ascii': entry.get('headword_ascii') or '',
                'headword': entry.get('headword') or '',
                'gloss': entry.get('gloss') or '',
            }
            if related_id == entry_id and selected_form is not None:
                item['selected_form'] = {
                    'index': form_index,
                    'ascii': selected_form.get('ascii') or '',
                    'form': selected_form.get('form') or '',
                    'evidence': selected_form.get('evidence') or '',
                }
            related.append(item)

        current_ascii = line['miluk_ascii']
        suggestion = SUGGESTIONS.get((story_id, line_number), {})
        proposed_ascii = (suggestion.get('after')
                          if suggestion.get('before') == current_ascii
                          else current_ascii)
        return {
            'schema': 'miluk-dictionary-repair-context/1',
            'story': {
                'story_id': story_id,
                'title': story['title'],
                'line': line_number,
            },
            'current': {
                'miluk_ascii': current_ascii,
                'miluk': line['miluk'],
                'english': line.get('english') or '',
            },
            'related_dictionary': related,
            'proposed': {
                'miluk_ascii': proposed_ascii,
                'miluk': render_miluk(proposed_ascii),
                'summary': suggestion.get('summary') or '',
            },
        }


def issue_markdown(context, proposed_ascii, proposed_miluk, summary='', notes=''):
    story = context['story']
    current = context['current']
    related = context['related_dictionary']
    structured = {
        'schema': 'miluk-dictionary-correction-candidate/1',
        'status': 'candidate',
        'target': {
            'source': 'corpus',
            'story_id': story['story_id'],
            'line': story['line'],
            'field': 'miluk_ascii',
        },
        'before': {
            'miluk_ascii': current['miluk_ascii'],
            'miluk': current['miluk'],
        },
        'after': {
            'miluk_ascii': proposed_ascii,
            'miluk': proposed_miluk,
        },
        'related_dictionary': related,
        'reviewer_summary': summary.strip(),
        'reviewer_notes': notes.strip(),
    }
    related_lines = []
    for entry in related:
        line = ('- `{entry_id}` — `{headword_ascii}` / {headword}'
                .format(**entry))
        if entry.get('gloss'):
            line += ' — ' + entry['gloss']
        if entry.get('selected_form'):
            form = entry['selected_form']
            line += ('\n  - selected attested form: `{}` / {} ({})'
                     .format(form['ascii'], form['form'], form['evidence']))
        related_lines.append(line)
    if not related_lines:
        related_lines.append('- No related dictionary entry is currently linked.')

    return """## Dictionary correction candidate

This issue is a review candidate only. Acceptance requires a separate,
ledger-backed and tested correction; creating this issue does not change the
corpus, dictionary, correction ledger, or published site.

| Source | Value |
| --- | --- |
| Story | `{story_id}` — {title} |
| Line | {line_number} |
| English | {english} |

### Proposed correction

{summary}

| | 1990 ASCII | Rendered Miluk |
| --- | --- | --- |
| Before | `{before_ascii}` | {before_miluk} |
| After | `{after_ascii}` | {after_miluk} |

### Related dictionary context

{related}

### Reviewer notes

{notes}

### Structured candidate

```json
{structured}
```
""".format(
        story_id=story['story_id'], title=story['title'],
        line_number=story['line'], english=current['english'] or '—',
        summary=summary.strip() or 'No summary supplied.',
        before_ascii=current['miluk_ascii'], before_miluk=current['miluk'],
        after_ascii=proposed_ascii, after_miluk=proposed_miluk,
        related='\n'.join(related_lines), notes=notes.strip() or 'None.',
        structured=json.dumps(structured, ensure_ascii=False, indent=2),
    )


def create_issue(context, proposed_ascii, repo, summary='', notes='', runner=subprocess.run):
    proposed_ascii = proposed_ascii.strip()
    if not proposed_ascii:
        raise ValueError('proposed miluk_ascii is required')
    if len(proposed_ascii) > 4000 or len(summary) > 300 or len(notes) > 8000:
        raise ValueError('candidate text is too long')
    if proposed_ascii == context['current']['miluk_ascii']:
        raise ValueError('the proposal must differ from the current miluk_ascii')
    proposed_miluk = render_miluk(proposed_ascii)
    body = issue_markdown(context, proposed_ascii, proposed_miluk, summary, notes)
    story = context['story']
    compact = summary.strip() or '{} → {}'.format(
        context['current']['miluk_ascii'], proposed_ascii)
    compact = ' '.join(compact.split())[:120]
    title = '[Dictionary correction] {} line {}: {}'.format(
        story['story_id'].split('-', 1)[0], story['line'], compact)
    command = [
        'gh', 'issue', 'create', '--repo', repo,
        '--title', title, '--body-file', '-',
    ]
    result = runner(command, cwd=REPO_ROOT, input=body, text=True,
                    capture_output=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or 'gh issue create failed').strip()
        raise RuntimeError(detail)
    match = re.search(r'https://github\.com/[^\s]+/issues/\d+', result.stdout or '')
    if not match:
        raise RuntimeError('gh did not return a GitHub Issue URL')
    return match.group(0), body


def is_loopback_name(value):
    if value == 'localhost':
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


class RepairDeskServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, data, token, repo, issue_runner=subprocess.run):
        super().__init__(address, handler)
        self.repair_data = data
        self.repair_token = token
        self.github_repo = repo
        self.issue_runner = issue_runner


class RepairDeskHandler(BaseHTTPRequestHandler):
    server_version = 'MilukRepairDesk/1'

    def log_message(self, format_string, *args):
        sys.stderr.write('[repair desk] ' + (format_string % args) + '\n')

    def _host_allowed(self):
        host = urlsplit('//' + (self.headers.get('Host') or '')).hostname
        return bool(host and is_loopback_name(host))

    def _origin_allowed(self):
        origin = self.headers.get('Origin')
        if not origin:
            return False
        parsed = urlsplit(origin)
        return (parsed.scheme == 'http' and parsed.hostname and
                is_loopback_name(parsed.hostname) and
                parsed.port == self.server.server_port)

    def _headers(self, status, content_type, length=0):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        self.end_headers()

    def _bytes(self, payload, content_type, status=HTTPStatus.OK):
        self._headers(status, content_type, len(payload))
        self.wfile.write(payload)

    def _json(self, value, status=HTTPStatus.OK):
        payload = (json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8')
        self._bytes(payload, 'application/json; charset=utf-8', status)

    def _error(self, status, message):
        self._json({'error': message}, status)

    def _query_context(self, query):
        values = parse_qs(query, keep_blank_values=True)
        return self.server.repair_data.context(
            values.get('story_id', [''])[0], values.get('line', [''])[0],
            values.get('entry_id', [None])[0], values.get('form_index', [None])[0])

    def _read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ValueError('invalid request length') from None
        if not 0 < length <= 16384:
            raise ValueError('invalid request length')
        try:
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError('invalid JSON request') from None

    def do_GET(self):
        if not self._host_allowed():
            self._error(HTTPStatus.FORBIDDEN, 'repair desk accepts loopback hosts only')
            return
        parsed = urlsplit(self.path)
        if parsed.path == '/':
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header('Location', '/dictionary/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if parsed.path == '/__repair/context':
            try:
                self._json(self._query_context(parsed.query))
            except ValueError as error:
                self._error(HTTPStatus.BAD_REQUEST, str(error))
            return
        if parsed.path == '/__repair/desk.js':
            config = 'window.DICTIONARY_REPAIR_DESK_CONFIG = {};\n'.format(
                json.dumps({'token': self.server.repair_token}, ensure_ascii=False))
            payload = config.encode('utf-8') + DESK_JS.read_bytes()
            self._bytes(payload, 'text/javascript; charset=utf-8')
            return
        self._serve_dictionary_file(parsed.path)

    def _serve_dictionary_file(self, request_path):
        relative = unquote(request_path).lstrip('/')
        if relative == 'dictionary':
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header('Location', '/dictionary/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if relative.endswith('/'):
            relative += 'index.html'
        candidate = (REPO_ROOT / relative).resolve()
        try:
            candidate.relative_to(DICTIONARY_ROOT.resolve())
        except ValueError:
            self._error(HTTPStatus.NOT_FOUND, 'not found')
            return
        if not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, 'not found')
            return
        payload = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
        if candidate.suffix == '.html' and (
                candidate.parent == DICTIONARY_ROOT / 'stories' or
                candidate.parent == DICTIONARY_ROOT / 'words'):
            marker = b'</body>'
            injection = b'<script src="/__repair/desk.js"></script>\n'
            payload = payload.replace(marker, injection + marker, 1)
        if content_type.startswith('text/') or content_type in {'application/javascript', 'application/json'}:
            content_type += '; charset=utf-8'
        self._bytes(payload, content_type)

    def do_POST(self):
        if not self._host_allowed() or not self._origin_allowed():
            self._error(HTTPStatus.FORBIDDEN, 'same-origin loopback request required')
            return
        if not secrets.compare_digest(
                self.headers.get('X-Repair-Desk-Token') or '',
                self.server.repair_token):
            self._error(HTTPStatus.FORBIDDEN, 'invalid repair desk session')
            return
        parsed = urlsplit(self.path)
        try:
            request = self._read_json()
            context = self.server.repair_data.context(
                request.get('story_id'), request.get('line'),
                request.get('entry_id'), request.get('form_index'))
            proposed_ascii = str(request.get('proposed_ascii') or '').strip()
            if parsed.path == '/__repair/preview':
                if len(proposed_ascii) > 4000:
                    raise ValueError('candidate text is too long')
                self._json({'miluk_ascii': proposed_ascii,
                            'miluk': render_miluk(proposed_ascii)})
                return
            if parsed.path == '/__repair/issues':
                issue_url, _ = create_issue(
                    context, proposed_ascii, self.server.github_repo,
                    str(request.get('summary') or ''), str(request.get('notes') or ''),
                    runner=self.server.issue_runner)
                self._json({'issue_url': issue_url}, HTTPStatus.CREATED)
                return
            self._error(HTTPStatus.NOT_FOUND, 'not found')
        except ValueError as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
        except RuntimeError as error:
            self._error(HTTPStatus.BAD_GATEWAY, str(error))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000,
                        help='loopback port (default: 8000)')
    parser.add_argument('--repo', default=None,
                        help='GitHub owner/repository (defaults to origin)')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('--port must be between 0 and 65535')
    data = RepairData()
    repo = args.repo or repository_slug()
    token = secrets.token_urlsafe(32)
    server = RepairDeskServer(
        ('127.0.0.1', args.port), RepairDeskHandler, data, token, repo)
    url = 'http://127.0.0.1:{}/dictionary/'.format(server.server_port)
    print('Dictionary Repair Desk: ' + url, flush=True)
    print('Candidates become GitHub Issues only after Create GitHub Issue is pressed.',
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
