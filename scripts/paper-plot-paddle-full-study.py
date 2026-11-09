"""Plot the selected publication traces with full paddle collision spans."""
import hashlib
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from paddle_plot_evidence import ROOT, band, crossings


def main():
    pdfmetrics.registerFontFamily('Helvetica',normal='Helvetica',bold='Helvetica-Bold')
    selected=json.loads((ROOT/'code/evaluations/repetitions-complete-coverage-20261102.json').read_text())['episodes']
    out=ROOT/'results/paper-figures/paddle-luna-llama.pdf';c=canvas.Canvas(str(out),pagesize=(600,470))
    c.setTitle('Illustrative paddle trajectories with full paddle spans');c.setAuthor('Fereydoun Farrahi Moghaddam')
    def text(x,y,s,size=12,color='#263345'):
        c.setFont('Helvetica',size);c.setFillColor(HexColor(color));c.drawString(x,y,s)
    def line(points,color,width=1):
        p=c.beginPath();p.moveTo(*points[0])
        for q in points[1:]:p.lineTo(*q)
        c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.drawPath(p)
    audit=[]
    for k,(model,name) in enumerate([('openai/gpt-6-luna','GPT-6 Luna'),('meta-llama/llama-4-maverick','Llama 4 Maverick')]):
        e=next(e for e in selected if e['model']==model and e['scenario']=='paddle');p=ROOT/e['directory'].replace('\\','/')/'run-0.jsonl'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==e['evidence_sha256']['run-0.jsonl']
        rows=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()]
        states=[rows[0]['env']]+[s for r in rows for s in [r['env'],*r['after_calls'],*r['trajectory']]]
        events=crossings(rows);bottom=292-k*215;h=115
        xy=lambda t,y:(65+520*t/30,bottom+h*(14-y)/14)
        text(65,bottom+h+18,f'({chr(97+k)}) {name}',14)
        for y in [0,7,14]:
            xx,yy=xy(0,y);line([(65,yy),(585,yy)],'#e5e9ef',.6);text(38,yy-4,str(y),12)
        for left,right in zip(states,states[1:]):
            if left['vx']>0:
                x,_=xy(left['seconds'],14);end,_=xy(right['seconds'],14)
                c.setFillColor(HexColor('#edf1f6'));c.rect(x,bottom,max(0,end-x),h,fill=1,stroke=0)
        band(c,states,xy,HexColor('#c8dff2'))
        line([xy(s['seconds'],s['right_y']) for s in states],'#2563a6',1.1)
        for left,right in zip(states,states[1:]):
            if (left['score_left'],left['score_right'])==(right['score_left'],right['score_right']):
                line([xy(left['seconds'],left['ball_y']),xy(right['seconds'],right['ball_y'])],'#6c7784',.8)
        for event in events:
            line([xy(event['seconds'],event['paddle_y']-2.5),xy(event['seconds'],event['paddle_y']+2.5)],'#2563a6',.8)
            x,y=xy(event['seconds'],event['ball_y']);c.setStrokeColor(HexColor('#176a42'));c.setLineWidth(1)
            if event['hit']:c.circle(x,y,2.8,stroke=1,fill=0)
            else:
                line([(x-3,y-3),(x+3,y+3)],'#a22e39',1.1);line([(x-3,y+3),(x+3,y-3)],'#a22e39',1.1)
        text(5,bottom+h/2,'Row',12)
        for r in rows:
            t=r['env']['seconds'];x=65+520*t/30
            if any(n=='read_screen' for n,a in r['tool_calls']):line([(x,bottom-12),(x,bottom-18)],'#667788',.8)
            for n,a in r['tool_calls']:
                if n=='set_right_paddle':
                    yy=bottom-30;c.setFillColor(HexColor('#bd5b25'));c.circle(x,yy,2,fill=1,stroke=0)
        text(5,bottom-17,'Read',11);text(5,bottom-34,'Act',11)
        for t in [0,10,20,30]:x,y=xy(t,14);text(x-5,bottom-52,str(t),12)
        audit.append(dict(model=model,source=e['directory'],recorded_returns=states[-1]['right_hits'],verified_return_markers=sum(v['hit'] for v in events),missed_face_crossings=sum(not v['hit'] for v in events)))
    text(235,5,'Simulated seconds',13)
    c.save();print(json.dumps(audit))


if __name__=='__main__':main()
