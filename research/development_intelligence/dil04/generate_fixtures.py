"""Synthetic-only test corpus and manually specified labeled tasks.

Gold is typed below; NEVER computed by calling the retrieval implementation.
Do not run after freezing and claiming no post-holdout changes.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
projects={
 'model':'モデル', 'viewer':'ビューア', 'build':'ビルド', 'player':'プレイヤー',
 'stamp':'転写', 'shape':'診断', 'joint':'関節', 'laser':'レーザー'
}
topics={
 'handoff':('引き継ぎ','中断再開','引き継ぎ先は差分を確認し未保存の変更を上書きしない。'),
 'privacy':('非公開データ','私有ファイル','個人所有のモデルや画像を公開CIに送らない。'),
 'ci':('継続検証','CI結果','検証結果は対象コミットSHAと結び付けて報告する。'),
 'geometry':('形状品質','自己交差','メッシュ変更は対象以外の形状退行を検査する。')
}
docs=[]
for pi,(project,pname) in enumerate(projects.items()):
 for ti,(topic,(title,alias,norm)) in enumerate(topics.items()):
  docid=f'{project}-{topic}-r2'
  text=(f'{pname}プロジェクトの{title}基準。{norm} '
        f'固定の評価担当と出典情報を保持する。版差異と環境が不明なら未検証として報告する。'
        f'作業条件を確かめ、必要十分な品質条件が達成されたら追加最適化を停止する。')
  docs.append({'id':docid,'source':f'synthetic/{project}/{topic}.md','project':project,'topic':topic,
               'revision':'current','status':'approved','visibility':'public_synthetic',
               'title':f'{pname} {title}','aliases':[alias,topic], 'text':text})
# retired lookalikes that a naive full dump contains but scoped search must exclude
for project in ('model','viewer','player','shape','joint','laser','stamp','build'):
 docs.append({'id':f'{project}-handoff-r1','source':f'synthetic/old/{project}.md','project':project,
              'topic':'handoff','revision':'retired','status':'approved','visibility':'public_synthetic',
              'title':'引き継ぎ旧版','aliases':['中断再開'],
              'text':'旧基準: 中断後は過去ファイルを確認せず再開してよい。これは廃止された人工例。'})
# sparse query cases rely on surface text aliases, NOT labeled gold ID supplied in query
# hand-author desired document IDs as test oracles
def q(i,project,topics,query,gold,max_docs=3):
 return {'id':i,'project':project,'topics':topics,'query':query,'max_docs':max_docs,'gold_ids':gold}
D=[
 q('d01','model',['privacy'],'3D制作で公開可否のルールを見たい',['model-privacy-r2']),
 q('d02','viewer',['ci'],'画面テストのCIを確認',['viewer-ci-r2']),
 q('d03','build',['handoff','ci'],'担当交代と検証',['build-handoff-r2','build-ci-r2']),
 q('d04','player',[],'私有ファイル',['player-privacy-r2']),
 q('d05','stamp',['geometry'],'転写の品質条件',['stamp-geometry-r2']),
 q('d06','shape',['handoff'],'再開時の引き継ぎ',['shape-handoff-r2']),
 q('d07','joint',[],'自己交差',['joint-geometry-r2']),
 q('d08','laser',['privacy','ci'],'CIと外部共有',['laser-privacy-r2','laser-ci-r2']),
 q('d09','model',[],'中断再開',['model-handoff-r2']),
 q('d10','viewer',['geometry','privacy'],'形状と非公開',['viewer-geometry-r2','viewer-privacy-r2']),
 q('d11','stamp',[],'CI結果',['stamp-ci-r2']),
 q('d12','build',['privacy'],'秘匿情報取り扱い',['build-privacy-r2'])
]
H=[
 q('h01','laser',[],'自己交差',['laser-geometry-r2']),
 q('h02','player',['handoff','privacy'],'再開と権利',['player-handoff-r2','player-privacy-r2']),
 q('h03','shape',[],'私有ファイル',['shape-privacy-r2']),
 q('h04','joint',['ci'],'自動テストの合否',['joint-ci-r2']),
 q('h05','build',[],'中断再開',['build-handoff-r2']),
 q('h06','model',['geometry','ci'],'モデル品質とテスト',['model-geometry-r2','model-ci-r2']),
 q('h07','stamp',[],'自己交差',['stamp-geometry-r2']),
 q('h08','viewer',['privacy'],'公開先の制約',['viewer-privacy-r2']),
 q('h09','laser',['handoff','ci'],'稼働状態と検査',['laser-handoff-r2','laser-ci-r2']),
 q('h10','player',[],'CI結果',['player-ci-r2']),
 q('h11','shape',['geometry'],'形状計測',['shape-geometry-r2']),
 q('h12','joint',[],'私有ファイル',['joint-privacy-r2'])
]
for file,data in [('corpus.json',docs),('fixtures/development.json',D),('fixtures/holdout.json',H)]:
 p=ROOT/file;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('corpus',len(docs),'development',len(D),'holdout',len(H))
