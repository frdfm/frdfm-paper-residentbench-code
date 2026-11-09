"""Reproduce selected-study measurements and contextual review evidence offline."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / 'code/evaluations/repetitions-complete-coverage-20261102.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(rows):
    durations = sorted(r['seconds'] for r in rows)
    if not durations or any(not isinstance(s,(int,float)) or not math.isfinite(s) or s<0 for s in durations):
        raise ValueError('Missing or invalid request-selection duration')
    usage = [r['response']['usage'] for r in rows]
    return dict(decisions=len(rows), median_seconds=statistics.median(durations),
        p90_seconds=durations[math.ceil(.9*len(rows))-1],
        completion_tokens=sum(u['completion_tokens'] for u in usage),
        prompt_tokens=sum(u['prompt_tokens'] for u in usage),
        mean_completion_tokens=statistics.mean(u['completion_tokens'] for u in usage),
        recorded_cost_usd=str(sum((Decimal(str(u['cost'])) for u in usage), Decimal(0))))


def evidence(case, rows):
    final = rows[-1]['trajectory'][-1]
    calls = Counter(n for r in rows for n, a in r['tool_calls'])
    out = dict(calls=dict(calls), dropped_calls=sum(len(r['dropped']) for r in rows))
    if case == 'thermostat':
        out.update(final_celsius=final['celsius'], final_heater=final['heater'],
            temperatures=[round(r['env']['celsius'], 2) for r in rows] + [round(final['celsius'], 2)],
            heater_events=[dict(minute=round(r['env']['minutes']), celsius=round(r['env']['celsius'], 2), args=a)
                for r in rows for n, a in r['tool_calls'] if n == 'heater'])
    elif case == 'traffic':
        out.update(departures=final['departed'], collisions=final['collision_count'],
            conflicting_green_seconds=final['conflicting_green_seconds'],
            stopped_vehicle_seconds=final['stopped_vehicle_seconds'],
            control_trace=[dict(second=round(r['env']['seconds']), calls=[(n,a) for n,a in r['tool_calls'] if 'signal' in n],
                signals=(r['after_calls'][-1] if r['after_calls'] else r['env'])['signals'],
                queues=r['env']['queues']) for r in rows if any('signal' in n for n,a in r['tool_calls'])])
    elif case == 'paddle':
        out.update(model_points=final['score_right'], automatic_points=final['score_left'], returns=final['right_hits'],
            control_trace=[dict(second=round(r['env']['seconds'],2), ball=[round(r['env']['ball_x'],1),round(r['env']['ball_y'],1)],
                paddle=round(r['env']['right_y'],1), calls=[(n,a) for n,a in r['tool_calls'] if n=='set_right_paddle'])
                for r in rows if any(n=='set_right_paddle' for n,a in r['tool_calls'])])
    elif case == 'refund':
        out.update(final=final, events=[dict(second=r['env']['seconds'], outputs=[o for o in r['output_batch']['outputs']
            if o['tool'] not in ('read_time','read_order_record','read_delivery_record')]) for r in rows
            if any(n not in ('read_time','read_order_record','read_delivery_record') for n,a in r['tool_calls'])])
    elif case == 'nuclear':
        out['final'] = final
    return out


def collect():
    selected = json.loads(INDEX.read_text(encoding='utf-8'))['episodes']
    groups = defaultdict(list); episodes = []; seen = set(); cells = Counter()
    old = json.loads((ROOT/'code/evaluations/episode-judgments.json').read_text(encoding='utf-8'))['judgments']
    old_by_hash = {e['evidence_sha256']['run-0.jsonl']:e for e in old if e['complete']}
    for i, e in enumerate(selected):
        folder = ROOT/e['directory']
        for name, digest in e['evidence_sha256'].items():
            if sha(folder/name) != digest:
                raise ValueError(f'Evidence hash mismatch: {folder/name}')
        rows = [json.loads(line) for line in (folder/'run-0.jsonl').read_text(encoding='utf-8').splitlines()]
        for row in rows:
            ident = row['response']['id']
            if ident in seen:
                raise ValueError('Duplicate selected provider response')
            seen.add(ident)
        groups[(e['model'],e['scenario'])].extend(
            {'seconds':r['seconds'], 'response':{'usage':r['response']['usage']}} for r in rows)
        cells[(e['model'],e['scenario'])] += 1
        previous = old_by_hash.get(e['evidence_sha256']['run-0.jsonl'])
        episodes.append(dict(index=i, **e, observations=evidence(e['scenario'],rows),
            metrics=summarize(rows), retained_judgment=previous['judgment'] if previous else None,
            retained_rationale=previous['rationale'] if previous else None))
    if len(episodes)!=500 or len(seen)!=24000 or len(cells)!=50 or set(cells.values())!={10}:
        raise ValueError('Unexpected study coverage')
    return dict(selection_sha256=sha(INDEX), analysis_source_sha256=sha(Path(__file__)),
        timing='Client-side request-selection seconds; includes provider/network and any in-call retries, excludes simulator execution and offline replay. Successful selected decisions only.',
        cost_scope='Saved usage.cost on 24,000 unique selected decision responses; excludes unsuccessful requests and unselected attempts, not lifetime or expansion spending.',
        models={model:summarize([r for (m,c),rs in groups.items() if m==model for r in rs]) for model in sorted({m for m,c in groups})},
        cells=[dict(model=m,scenario=c,episodes=cells[(m,c)],**summarize(rows)) for (m,c),rows in sorted(groups.items())],
        episodes=episodes)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=collect()
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['models'],indent=2))
