"""Authored synthetic traces and independent hand-annotated end-state gold.
Running this again after FREEZE invalidates the experiment. Do not tune holdout.
"""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
DEV='d0'

def e(t, team, head=None, ci='success', scope=True, base=DEV):
    return dict(time=t,team=team,head=head or team+'1',ci=ci,scope_ok=scope,base_sha=base)

def c(id, desc, events, valid, heads=None):
    return dict(id=id,description=desc,dev_sha=DEV,events=events,final_heads=heads or {t:t+'1' for t in 'BCD'},gold_valid=sorted(valid))

def baseline(t1=10,t2=20,t3=30):
    return [e(t1,'B'),e(t2,'C'),e(t3,'D')]

dev=[
 c('d01','staggered green',baseline(),'BCD'),
 c('d02','simultaneous green',baseline(10,10,10),'BCD'),
 c('d03','same SHA repeated status',[e(5,'B',ci='pending'),e(10,'B'),e(20,'C'),e(30,'D')],'BCD'),
 c('d04','B revision replaced then green',[e(5,'B'),e(10,'B','B2',ci='pending'),e(20,'C'),e(25,'B','B2'),e(30,'D')],'BCD',dict(B='B2',C='C1',D='D1')),
 c('d05','D final CI missing',[e(10,'B'),e(20,'C'),e(30,'D',ci='missing')],'BC'),
 c('d06','C wrong base',[e(10,'B'),e(20,'C',base='other'),e(30,'D')],'BD'),
 c('d07','B scope conflict',[e(10,'B',scope=False),e(20,'C'),e(30,'D')],'CD'),
 c('d08','late failed C',[e(10,'B'),e(20,'C'),e(30,'D'),e(40,'C',ci='failed')],'BD'),
 c('d09','final head higher than seen',baseline(),'CD',dict(B='B2',C='C1',D='D1')),
 c('d10','one PR not submitted',[e(10,'B'),e(30,'D')],'BD'),
 c('d11','head cycles back after pending',[e(4,'B'),e(8,'B','B2',ci='pending'),e(12,'B'),e(20,'C'),e(30,'D')],'BCD'),
 c('d12','older head CI success must not count',[e(10,'B'),e(15,'B','B2',ci='pending'),e(20,'C'),e(30,'D')],'CD',dict(B='B2',C='C1',D='D1')),
]
held=[
 c('h01','B 7 minutes before C, D',baseline(0,420,450),'BCD'),
 c('h02','D first, C last',[e(0,'D'),e(50,'B'),e(90,'C')],'BCD'),
 c('h03','all green instant',[e(20,'B'),e(20,'C'),e(20,'D')],'BCD'),
 c('h04','B new head after prior pre-review',[e(5,'B'),e(10,'C'),e(11,'B','B2',ci='pending'),e(15,'D'),e(30,'B','B2')],'BCD',dict(B='B2',C='C1',D='D1')),
 c('h05','D never green',[e(2,'B'),e(3,'C'),e(4,'D',ci='failed')],'BC'),
 c('h06','C mistakenly stamped old base',[e(2,'B'),e(3,'C',base='old'),e(4,'D')],'BD'),
 c('h07','B is missing exact final head',[e(2,'B'),e(3,'C'),e(4,'D')],'CD',dict(B='B3',C='C1',D='D1')),
 c('h08','B green -> failed -> green same head',[e(2,'B'),e(3,'B',ci='failed'),e(4,'C'),e(5,'B'),e(6,'D')],'BCD'),
 c('h09','wrong D path authority',[e(2,'D',scope=False),e(4,'C'),e(10,'B')],'BC'),
 c('h10','C changes HEAD twice',[e(2,'C'),e(3,'B'),e(4,'C','C2'),e(8,'C','C3',ci='pending'),e(11,'D'),e(20,'C','C3')],'BCD',dict(B='B1',C='C3',D='D1')),
 c('h11','a review can be staged before final all green',[e(0,'B'),e(100,'C'),e(200,'D')],'BCD'),
 c('h12','new D HEAD has no matching CI',[e(0,'D'),e(10,'B'),e(20,'C'),e(21,'D','D2',ci='missing')],'BC',dict(B='B1',C='C1',D='D2')),
]
for filename,rows in [('development',dev),('holdout',held)]:
    (P/'fixtures'/f'{filename}.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
