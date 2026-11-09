"""Version the traffic clarification and exact author-reviewed episode decisions."""
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'code/evaluations/study-judgments-yellow-v2-20261102.json'
ORIGINAL = ROOT / 'code/evaluations/study-judgments-20261102.json'
KEY = ROOT / 'code/evaluations/anonymous-author-review-key-20261102.json'
REVIEW = ROOT / 'code/evaluations/author-review-20261103/review-record.json'
OUTPUT = ROOT / 'code/evaluations/study-judgments-author-v3-20261103.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile():
    base = json.loads(BASE.read_text(encoding='utf-8'))
    original = json.loads(ORIGINAL.read_text(encoding='utf-8'))
    key = json.loads(KEY.read_text(encoding='utf-8'))
    review = json.loads(REVIEW.read_text(encoding='utf-8'))
    reasons = {e['case_number']:e for e in review['cases']}
    out = copy.deepcopy(base)
    reviewed = []
    for case in key['cases']:
        label = case.get('author_decision')
        if label is None:
            continue
        assert label in ('Success', 'Fail')
        entry = out['judgments'][case['episode_index']]
        assert entry['directory'] == case['directory']
        polished = reasons.get(case['case_number'])
        if polished:
            assert polished['author_verdict'] == label
        old = entry['judgment']
        entry['pre_author_assessment'] = dict(judgment=old, rationale=entry['rationale'])
        entry['author_review'] = dict(case_number=case['case_number'],
            judgment=label, reason_recorded=case['author_reason'],
            reason_proofread=polished['reason_proofread'] if polished else case['author_reason'],
            source=str(KEY.relative_to(ROOT)).replace('\\','/'))
        entry['judgment'] = label
        entry['rationale'] = entry['author_review']['reason_proofread']
        if old != label:
            entry['retained'] = False
        reviewed.append(dict(index=entry['index'],case_number=case['case_number'],
            scenario=entry['scenario'],model=entry['model'],previous=old,final=label))
    assert len(reviewed) == 14
    assert sum(e['previous'] != e['final'] for e in reviewed) == 6
    by_scenario = defaultdict(Counter)
    for entry in out['judgments']:
        by_scenario[entry['scenario']][entry['judgment']] += 1
        path = ROOT / entry['directory'] / 'run-0.jsonl'
        assert sha(path) == entry['evidence_sha256']['run-0.jsonl']
    out['counts'] = dict(Counter(e['judgment'] for e in out['judgments']))
    out['method'] = ('Retrospective contextual Codex assessment of all 500 episodes, followed by '
        'the designer-clarified yellow-phase reassessment of all 100 traffic episodes and exact '
        'author verdicts on 14 selected episodes. Model names were masked in the author graph '
        'packet; prior assisted material was available. No representative independent agreement '
        'estimate. Human verdicts apply only to the reviewed episodes; no numerical thermostat '
        'or paddle threshold or full-scenario relabeling is inferred from them.')
    out['assessment_revision'] = dict(
        version='author-v3-20261103',
        inputs_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (BASE,ORIGINAL,KEY,REVIEW)},
        basis='Retrospective yellow-phase clarification plus explicit final author verdicts, completed 3 November 2026.',
        human_review_count=14, focused_packet_count=13,
        human_selection='Three targeted thermostat cases, ten selected controls, and the earlier reviewed traffic case 115. Not a representative sample.',
        human_label_changes_from_yellow_v2=6,
        total_label_changes_from_original=sum(a['judgment']!=b['judgment'] for a,b in zip(original['judgments'],out['judgments'])),
        reviewed=reviewed,
        status='Final recorded labels used for the updated manuscript; original and yellow-v2 assessments retained unchanged.',
        limitations='Unreviewed contextual labels retain their prior assessments. Targeted designer review does not validate consistency across all unreviewed episodes or estimate independent agreement.')
    out['scenario_counts'] = {k:dict(v) for k,v in sorted(by_scenario.items())}
    assert out['counts'] == {'Success':285,'Fail':215}
    return out


if __name__ == '__main__':
    result = reconcile()
    serialized = json.dumps(result,indent=2)+'\n'
    if OUTPUT.exists():
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'Preserve versioned assessments; create a new revision for new evidence.'
    else:
        OUTPUT.write_text(serialized,encoding='utf-8')
    print(json.dumps({'counts':result['counts'],'scenario_counts':result['scenario_counts'],
        'author_reviewed':14,'changed_from_v2':6,'changed_from_original':result['assessment_revision']['total_label_changes_from_original']}))
