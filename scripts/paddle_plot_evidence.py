"""Offline paddle-face crossings and full collision span for scientific plots."""
from pathlib import Path
import math
import sys

PUBLIC_ROOT=Path(__file__).resolve().parents[1]
ROOT=PUBLIC_ROOT/'study'
sys.path.insert(0,str(PUBLIC_ROOT))
from residentbench import pong

HALF_SPAN=pong.HALF+.5


def crossings(rows,seed=20261029):
    env=pong.PaddleScreen(seed=seed);events=[]
    for row in rows:
        for name,args in row['tool_calls']:
            if name=='set_right_paddle' and args.get('direction') in ('up','down','stationary'):
                env.motion=args['direction']
        for sample in row['trajectory']:
            end=sample['seconds']
            while env.time<end-1e-10:
                dt=min(pong.DT,end-env.time);before=env.snapshot();env.tick(dt);after=env.snapshot()
                face=pong.RIGHT_X-1
                if before['vx']>0 and before['ball_x']<=face<=before['ball_x']+before['vx']*dt:
                    fraction=(face-before['ball_x'])/(before['vx']*dt)
                    y=before['ball_y']+before['vy']*dt
                    if y<1:y=2-y
                    elif y>pong.HEIGHT-2:y=2*(pong.HEIGHT-2)-y
                    contact=before['ball_y']+fraction*(y-before['ball_y'])
                    hit=after['right_hits']>before['right_hits']
                    assert hit==(abs(contact-after['right_y'])<=HALF_SPAN)
                    events.append(dict(seconds=before['seconds']+fraction*dt,ball_y=contact,
                        paddle_y=after['right_y'],hit=hit))
            env.time=end
            for name in ('right_y','ball_x','ball_y','right_hits','score_left','score_right'):
                if not math.isclose(getattr(env,name),sample[name],rel_tol=1e-12,abs_tol=1e-9):
                    raise ValueError(f'Offline plot replay differs in {name}')
    assert sum(e['hit'] for e in events)==rows[-1]['trajectory'][-1]['right_hits']
    return events


def band(canvas,states,scale,color):
    """Full continuous contact span; no smoothing or inferred judgments."""
    p=canvas.beginPath();p.moveTo(*scale(states[0]['seconds'],states[0]['right_y']-HALF_SPAN))
    for s in states[1:]:p.lineTo(*scale(s['seconds'],s['right_y']-HALF_SPAN))
    for s in reversed(states):p.lineTo(*scale(s['seconds'],s['right_y']+HALF_SPAN))
    p.close();canvas.setFillColor(color);canvas.drawPath(p,fill=1,stroke=0)
