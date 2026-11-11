"""Independent SQLite JSON predicate for the frozen synthetic active-evidence cases.

No import of status_view. This oracle checks recent-observation truth only,
not diagnostics, malformed arbitrary JSON, artifact validity or process life.
"""
import json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SQL='''SELECT coalesce(
 json_extract(r,'$.status')='running'
 AND json_extract(r,'$.work_id')=json_extract(e,'$.work_id')
 AND json_extract(r,'$.target_id')=json_extract(e,'$.target_id')
 AND json_extract(r,'$.attempt_id')=json_extract(e,'$.attempt_id')
 AND json_extract(r,'$.revision')=json_extract(e,'$.revision')
 AND json_type(r,'$.updated_at')='integer'
 AND json_type(r,'$.heartbeat_at')='integer'
 AND json_type(r,'$.verified_steps')='integer'
 AND json_type(r,'$.total_steps')='integer'
 AND json_extract(r,'$.verified_steps') BETWEEN 0 AND json_extract(r,'$.total_steps')
 AND json_extract(r,'$.total_steps') BETWEEN 0 AND 10000
 AND n-json_extract(r,'$.updated_at') BETWEEN 0 AND 300
 AND n-json_extract(r,'$.heartbeat_at') BETWEEN 0 AND 30
 AND json_extract(r,'$.heartbeat_at')<=json_extract(r,'$.updated_at')
 AND json_extract(r,'$.heartbeat_attempt')=json_extract(e,'$.attempt_id'),0)
 FROM (SELECT ? AS r, ? AS e, ? AS n)'''

def verify():
    count=0
    with sqlite3.connect(':memory:') as db:
        for split in ('development','holdout'):
            for row in json.loads((ROOT/'fixtures'/f'{split}.json').read_text()):
                got=bool(db.execute(SQL,(json.dumps(row['record']),json.dumps(row['expected']),row['now'])).fetchone()[0])
                assert got==row['gold_recently_observed'],row['id']
                count+=1
    return dict(sqlite=sqlite3.sqlite_version,cases=count,mismatches=0,scope='recent_observation_on_frozen_synthetic_cases_only')

if __name__=='__main__':print(json.dumps(verify()))
