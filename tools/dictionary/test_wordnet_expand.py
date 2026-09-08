"""Regression coverage for wordnet_expand.py's parser and scoring.

Uses a tiny synthetic WordNet-format fixture rather than the real database
(which is a build-time-only input, not vendored in this repository — see
provenance/WORDNET_SOURCE.md), so this test has no network dependency and no
external data dependency.
"""
import json
import tempfile
import unittest
from pathlib import Path

import wordnet_expand as we

# Synthetic mini-WordNet: pick(00001)-hypernym->tool(00003); pick has hyponym
# mattock(00002); tool has another hyponym adze(00004). "run" as a verb with
# a synonym "sprint" to exercise the verb path.
INDEX_NOUN = """\
pick n 1 1 @ 1 0 00000001
mattock n 1 1 ~ 1 0 00000002
tool n 1 2 ~ 2 0 00000003
adze n 1 1 ~ 1 0 00000004
"""
DATA_NOUN = """\
00000001 00 n 01 pick 0 002 @ 00000003 n 0000 ~ 00000002 n 0000 | a heavy digging tool
00000002 00 n 01 mattock 0 001 @ 00000001 n 0000 | a kind of pick
00000003 00 n 02 tool 0 implement 0 002 ~ 00000001 n 0000 ~ 00000004 n 0000 | an implement
00000004 00 n 01 adze 0 000 | an edge tool
"""
INDEX_VERB = """\
run v 1 1 @ 1 0 00000005
"""
DATA_VERB = """\
00000005 00 v 02 run 0 sprint 0 000 | move fast
"""


class WordnetExpandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wn_dir = Path(self.tmp.name)
        (wn_dir / 'index.noun').write_text(INDEX_NOUN, encoding='utf-8')
        (wn_dir / 'data.noun').write_text(DATA_NOUN, encoding='utf-8')
        (wn_dir / 'index.verb').write_text(INDEX_VERB, encoding='utf-8')
        (wn_dir / 'data.verb').write_text(DATA_VERB, encoding='utf-8')
        self.wn_dir = wn_dir

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_pos_parses_lemmas_and_pointers(self):
        l2o, synsets = we.load_pos(self.wn_dir, 'noun')
        self.assertEqual(l2o['pick'], ['00000001'])
        self.assertEqual(synsets['00000001']['lemmas'], ['pick'])
        self.assertEqual(synsets['00000001']['hyper'], ['00000003'])
        self.assertEqual(synsets['00000001']['hypo'], ['00000002'])
        self.assertEqual(synsets['00000003']['hypo'], ['00000001', '00000004'])

    def test_related_for_word_direct_synonym_scores_one(self):
        l2o, synsets = we.load_pos(self.wn_dir, 'verb')
        related = we.related_for_word('run', l2o, synsets)
        self.assertEqual(related.get('sprint'), 1.0)

    def test_related_for_word_one_hop_sibling(self):
        l2o, synsets = we.load_pos(self.wn_dir, 'noun')
        # mattock -> hypernym pick -> hypernym tool: one hop from mattock
        # reaches "pick" itself (0.6); it does not reach "adze" (two hops).
        related = we.related_for_word('mattock', l2o, synsets)
        self.assertEqual(related.get('pick'), 0.6)
        self.assertNotIn('adze', related)

    def test_gloss_words_filters_short_and_stop_words(self):
        self.assertEqual(we.gloss_words('to go and pick it up'), ['pick'])

    def test_main_builds_deterministic_sorted_json(self):
        dict_path = Path(self.tmp.name) / 'dictionary.json'
        dict_path.write_text(json.dumps({'entries': [
            {'entry_id': 'e0001-x', 'gloss': 'go pick'},
            {'entry_id': 'e0002-y', 'gloss': 'a mattock'},
        ]}), encoding='utf-8')
        out_path = Path(self.tmp.name) / 'out.json'
        import sys
        old_argv = sys.argv
        sys.argv = ['wordnet_expand.py', '--wordnet-dir', str(self.wn_dir),
                    '--dictionary', str(dict_path), '--out', str(out_path),
                    '--min-score', '0.6']
        try:
            we.main()
        finally:
            sys.argv = old_argv
        result = json.loads(out_path.read_text(encoding='utf-8'))
        self.assertEqual(result['mattock'], [['e0001-x', 0.6]])
        self.assertIn('pick', result)

    def test_main_default_min_score_keeps_only_direct_synonyms(self):
        dict_path = Path(self.tmp.name) / 'dictionary2.json'
        dict_path.write_text(json.dumps({'entries': [
            {'entry_id': 'e0001-x', 'gloss': 'go pick'},
        ]}), encoding='utf-8')
        out_path = Path(self.tmp.name) / 'out2.json'
        import sys
        old_argv = sys.argv
        sys.argv = ['wordnet_expand.py', '--wordnet-dir', str(self.wn_dir),
                    '--dictionary', str(dict_path), '--out', str(out_path)]
        try:
            we.main()
        finally:
            sys.argv = old_argv
        result = json.loads(out_path.read_text(encoding='utf-8'))
        # 'mattock' is only a 0.6 (hypernym) relation to 'pick' in this
        # fixture; the default --min-score 1.0 must exclude it.
        self.assertNotIn('mattock', result)


if __name__ == '__main__':
    unittest.main()
