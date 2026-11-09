"""Offline reproduction of the complete selected study and final review labels."""
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

from . import NativeToolCalling
from .reproduce import ROOT, SavedResponses, execute, close, require

STUDY = ROOT/'study'
EVALUATIONS = STUDY/'code/evaluations'


def locate(relative):
    path = (STUDY/relative.replace('\\', '/')).resolve()
    require(path.is_relative_to(STUDY.resolve()), 'Evidence path escapes the study directory')
    return path


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def tool(name):
    path = STUDY/'code/tools'/f'{name}.py'
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(replay=True):
    manifest = read(STUDY/'manifest.json')
    for item in manifest['files']:
        require(hashlib.sha256(locate(item['path']).read_bytes()).hexdigest() == item['sha256'],
                f"Changed study record: {item['path']}")
    selection = read(EVALUATIONS/'repetitions-complete-coverage-20261102.json')['episodes']
    measured = read(EVALUATIONS/'study-measurements-20261102.json')
    initial = read(EVALUATIONS/'study-judgments-20261102.json')
    yellow = read(EVALUATIONS/'study-judgments-yellow-v2-20261102.json')
    final = read(EVALUATIONS/'study-judgments-author-v3-20261103.json')
    key = read(EVALUATIONS/'anonymous-author-review-key-20261102.json')
    reviews = {e['episode_index']:e for e in key['cases'] if e.get('author_decision')}
    require(len(reviews) == 14, 'Unexpected human review scope')
    for relative, digest in final['assessment_revision']['inputs_sha256'].items():
        require(hashlib.sha256(locate(relative).read_bytes()).hexdigest() == digest,
                'Assessment provenance hash mismatch')
    require(hashlib.sha256((EVALUATIONS/'study-measurements-20261102.json').read_bytes()).hexdigest()
            == final['measurement_evidence_sha256'], 'Measurement provenance mismatch')
    analysis = tool('paper-study-analysis')
    require(hashlib.sha256((STUDY/'code/tools/paper-study-analysis.py').read_bytes()).hexdigest()
            == measured['analysis_source_sha256'], 'Analysis source hash mismatch')
    violations = tool('reassess-traffic-yellow').violations
    cells = Counter(); labels = Counter(); ids = set(); groups = defaultdict(list)
    for index, entry in enumerate(selection):
        folder = locate(entry['directory'])
        for name, digest in entry['evidence_sha256'].items():
            require(hashlib.sha256((folder/name).read_bytes()).hexdigest() == digest,
                    f'Selected evidence hash mismatch: {index}/{name}')
        config = read(folder/'config.json')
        rows = [json.loads(line) for line in (folder/'run-0.jsonl').read_text(encoding='utf-8').splitlines()]
        require(len(rows) == entry['decisions'], 'Selected decision count mismatch')
        observation = measured['episodes'][index]
        judgment = final['judgments'][index]
        for field in ('model', 'scenario', 'directory', 'decisions', 'evidence_sha256'):
            require(entry[field] == observation[field] == judgment[field], f'Misaligned {field}: {index}')
        require(close(analysis.evidence(entry['scenario'], rows), observation['observations']),
                f'Measurements differ: {index}')
        metrics = [{'seconds':row['seconds'], 'response':{'usage':row['response']['usage']}} for row in rows]
        require(analysis.summarize(metrics) == observation['metrics'], f'Episode metrics differ: {index}')
        groups[entry['model']].extend(metrics)
        for row in rows:
            ident = row['response']['id']
            require(ident not in ids, 'Duplicate selected response ID')
            ids.add(ident)
        if entry['scenario'] == 'traffic':
            bad = violations(rows)
            require(bad == yellow['judgments'][index]['yellow_phase_violations'], 'Yellow-path evidence differs')
            expected = 'Fail' if bad else initial['judgments'][index]['judgment']
            require(expected == yellow['judgments'][index]['judgment'], 'Yellow assessment differs')
        else:
            require(initial['judgments'][index] == yellow['judgments'][index], 'Unexpected non-traffic revision')
        if index in reviews:
            review = reviews[index]
            require(judgment['judgment'] == review['author_decision'], 'Human verdict mismatch')
            require(judgment['pre_author_assessment']['judgment'] == yellow['judgments'][index]['judgment'],
                    'Missing prior assessment')
        else:
            require(judgment == yellow['judgments'][index], 'Unreviewed episode relabeled')
        if replay:
            model = SavedResponses(rows, config['tools'])
            chooser = NativeToolCalling(tool_choice='auto', max_tokens=config.get('max_tokens', 4096), retries=0)
            replayed = execute(entry['scenario'], config, model, chooser)
            require(model.index == len(rows) == len(replayed), f'Replay count mismatch: {index}')
            for old, new in zip(rows, replayed):
                for field in ('message', 'tool_calls', 'dropped', 'env', 'after_calls', 'trajectory', 'output_batch', 'mandatory_outputs'):
                    if field in old:
                        require(close(old[field], new.get(field)), f'Replay mismatch: {index}/{old["turn"]}/{field}')
        cells[(entry['model'], entry['scenario'])] += 1
        labels[judgment['judgment']] += 1
    require(len(selection) == 500 and len(ids) == 24000 and len(cells) == 50 and set(cells.values()) == {10},
            'Study is not balanced')
    for model, rows in groups.items():
        require(analysis.summarize(rows) == measured['models'][model], f'Pooled metrics differ: {model}')
    require(labels == Counter(Success=285, Fail=215), 'Final totals differ')
    return {'episodes':500, 'decisions':24000, 'human_reviewed':14,
            'Success':285, 'Fail':215, 'offline_replay':replay}


def summarize():
    result = verify(replay=False)
    final = read(EVALUATIONS/'study-judgments-author-v3-20261103.json')
    measurements = read(EVALUATIONS/'study-measurements-20261102.json')
    out = ROOT/'results/full-study'; out.mkdir(parents=True, exist_ok=True)
    scenarios = ('thermostat', 'traffic', 'nuclear', 'paddle', 'refund')
    counts = Counter((j['model'], j['scenario']) for j in final['judgments'] if j['judgment'] == 'Success')
    with (out/'success.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['model', *scenarios])
        writer.writeheader()
        for model in measurements['models']:
            writer.writerow(dict(model=model, **{s:counts[(model,s)] for s in scenarios}))
    with (out/'episodes.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['index','model','scenario','decisions','judgment','rationale','author_review_case'])
        writer.writeheader()
        for j in final['judgments']:
            writer.writerow({**{k:j[k] for k in ('index','model','scenario','decisions','judgment','rationale')},
                             'author_review_case':j.get('author_review',{}).get('case_number','')})
    (out/'runtime-usage.json').write_text(json.dumps(measurements['models'],indent=2)+'\n',encoding='utf-8')
    (out/'summary.json').write_text(json.dumps({**result, 'scenario_counts':final['scenario_counts'],
        'assessment_scope':final['method']},indent=2)+'\n',encoding='utf-8')
    return result
