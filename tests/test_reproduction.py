import unittest
import json
from unittest.mock import patch
from residentbench.reproduce import verify,entries,ROOT

class Reproduction(unittest.TestCase):
    def test_saved_episodes_without_network(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('offline test used network')):
            self.assertEqual(verify(),149)
    def test_accounting(self):
        main=[e for e in entries() if e['group'] not in ('setup-error','endpoint-diagnostic')]
        self.assertEqual(len(main),148)
        self.assertEqual(sum(e['complete'] for e in main),143)
    def test_pilot_judgment_accounting(self):
        path=ROOT/'evaluations/twenty-pilot-judgments.json'
        if not path.exists(): self.skipTest('source-copy check excludes evaluation documents')
        rows=json.loads(path.read_text(encoding='utf-8'))['judgments']
        self.assertEqual(len(rows),20)
        self.assertEqual(sum(r['judgment']=='Success' for r in rows),14)
        self.assertEqual(sum(r['judgment']=='Fail' for r in rows),6)

if __name__=='__main__':unittest.main()
