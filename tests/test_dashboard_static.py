"""Read-only standalone CBDK live dashboard smoke tests (no network required)."""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "dashboard" / "index.html"


class DashboardStaticTests(unittest.TestCase):
    def test_standalone_and_safety(self):
        page = HTML.read_text(encoding="utf-8")
        self.assertIn('lang="ja"', page)
        self.assertEqual(len(re.findall(r"<script(?:\s[^>]*)?>", page)), 1)
        self.assertNotRegex(page, r"<script[^>]*\bsrc\s*=")
        for identity in ("refresh", "automatic", "sound", "teamA", "teamB",
                         "teamC", "teamD", "progress", "cadence", "tasks",
                         "previewSound", "teamSummary", "teamLead",
                         "waitAfterBCD", "aLead"):
            self.assertIn('id="' + identity + '"', page)
        self.assertIn("api.github.com/repos/", page)
        self.assertIn("raw.githubusercontent.com/", page)
        self.assertIn("textContent", page)
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("Authorization", page)
        self.assertNotIn("localStorage.setItem('token'", page)
        self.assertIn("5*60*1000", page)
        self.assertIn('github("/contents/docs/PARALLEL_ROLLING_QUEUE.md"+qs)', page)
        self.assertIn('previewSound', page)
        self.assertIn('seen:"cbdk-live-v1-seen"', page)
        self.assertIn("if(!firstLoad)newly.push", page)

    @unittest.skipUnless(shutil.which("node"), "Node is optional; Python-only static assertions cover fallback")
    def test_javascript_semantics_offline(self):
        page = HTML.read_text(encoding="utf-8")
        match = re.search(r"<script>\s*([\s\S]+?)\s*</script>", page)
        self.assertIsNotNone(match)
        script = match.group(1)
        needle = "  applyAutomatic();refresh()"
        self.assertEqual(script.count(needle), 1)
        script = script.replace(
            needle,
            "  return {roundFromQueue,taskText,ci,teamStatus,announce,renderSummary,speedMetrics};",
            1,
        )
        js = """
const assert = require('node:assert/strict');
const elements = {};
global.document = { getElementById(id) {
  return elements[id] || (elements[id] = {textContent:'',addEventListener(){},setAttribute(){}});
}};
const dashboard = """ + script + """;
const queue = '## 2026-11-08 — R7統合完了・R8正式割当\\n### R8候補 — B / GLB\\n境界検証\\n\\n### R8候補 — C / UI\\nUIの復元';
const q = dashboard.roundFromQueue(queue);
assert.equal(q.round,8);
assert.match(dashboard.taskText(q.section,8,'B'), /境界検証/);
const five = ['CBDK Python tests','CBDK Windows PowerShell launcher regression',
  'CBDK Blender multi-version runtime smoke',
  'CBDK offline 3D browser interaction smoke','CBDK durable handoff'];
const seven = five.concat(['CBDK Windows kit package','CBDK Agent Skill package']);
const runsFor = (names,sha,event) => names.map((name,i) => ({
  name,head_sha:sha,event,status:'completed',conclusion:'success',
  created_at:new Date(Date.UTC(2026,10,8,0,i)).toISOString(),
  updated_at:new Date(Date.UTC(2026,10,8,1,0)).toISOString(),pull_requests:[]
}));
const b = { number:71,title:'[Team B R8] Safety test',
  head:{sha:'source-b'},created_at:'2026-11-08T00:00:00Z',updated_at:'2026-11-08T04:00:00Z' };
const runs = runsFor(five,'source-b','pull_request');
assert.equal(dashboard.teamStatus('B',8,[b],runs).state,'done');
assert.equal(dashboard.teamStatus('B',8,[b],runs).completedId,'8:B');
assert.equal(dashboard.ci(runs,five,'different','pull_request',71).status,'unknown');
assert.equal(dashboard.ci(runs.slice(1),five,'source-b','pull_request',71).status,'unknown');
const failed = runs.map(x=>({...x}));
failed[0].conclusion='failure';
assert.equal(dashboard.teamStatus('B',8,[b],failed).state,'error');
const a = {number:72,title:'[Team A][R8 integration] Combine',
  created_at:'2026-11-08T02:00:00Z',updated_at:'2026-11-08T05:00:00Z',
  merged_at:'2026-11-08T05:00:00Z',merge_commit_sha:'merge-a'};
assert.equal(dashboard.teamStatus('A',8,[a],runsFor(seven,'merge-a','push')).state,'done');
assert.equal(dashboard.teamStatus('A',8,[a],runsFor(seven,'merge-a','push')).completedId,'8:A');
assert.equal(dashboard.teamStatus('A',8,[a],runsFor(five,'merge-a','push')).state,'running');
// R8 example: CI all green at 01:00, A merged at 05:00.
const c = {...b,number:73,title:'[Team C R8] tests',head:{sha:'source-c'}};
const d = {...b,number:74,title:'[Team D R8] tests',head:{sha:'source-d'}};
const tpr = [b,c,d,a];
const truns = runsFor(five,'source-b','pull_request').concat(
  runsFor(five,'source-c','pull_request'),runsFor(five,'source-d','pull_request'));
const speed = dashboard.speedMetrics(8,tpr,truns,Date.parse('2026-11-08T06:00:00Z'));
assert.equal(speed.teamLeadMinutes,60);
assert.equal(speed.waitMinutes,240);
assert.equal(speed.aLeadMinutes,180);
assert.equal(speed.waitingLive,false);
assert.equal(speed.complete,3);
// Before A merges, show live wait only after all three CI complete.
const live = dashboard.speedMetrics(8,[b,c,d],truns,Date.parse('2026-11-08T02:15:00Z'));
assert.equal(live.waitMinutes,75);
assert.equal(live.waitingLive,true);
const missing = dashboard.speedMetrics(8,[b,c,d],truns.slice(1),Date.parse('2026-11-08T06:00:00Z'));
assert.equal(missing.teamLeadMinutes,null);
assert.equal(missing.waitMinutes,null);
const wrongSHA = dashboard.speedMetrics(8,[{...b,head:{sha:'different'}},c,d],truns,Date.parse('2026-11-08T06:00:00Z'));
assert.equal(wrongSHA.teamLeadMinutes,null);
dashboard.renderSummary([{team:'A',item:{state:'waiting'}},
  {team:'B',item:{state:'done'}},{team:'C',item:{state:'running'}},
  {team:'D',item:{state:'done'}}],8);
assert.match(elements.teamSummary.textContent,/BCD完了 2\/3/);
dashboard.announce([{team:'B',item:{completedId:'8:B'}}]);
assert.equal(elements.flash.textContent,''); // existing completion on initial page load
dashboard.announce([{team:'B',item:{completedId:'8:B'}},
  {team:'C',item:{completedId:'8:C'}}]);
assert.match(elements.flash.textContent,/C 完了を新規検出/);
dashboard.announce([{team:'C',item:{completedId:'8:C'}}]);
assert.equal(elements.flash.textContent,''); // no duplicate alert
console.log('dashboard offline checks passed');
"""
        result = subprocess.run(
            ["node", "-"], input=js, capture_output=True,
            encoding="utf-8", timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dashboard offline checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
