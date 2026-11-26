"""Observe the unchanged public dashboard's phase semantics, offline only.

Execute only repository-owned pinned HTML in a Node stub, mirroring the
existing test_dashboard_static harness. Never consume arbitrary HTML/files.
"""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
html=(ROOT/'docs/dashboard/index.html').read_text()
script=re.search(r'<script>\s*([\s\S]+?)\s*</script>',html).group(1)
needle='  applyAutomatic();refresh()'
assert script.count(needle)==1
script=script.replace(needle,'  return {ci,teamStatus};',1)
js='''const elements={};
global.document={getElementById(id){return elements[id]||(elements[id]={textContent:'',addEventListener(){},setAttribute(){}});}};
const dashboard='''+script+''';
const p={number:1,title:'[Team B R14] synthetic',head:{sha:'synthetic'},updated_at:'2026-11-01T00:00:00Z'};
console.log(JSON.stringify({missing_ci:dashboard.teamStatus('B',14,[p],[]),no_integration_pr:dashboard.teamStatus('A',14,[],[])}));
'''
r=subprocess.run(['node','-'],input=js,text=True,capture_output=True,timeout=10,check=True)
print(json.dumps(dict(source_sha256=hashlib.sha256(html.encode()).hexdigest(),node=subprocess.check_output(['node','--version'],text=True).strip(),observations=json.loads(r.stdout),interpretation='workflow phase is not executor liveness'),indent=2))
