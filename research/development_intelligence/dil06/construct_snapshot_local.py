"""One-off manual transcription of exact public GitHub run/jobs evidence.

Source inputs: GET actions/runs?head_sha, GET actions/runs/{id}/jobs,
GET pulls/{pr}. Transcribed only public fixed-id metadata, not private logs.
"""
import json
from pathlib import Path
from measure import REQUIRED

ROOT=Path(__file__).parent
REPO='mibesamiti-png/Chappy-Blender-DevKit'
# family: [run id, created_at, updated_at, required job completion clock times]
# Every CI job is on 2026-11-08 UTC in R13/R14.
observed={
'R13':{
 'B':(100,'f3e83449bb41512771a25010a02002bddf37ec20','2026-11-08T01:55:25Z',{
   'Python':(42436315594,'01:55:29','01:56:12',['01:56:12','01:56:08','01:56:12']),
   'Windows':(42436315598,'01:55:29','01:56:52',['01:56:52','01:56:37']),
   'Blender':(42436330263,'01:55:42','01:58:47',['01:57:20','01:57:40','01:58:46']),
   'Browser':(42436315596,'01:55:29','01:56:09',['01:56:08']),
   'Handoff':(42436315639,'01:55:29','01:55:39',['01:55:38'])}),
 'C':(102,'233738e8294fd7658d378611ba55ab73f5c923f5','2026-11-08T02:22:32Z',{
   'Python':(42438274491,'02:22:36','02:23:38',['02:23:22','02:23:38','02:23:25']),
   'Windows':(42438274540,'02:22:36','02:23:56',['02:23:55','02:23:56']),
   'Blender':(42438274474,'02:22:36','02:25:11',['02:24:23','02:24:53','02:25:10']),
   'Browser':(42438274464,'02:22:36','02:23:09',['02:23:08']),
   'Handoff':(42438274453,'02:22:36','02:22:47',['02:22:46'])}),
 'D':(103,'fa97caaee002b9c9959f5eb8cc75fbb93a9e6ec9','2026-11-08T02:24:06Z',{
   'Python':(42439001914,'02:32:48','02:34:06',['02:33:41','02:34:05','02:33:57']),
   'Windows':(42439001942,'02:32:48','02:34:20',['02:34:19','02:34:16']),
   'Blender':(42439001915,'02:32:48','02:35:37',['02:35:27','02:35:14','02:35:37']),
   'Browser':(42439001920,'02:32:48','02:33:22',['02:33:22']),
   'Handoff':(42439001916,'02:32:48','02:32:58',['02:32:57'])}),
 },
'R14':{
 'B':(107,'a58e070cf1a3516cb49f26558b66d0f494c1f318','2026-11-08T03:32:29Z',{
   'Python':(42443283094,'03:34:24','03:35:31',['03:35:16','03:35:30','03:35:15']),
   'Windows':(42443283121,'03:34:24','03:35:43',['03:35:37','03:35:42']),
   'Blender':(42443283072,'03:34:24','03:37:40',['03:37:14','03:37:40','03:37:35']),
   'Browser':(42443283092,'03:34:24','03:35:01',['03:35:00']),
   'Handoff':(42443283082,'03:34:24','03:34:37',['03:34:36'])}),
 'C':(108,'f6300b28d31dc14cc41f47d3d19eb2b14d76853f','2026-11-08T03:33:11Z',{
   'Python':(42443198800,'03:33:14','03:34:07',['03:34:07','03:34:05','03:34:05']),
   'Windows':(42443198728,'03:33:14','03:34:31',['03:34:23','03:34:31']),
   'Blender':(42443199069,'03:33:14','03:36:08',['03:35:50','03:35:08','03:36:07']),
   'Browser':(42443198705,'03:33:14','03:33:54',['03:33:54']),
   'Handoff':(42443198765,'03:33:14','03:33:25',['03:33:24'])}),
 'D':(106,'f8aea0d30ce7b3c06c6fc2a5ce5732341bb0ae8f','2026-11-08T03:32:12Z',{
   'Python':(42443201866,'03:33:17','03:34:33',['03:34:14','03:34:32','03:34:20']),
   'Windows':(42443201782,'03:33:17','03:34:51',['03:34:50','03:34:45']),
   'Blender':(42443201744,'03:33:17','03:36:55',['03:35:34','03:35:24','03:36:54']),
   'Browser':(42443201739,'03:33:17','03:33:54',['03:33:54']),
   'Handoff':(42443201714,'03:33:17','03:33:33',['03:33:32'])}),
 }
}

def at(s):return '2026-11-08T'+s+'Z'

rounds=[]
for name,teams in observed.items():
    team_entries=[]
    for role,(pr,head,created,flowdata) in teams.items():
        flows=[]
        for family, (run_id, run_created, run_updated, ends) in flowdata.items():
            jobs=[]
            assert len(ends)==len(REQUIRED[family])
            for job_name,clock in zip(REQUIRED[family],ends):
                jobs.append({'name':job_name,'status':'completed','conclusion':'success','head_sha':head,'completed_at':at(clock)})
            if family=='Handoff':
                jobs.append({'name':'Sync latest durable handoff to GitHub main','status':'completed','conclusion':'skipped','head_sha':head,'completed_at':at(ends[-1])})
            flows.append({'family':family,'run_id':run_id,'run_url':f'https://github.com/{REPO}/actions/runs/{run_id}',
                          'head_sha':head,'status':'completed','conclusion':'success',
                          'run_created_at':at(run_created),'run_updated_at':at(run_updated),
                          'job_total':len(jobs),'jobs':jobs})
        team_entries.append({'role':role,'pr':pr,'pr_url':f'https://github.com/{REPO}/pull/{pr}',
                             'head_sha':head,'pr_created_at':created,'workflows':flows})
    int_number,int_created=(104,'2026-11-08T02:44:01Z') if name=='R13' else (117,'2026-11-10T21:24:36Z')
    rounds.append({'round':name,'teams':team_entries,'integration_pr':{'number':int_number,'url':f'https://github.com/{REPO}/pull/{int_number}', 'created_at':int_created}})

# R15 is not a negative verdict: no A integration PR or complete CI snapshots read for this study.
rounds.append({'round':'R15','teams':[
 {'role':'B','pr':120,'pr_url':f'https://github.com/{REPO}/pull/120','head_sha':'70b27ab40b9c129d780fd26fdd177c9e67368b65','workflows':[]},
 {'role':'C','pr':121,'pr_url':f'https://github.com/{REPO}/pull/121','head_sha':'54832e779c5cd26a10e392120bcb7bb2f514b874','workflows':[]},
 {'role':'D','pr':119,'pr_url':f'https://github.com/{REPO}/pull/119','head_sha':'cae75c51c9004d8bbaecdce432761da3d981c31d','workflows':[]},
], 'integration_pr':None, 'note':'R15 observed at 2026-11-10 22:22 UTC. No completed integrated stage; this cycle did not collect its CI. Censored, not failed or waiting.'})

payload={'schema_version':1,'repo':REPO,'recorded_at':'2026-11-10T22:24:00Z','source':'GitHub REST public pull and job API, cited per PR/run', 'rounds':rounds}
(ROOT/'observed.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('snapshot',len(rounds),'rounds',sum(len(t['workflows']) for r in rounds for t in r['teams']),'workflows')
