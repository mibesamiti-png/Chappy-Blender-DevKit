"""Fixture authoring helper, not part of benchmark or post-holdout tuning."""
import json
from pathlib import Path
out=Path(__file__).parent/'fixtures'

def w(actor='A',epoch=1,revision=0,payload='v1',failpoint=None):
    r=dict(op='write',actor=actor,epoch=epoch,revision=revision,payload=payload)
    if failpoint: r['failpoint']=failpoint
    return r

def h(actor='A',epoch=1,revision=0,next_writer='B',failpoint=None):
    r=dict(op='handoff',actor=actor,epoch=epoch,revision=revision,next_writer=next_writer)
    if failpoint: r['failpoint']=failpoint
    return r

def c():return {'op':'corrupt_checkpoint'}

def row(id,description,events,statuses,writer='A',epoch=1,revision=0,payload='seed',recovery='valid'):
    return {'id':id,'description':description,'events':events,'gold':{'statuses':statuses,'state':dict(writer=writer,epoch=epoch,revision=revision,payload=payload),'recovery':recovery}}

D=[
 row('d01','single regular write',[w(payload='one')],['applied'],revision=1,payload='one'),
 row('d02','normal handoff',[h()],['applied'],writer='B',epoch=2),
 row('d03','old writer after transfer',[h(),w(payload='old')],['applied','rejected'],writer='B',epoch=2),
 row('d04','stale same-writer revision',[w(payload='one'),w(payload='old')],['applied','rejected'],revision=1,payload='one'),
 row('d05','new writer can edit',[h(),w('B',2,0,'beta')],['applied','applied'],writer='B',epoch=2,revision=1,payload='beta'),
 row('d06','interrupt before checkpoint on write',[w(payload='broken',failpoint='before_checkpoint')],['interrupted']),
 row('d07','interrupt before checkpoint on transfer',[h(failpoint='before_checkpoint')],['interrupted']),
 row('d08','human edit protected',[h(next_writer='H'),w('H',2,0,'human'),w('A',1,0,'robot')],['applied','applied','rejected'],writer='H',epoch=2,revision=1,payload='human'),
 row('d09','ABA owner reused stale epoch',[h(),h('B',2,0,'A'),w(payload='stale')],['applied','applied','rejected'],epoch=3),
 row('d10','ABA owner reused fresh epoch',[h(),h('B',2,0,'A'),w('A',3,0,'fresh')],['applied','applied','applied'],epoch=3,revision=1,payload='fresh'),
 row('d11','handoff with stale revision',[w(payload='one'),h()],['applied','rejected'],revision=1,payload='one'),
 row('d12','tampered checkpoint detected',[c()],['applied'],recovery='invalid'),
]
H=[
 row('h01','failed write then retry',[w(payload='bad',failpoint='before_checkpoint'),w(payload='good')],['interrupted','applied'],revision=1,payload='good'),
 row('h02','failed handoff then retry',[h(failpoint='before_checkpoint'),h()],['interrupted','applied'],writer='B',epoch=2),
 row('h03','handoff after write protects prior result',[w(payload='one'),h(revision=1),w('A',1,1,'old')],['applied','applied','rejected'],writer='B',epoch=2,revision=1,payload='one'),
 row('h04','new owner failure and retry',[h(),w('B',2,0,'bad',failpoint='before_checkpoint'),w('B',2,0,'good')],['applied','interrupted','applied'],writer='B',epoch=2,revision=1,payload='good'),
 row('h05','wrong epoch with current revision',[w(payload='one'),w('A',2,1,'stale')],['applied','rejected'],revision=1,payload='one'),
 row('h06','old B writer after B->H',[h(),h('B',2,0,'H'),w('B',2,0,'stale')],['applied','applied','rejected'],writer='H',epoch=3),
 row('h07','old A writer transfer after A->B->A',[h(),h('B',2,0,'A'),h('A',1,0,'C')],['applied','applied','rejected'],epoch=3),
 row('h08','human change then stale AI rewrite',[h(next_writer='H'),w('H',2,0,'human'),h('H',2,1,'A'),w('A',1,1,'robot')],['applied','applied','applied','rejected'],writer='A',epoch=3,revision=1,payload='human'),
 row('h09','failed handoff does not revoke current owner',[h(failpoint='before_checkpoint'),w(payload='continue')],['interrupted','applied'],revision=1,payload='continue'),
 row('h10','failed write does not change transfer revision',[w(payload='broken',failpoint='before_checkpoint'),h()],['interrupted','applied'],writer='B',epoch=2),
 row('h11','checkpoint tamper after legitimate edit',[w(payload='one'),c()],['applied','applied'],revision=1,payload='one',recovery='invalid'),
 row('h12','full ABA with interleaved edits',[w(payload='one'),h(revision=1),w('B',2,1,'two'),h('B',2,2,'A'),w('A',1,2,'old')],['applied','applied','applied','applied','rejected'],epoch=3,revision=2,payload='two'),
]
for filename,rows in [('development.json',D),('holdout.json',H)]:
 (out/filename).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('fixtures:',len(D),len(H))
