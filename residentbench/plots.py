"""Descriptive figures for every saved episode, never automatic grades."""
import html
from .reproduce import ROOT,entries,load,export

def episode_states(rows):
    """Return recorded states in capture order, including immediate tool effects."""
    if not rows:
        return []
    return [rows[0]['env']]+[state for row in rows
        for state in [row['env'],*row['after_calls'],*row['trajectory']]]

def gallery(root=ROOT):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=root/'results/gallery';out.mkdir(parents=True,exist_ok=True)
    links=[]
    for e in entries(root):
        cfg,rows=load(e,root)
        if not rows:continue
        case=e['scenario'];points=episode_states(rows)
        key='minutes' if case=='thermostat' else 'seconds';t=[p[key] for p in points]
        fig,(a,b)=plt.subplots(2,1,figsize=(11,5.4),sharex=True,layout='constrained')
        if case=='thermostat':
            a.plot(t,[p['celsius'] for p in points]);a.set_ylabel('Temperature (°C)')
            b.step(t,[p['heater'] for p in points],where='post');b.set_ylabel('Heater on');b.set_yticks([0,1])
        elif case=='traffic':
            roads=('north','south','east','west')
            for road in roads:a.plot(t,[p['queues'][road] for p in points],label=road.title())
            a.set_ylabel('Stopped cars');a.legend(ncol=4)
            for i,road in enumerate(roads):
                for j in range(len(points)-1):
                    b.broken_barh([(t[j],t[j+1]-t[j])],(i-.35,.7),facecolors={'red':'#d84a4a','yellow':'#edc244','green':'#30a574'}[points[j]['signals'][road]])
            b.set_yticks(range(4),[r.title() for r in roads]);b.set_ylabel('Signals')
        elif case=='paddle':
            bt=[];by=[];previous=(points[0]['score_left'],points[0]['score_right'])
            for p in points:
                score=(p['score_left'],p['score_right'])
                if score!=previous:bt.append(p['seconds']);by.append(float('nan'))
                bt.append(p['seconds']);by.append(p['ball_y']);previous=score
            a.plot(bt,by,label='Ball y',color='#8b8b8b',alpha=.8);a.plot(t,[p['right_y'] for p in points],label='Controlled paddle y',color='#2866a0');a.legend();a.set_ylabel('Screen row (0 = top)');a.set_ylim(14,0)
            for field,label in [('score_left','Left automated'),('score_right','Right controlled')]:b.step(t,[p[field] for p in points],where='post',label=label)
            b.legend();b.set_ylabel('Points')
        elif case=='nuclear':
            a.step(t,[p['launched'] for p in points],where='post',color='#b03242');a.set_ylabel('Launch recorded');a.set_yticks([0,1])
        else:
            a.step(t,[p['refund_repaid'] for p in points],where='post',label='Refund repaid');a.step(t,[p['item_location']!='recipient' for p in points],where='post',label='Item returned');a.legend();a.set_yticks([0,1]);a.set_ylabel('Ledger state')
        if case in ('nuclear','refund'):
            names=sorted({n for r in rows for n,args in r['tool_calls']})
            for i,name in enumerate(names):
                times=[r['env']['seconds'] for r in rows if any(n==name for n,args in r['tool_calls'])];b.scatter(times,[i]*len(times))
            b.set_yticks(range(len(names)),names,fontsize=7);b.set_ylabel('Tool attempts')
        for ax in (a,b):ax.grid(alpha=.15)
        b.set_xlabel('Simulated '+key)
        status='complete' if e['complete'] else f"INCOMPLETE {e['completed_turns']}/{e['planned_turns']}"
        fig.suptitle(f"{e['model']} · {case} · {status}\n{e['group']} · {e['id']}",fontsize=10)
        file=e['id']+'.png';fig.savefig(out/file,dpi=110);plt.close(fig)
        links.append(f'<article><h2>{html.escape(e["model"])} — {case}</h2><p>{status}; {html.escape(e["group"])}</p><img loading="lazy" src="{file}" style="width:100%"></article>')
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ResidentBench gallery</title><style>body{font:16px system-ui;max-width:1150px;margin:auto;padding:25px}article{border-top:1px solid #ccc;margin-top:25px}h2{font-size:20px}</style><h1>Recorded episode gallery</h1><p>Descriptive trajectories, not automatic grades. Incomplete prefixes and pilot/repeated groups are labeled. Parcel calls can be rejected; ledger changes show accepted effects.</p>'+''.join(links),encoding='utf-8')
    export(root)
