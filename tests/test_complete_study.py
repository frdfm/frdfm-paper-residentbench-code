"""Full-study reproduction must use saved evidence and no network or key."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from residentbench import study
from residentbench.reproduce import VerificationError


class CompleteStudy(unittest.TestCase):
    def test_all_selected_episodes_replay_without_network(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('Offline replay used the network')):
            result = study.verify()
        self.assertEqual(result, {'episodes':500, 'decisions':24000,
                                 'human_reviewed':14, 'Success':285, 'Fail':215,
                                 'offline_replay':True})

    def test_changed_archive_record_is_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'record.json').write_text('changed', encoding='utf-8')
            (root/'manifest.json').write_text(json.dumps({'files':[{
                'path':'record.json', 'sha256':hashlib.sha256(b'original').hexdigest()}]}), encoding='utf-8')
            with patch.object(study, 'STUDY', root):
                with self.assertRaisesRegex(VerificationError, 'Changed study record'):
                    study.verify()

    def test_archive_paths_cannot_escape_study(self):
        with self.assertRaisesRegex(VerificationError, 'escapes'):
            study.locate('../outside.json')
