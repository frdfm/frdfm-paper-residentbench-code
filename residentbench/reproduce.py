"""Offline verification and descriptive exports; no evaluator grades are inferred."""
import csv
import hashlib
import json
from pathlib import Path
from . import NativeToolCalling
from . import thermostat, traffic_bench, case_bench

ROOT = Path(__file__).resolve().parents[1]

def entries(root=ROOT):
    return json.loads((root/'experiments/manifest.json').read_text(encoding='utf-8'))['episodes']

def load(entry, root=ROOT):
    directory=root/entry['directory']
    config=json.loads((directory/'config.json').read_text(encoding='utf-8'))
    trace=directory/'run-0.jsonl'
    records=[json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines() if line.strip()] if trace.exists() else []
    return config,records

def execute(case, config, model, choose, output=None):
    if case=='thermostat': return thermostat.run_trial(model, output, choose)
    if case=='traffic': return traffic_bench.run_trial(model, output, choose, config.get('seed',20261028), config['turns'])[0]
    return case_bench.run_trial(case,model,choose,output,config.get('seed',20261029),config['turns'],config.get('description_variant',0))[0]

class EndReplay(BaseException): pass

class VerificationError(ValueError): pass

def require(condition, message):
    if not condition:
        raise VerificationError(message)

class SavedResponses:
    system=''
    def __init__(self, records, schemas): self.records,self.schemas,self.index=records,schemas,0
    def generate_raw(self,prompt,**kwargs):
        if self.index==len(self.records): raise EndReplay
        row=self.records[self.index]
        require(json.loads(prompt)==row['message'], f'model-visible message mismatch at turn {self.index+1}')
        require(kwargs['tools']==self.schemas, 'tool schema mismatch')
        self.index+=1
        return row['response']

def close(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return abs(a-b)<=1e-9*max(1,abs(a),abs(b))
    if isinstance(a,dict) and isinstance(b,dict): return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)): return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return a==b

def verify(root=ROOT, replay=True):
    count=0
    for entry in entries(root):
        directory=root/entry['directory']
        for name,digest in entry['files_sha256'].items():
            require(hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest, f'changed original: {directory/name}')
        cfg,rows=load(entry,root)
        if not rows or not replay: continue
        model=SavedResponses(rows,cfg['tools'])
        choose=NativeToolCalling(tool_choice='auto',max_tokens=cfg.get('max_tokens',4096),retries=0)
        try: result=execute(entry['scenario'],cfg,model,choose)
        except EndReplay: result=choose.log.__self__.records
        require(model.index==len(rows), f"{entry['id']}: replay consumed a different record count")
        require(len(result)==len(rows), f"{entry['id']}: replay produced a different record count")
        for old,new in zip(rows,result):
            for key in ('message','tool_calls','dropped','env','after_calls','trajectory','output_batch','mandatory_outputs'):
                if key in old:
                    require(close(old[key],new.get(key)), f"{entry['id']} turn {old['turn']} {key}")
        count+=1
    return count

def summaries(root=ROOT):
    result=[]
    for entry in entries(root):
        cfg,rows=load(entry,root)
        last=(rows[-1].get('trajectory') or [rows[-1]['env']])[-1] if rows else {}
        row={k:entry[k] for k in ('id','scenario','group','model','completed_turns','planned_turns','complete')}
        row.update(provider=cfg.get('provider'),reasoning=json.dumps(cfg.get('reasoning')),temperature=cfg.get('temperature'),cost_usd=sum((r['response'].get('usage') or {}).get('cost',0) or 0 for r in rows),terminal_environment=json.dumps(last,sort_keys=True))
        result.append(row)
    return result

def export(root=ROOT):
    out=root/'results';out.mkdir(exist_ok=True)
    rows=summaries(root)
    with (out/'episodes.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    nuclear={}
    for entry in entries(root):
        if entry['scenario']!='nuclear' or entry['group'] not in ('nuclear-repetitions','expansion'):continue
        cfg,trace=load(entry,root)
        final=trace[-1]['trajectory'][-1]
        stats=nuclear.setdefault(entry['model'],{'model':entry['model'],'episodes':0,'launched':0})
        stats['episodes']+=1;stats['launched']+=bool(final['launched'])
    with (out/'nuclear.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['model','episodes','launched']);writer.writeheader();writer.writerows(nuclear.values())
    return rows
