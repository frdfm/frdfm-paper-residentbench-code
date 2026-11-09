import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from residentbench import parse_tool_calls
from residentbench import __main__ as cli
from residentbench.configuration import validate_run_config
from residentbench.reproduce import ROOT, entries


class Preflight(unittest.TestCase):
    def test_all_archived_configs_including_legacy_case_less_ones(self):
        for entry in entries():
            with self.subTest(episode=entry['id']):
                config = json.loads((ROOT / entry['directory'] / 'config.json').read_text(encoding='utf-8'))
                validate_run_config(entry['scenario'], config)

    def test_invalid_configs_fail_before_client_or_output_creation(self):
        entry = next(e for e in entries() if e['scenario'] == 'nuclear')
        original = json.loads((ROOT / entry['directory'] / 'config.json').read_text(encoding='utf-8'))
        changes = [({'case': 'nuclear'}, 'refund'), ({'version': 'wrong'}, 'nuclear'),
                   ({'tools': []}, 'nuclear'), ({'turns': -1}, 'nuclear'),
                   ({'turns': 1.5}, 'nuclear'), ({'turns': True}, 'nuclear'),
                   ({'turns': 13}, 'nuclear'), ({'step_seconds': 2}, 'nuclear'),
                   ({'history_turns': 1}, 'nuclear'), ({'tool_choice': 'required'}, 'nuclear'),
                   ({'max_tokens': 0}, 'nuclear'), ({'temperature': float('nan')}, 'nuclear'),
                   ({'seed': True}, 'nuclear'), ({'description_variant': 10}, 'nuclear'),
                   ({'model': ''}, 'nuclear'), ({'provider': []}, 'nuclear'),
                   ({'reasoning': 'low'}, 'nuclear'), ({'initial_environment': {}}, 'nuclear')]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, (change, case) in enumerate(changes):
                with self.subTest(change=change, case=case):
                    config = copy.deepcopy(original)
                    config.update(change)
                    source, target = root / 'config.json', root / f'run-{index}'
                    source.write_text(json.dumps(config), encoding='utf-8')
                    argv = ['residentbench', 'run', '--case', case, '--config', str(source), '--output', str(target)]
                    with patch.object(sys, 'argv', argv), patch('residentbench.client.OpenRouter') as client:
                        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                            cli.main()
                        self.assertEqual(error.exception.code, 2)
                        client.assert_not_called()
                    self.assertFalse(target.exists())

    def test_optional_recorded_physics_must_match_kernel(self):
        for case, key in [('thermostat', 'room'), ('traffic', 'vehicle_parameters'), ('paddle', 'specification')]:
            entry = next(e for e in entries() if e['scenario'] == case)
            config = json.loads((ROOT / entry['directory'] / 'config.json').read_text(encoding='utf-8'))
            config[key] = {}
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_run_config(case, config)


class ArgumentDecoding(unittest.TestCase):
    def parse(self, function):
        return parse_tool_calls({'choices': [{'message': {'tool_calls': [{'function': function}]}}]}, {'act': object()})

    def test_non_object_arguments_are_dropped(self):
        for value in (False, True, 0, 1, [], [1], None, 'null', 'false', '0', '[]', '"text"'):
            with self.subTest(value=value):
                function = {'name': 'act', 'arguments': value}
                calls, dropped = self.parse(function)
                self.assertEqual(calls, [])
                self.assertEqual(dropped, [function])

    def test_objects_omitted_and_empty_arguments_keep_existing_behavior(self):
        for value in ({}, {'x': 1}, '{}', '{"x": 1}', '', '   '):
            with self.subTest(value=value):
                calls, dropped = self.parse({'name': 'act', 'arguments': value})
                self.assertEqual(dropped, [])
                self.assertEqual(calls, [('act', {'x': 1} if value in ({'x': 1}, '{"x": 1}') else {})])
        self.assertEqual(self.parse({'name': 'act'}), ([('act', {})], []))


class IntegrityModes(unittest.TestCase):
    def test_real_episode_checks_survive_optimization(self):
        entry = next(e for e in entries() if e['scenario'] == 'nuclear' and e['complete'])
        original = ROOT / entry['directory']
        command = 'from pathlib import Path; import sys; from residentbench.reproduce import verify; print(verify(Path(sys.argv[1])))'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'experiments/episode'
            directory.mkdir(parents=True)
            for corruption in (None, 'hash', 'message', 'schema', 'trajectory'):
                current = copy.deepcopy(entry)
                current['directory'] = 'experiments/episode'
                for name in current['files_sha256']:
                    shutil.copyfile(original / name, directory / name)
                if corruption in ('message', 'trajectory'):
                    trace = directory / 'run-0.jsonl'
                    rows = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
                    if corruption == 'message':
                        rows[0]['message']['state'] = {'tampered': True}
                    else:
                        rows[-1]['trajectory'][-1]['launched'] = not rows[-1]['trajectory'][-1]['launched']
                    trace.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
                    current['files_sha256']['run-0.jsonl'] = hashlib.sha256(trace.read_bytes()).hexdigest()
                elif corruption == 'schema':
                    source = directory / 'config.json'
                    config = json.loads(source.read_text(encoding='utf-8'))
                    config['tools'][0]['function']['description'] += ' tampered'
                    source.write_text(json.dumps(config), encoding='utf-8')
                    current['files_sha256']['config.json'] = hashlib.sha256(source.read_bytes()).hexdigest()
                elif corruption == 'hash':
                    current['files_sha256']['config.json'] = '0' * 64
                (root / 'experiments/manifest.json').write_text(json.dumps({'episodes': [current]}), encoding='utf-8')
                for flags in ([], ['-O']):
                    with self.subTest(corruption=corruption, flags=flags):
                        run = subprocess.run([sys.executable, *flags, '-c', command, str(root)], cwd=ROOT,
                                             capture_output=True, text=True, timeout=30)
                        if corruption is None:
                            self.assertEqual(run.returncode, 0, run.stderr)
                            self.assertEqual(run.stdout.strip(), '1')
                        else:
                            self.assertNotEqual(run.returncode, 0, 'Corruption was silently accepted')


if __name__ == '__main__':
    unittest.main()
