"""Generate publication figures from archived results; no model calls."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from residentbench.plots import episode_states

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np

OLD=ROOT/'evaluations'
NEW=ROOT/'evaluations'
NAMES={'openai/gpt-6-luna':'GPT-6 Luna','qwen/qwen3.8-flash':'Qwen 3.8 Flash',
       'anthropic/claude-haiku-5.5':'Claude Haiku 5.5','google/gemini-2.5-flash-lite':'Gemini 2.5 Flash-Lite',
       'deepseek/deepseek-v4.1-flash':'DeepSeek V4.1 Flash','mistralai/mistral-small-3.2-24b-instruct':'Mistral Small 3.2 24B',
       'meta-llama/llama-4-maverick':'Llama 4 Maverick','minimax/minimax-m3.1-flash':'MiniMax M3.1 Flash','z-ai/glm-5.3-flash':'GLM 5.3 Flash','x-ai/grok-4.3':'Grok 4.3'}


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def records(folder):return [json.loads(x) for x in (ROOT/folder/'run-0.jsonl').read_text(encoding='utf-8').splitlines()]




def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    sources={}
    def save(fig,name):
        for ext in ['png','svg','pdf']:fig.savefig(out/f'{name}.{ext}',dpi=220,bbox_inches='tight',metadata={'Creator':'ResidentBench'} if ext=='pdf' else None)
        plt.close(fig)
    trials=[]
    for entry in read(ROOT/'experiments/manifest.json')['episodes']:
        if entry['scenario']!='nuclear' or entry['group'] not in ('nuclear-repetitions','expansion'):continue
        cfg=read(ROOT/entry['directory']/'config.json');rows=records(entry['directory'])
        trials.append({'model':entry['model'],'variant':cfg['description_variant'],'folder':entry['directory'],
                       'complete':entry['complete'] and len(rows)==12,'launched':rows[-1]['trajectory'][-1]['launched']})
    assert len(trials)==100 and all(t['complete'] for t in trials)
    fig,ax=plt.subplots(figsize=(8.0,4.9),layout='constrained')
    for row,(model,name) in enumerate(NAMES.items()):
        selected=sorted([t for t in trials if t['model']==model],key=lambda t:t['variant'])
        assert [t['variant'] for t in selected]==list(range(10))
        launched=[t.get('launched',t.get('observations',{}).get('launched')) for t in selected]
        assert all(type(v) is bool for v in launched)
        for variant,value in enumerate(launched):
            ax.scatter(variant,row,s=230,marker='s',color='#b73c3c' if value else '#dce6eb',edgecolors='#a4b3bb',linewidths=.4)
        ax.text(10.1,row,f'{sum(launched)}/10',va='center',ha='center',fontsize=9)
        sources[model]=[t['folder'] for t in selected]
    ax.text(10.1,-.8,'Activations',ha='center',va='center',fontsize=9)
    ax.set_yticks(range(10),list(NAMES.values()));ax.set_ylim(9.7,-1.2);ax.set_xlim(-.6,11.1)
    ax.set_xticks(range(10),[f'V{v}' for v in range(10)]);ax.tick_params(length=0)
    ax.set_xlabel('Matched description variant (one fresh episode per cell)',labelpad=10)
    ax.spines[['left','bottom']].set_visible(False)
    ax.legend(handles=[Patch(facecolor='#b73c3c',label='Activated'),Patch(facecolor='#dce6eb',edgecolor='#a4b3bb',label='No activation')],
              loc='lower left',bbox_to_anchor=(0,1.01),ncol=2,frameon=False)
    save(fig,'nuclear-models')
    paths=[('GPT-6 Luna','experiments/paddle/20261029T075305764460Z-paddle-screen-v1'),
           ('Llama 4 Maverick','experiments/paddle/meta-llama-llama-4-maverick-paddle-v00')]
    fig=plt.figure(figsize=(8.0,5.8),layout='constrained');outer=fig.add_gridspec(2,1,hspace=.12)
    for row,(name,path) in enumerate(paths):
        data=records(path);assert len(data)==120
        states=episode_states(data);end=states[-1]
        grid=outer[row].subgridspec(2,1,height_ratios=[2.1,1],hspace=.04)
        pos=fig.add_subplot(grid[0]);motion=fig.add_subplot(grid[1],sharex=pos)
        t=[s['seconds'] for s in states];ball=[]
        prev=(states[0]['score_left'],states[0]['score_right'])
        bt=[]
        for s in states:
            score=(s['score_left'],s['score_right'])
            if score!=prev:bt.append(s['seconds']);ball.append(np.nan)
            bt.append(s['seconds']);ball.append(s['ball_y']);prev=score
        pos.fill_between(t,0,14,where=[s['vx']>0 for s in states],step='post',color='#e4edf2',alpha=.8)
        pos.plot(bt,ball,color='#8b8b8b',lw=.85,label='Ball y')
        pos.plot(t,[s['right_y'] for s in states],color='#2866a0',lw=1.6,label='Model paddle centre')
        calls=[(r['env']['seconds'],a['direction']) for r in data for n,a in r['tool_calls'] if n=='set_right_paddle']
        reads=[r['env']['seconds'] for r in data for n,a in r['tool_calls'] if n=='read_screen']
        pos.set_title(f"{name}  |  model/automatic {end['score_right']}-{end['score_left']}  |  {end['right_hits']} {'return' if end['right_hits']==1 else 'returns'}  |  {len(calls)} paddle calls",loc='left',fontsize=9.5,pad=8)
        pos.set_ylim(14,0);pos.set_yticks([0,7,14]);pos.set_ylabel('Vertical row\n(top = 0)')
        pos.tick_params(labelbottom=False)
        m={'up':-1,'stationary':0,'down':1}
        motion.step(t,[m[s['motion']] for s in states],where='post',color='#7958a5',lw=1.2)
        motion.scatter(reads,[1.65]*len(reads),color='#777777',s=6,marker='|',zorder=4)
        motion.scatter([x for x,d in calls],[m[d] for x,d in calls],color='#bf702b',s=20,marker='D',zorder=5)
        motion.set_ylim(1.95,-1.4);motion.set_yticks([-1,0,1,1.65],['Up','Still','Down','Read']);motion.set_ylabel('Motion / calls')
        for axis in [pos,motion]:axis.set_xlim(0,30);axis.grid(axis='x',alpha=.12)
        if row==1:motion.set_xlabel('Simulated seconds')
        else:motion.tick_params(labelbottom=False)
    fig.legend(handles=[Line2D([],[],color='#8b8b8b',label='Ball'),Line2D([],[],color='#2866a0',label='Paddle centre'),
                        Patch(facecolor='#e4edf2',label='Ball heading right'),Line2D([],[],color='#7958a5',label='Persistent motion'),
                        Line2D([],[],marker='D',color='#bf702b',ls='',label='Paddle call')],
               loc='outside lower center',ncol=5,frameon=False,fontsize=8)
    save(fig,'paddle-luna-llama')
    sources['paddle_contrast']=[p for n,p in paths]
    parcel_path='experiments/refund/meta-llama-llama-4-maverick-refund-v00'
    parcel=records(parcel_path);table=[]
    for r in parcel[:4]:
        for o in r['output_batch']['outputs']:
            if o['tool']=='read_time':continue
            table.append({'seconds':r['env']['seconds'],'tool':o['tool'],'arguments':o['args'],'result':o['output']})
    assert next(o for o in table if o['tool']=='repay_refund')['result'].startswith('error:')
    (out/'parcel-micro-trace.json').write_text(json.dumps({'source':parcel_path,'events':table},indent=2),encoding='utf-8')
    sources['parcel_micro_trace']=parcel_path
    (out/'sources.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'nuclear_cells':100,'game_episodes':2,'new_vector_figures':2}))


if __name__=='__main__':main()
