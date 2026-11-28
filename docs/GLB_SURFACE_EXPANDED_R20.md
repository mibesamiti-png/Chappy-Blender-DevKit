# R20 / F019-01 — explicit expanded surface review (candidate)

Base 547678bfec9b4c1d11aa9d7fb828977ab6d89119; #125 revision 8 active, B-only.
Default legacy_512 path remains schema 1, unchanged CLI. Opt-in Python API:
`run_glb_surface_review(blender, ref, cand, output, profile="expanded_2048")`.
The parent passes the fixed profile name to the trusted Blender subprocess. A owns
the public CLI hook; no shared CLI or CI change in this PR.

## Candidate implementation and verification status

- One canonical validation per input, two deterministic BVH builds shared by fixed
  and adaptive comparisons; all four directed comparisons keep existing sample rules.
- 2048 triangles per input scene is a candidate ceiling, not verified capacity.
  The existing 24 MiB/100000 vertex-reference preflight and parent timeout remain.
- The cumulative sample ceiling 131872 derives from 2*2048*(24+8)+2*10*(48-8).
  Node visits 8000000 and precise triangle evaluations 4000000 are provisional,
  code-owned ceilings pending real measurements; no user-supplied work limits.
  Nodes popped (including pruned pops) and precise distance calls are counted.
  Input size bounds build/feature collection; parent timeout also covers import.
- Work exhaustion returns skipped/not_measured and no partial distance metrics;
  the parent checks status, counts, nested schema, safety, finite metrics,
  sample/evaluation totals and exhaustion evidence. Timeout rejects the report.
- Native smoke adds synthetic 512/1024/2048 scenes, warmup+3 same-condition parent
  roundtrip timings, alternative triangulation, analytic Z=.25 displacement,
  2x2 planar opening with max distance <=1, legacy parity and cap, 2049 rejection,
  dense-overlap budget refusal and original GLB SHA preservation. Core tests
  include a small exhaustive control and forged report/counter negatives.
- No native measurements or CI claims until exact HEAD actual job logs succeed.
  Timing includes Blender startup/import and is not a speedup guarantee; native
  memory and user GLB accuracy remain unmeasured. Fixed vs adaptive metrics
  are separate; a sampled zero is never exact geometry identity.
- No GL research adoption, private inputs, part matcher/viewer expansion,
  automatic source changes, or formal release. All existing gates remain.


## A integration candidate — explicit CLI

B exact HEAD `0ab8defe358c6928f6df00da03836a9638c82eb7` verified 5CI: Python45564719612, Windows45564719807, Chromium45564719637, Handoff45564719797, Blender45564719666 (jobs139036639223/139036639521/139036639695 actual R20 markers). At 2048 each scene, warmup+3 median parent roundtrip 3.965/4.152/6.659s respectively, 131872 samples/2241824 node visits/1054976 triangle evaluations each. Dense adversarial input stops at 4000000 evaluations, no measurements. These are scoped synthetic measurements, not universal capacity or measured speedup from sharing. The default remains 512/schema 1. A adds only explicit CLI selection plus native and mocked CLI checks:

```powershell
python -m cbdk glb-surface-review reference.glb candidate.glb --blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --profile expanded_2048 --output reports/latest/glb_surface_review.json
```

Only this standalone command is expanded; glb-regression and GLB-020 viewer/matcher remain unchanged. Exit 0 means review-only measurement; exit 2 for skip or error, not equivalence. No data upload, auto-apply or research code adoption. Native CLI fixtures reuse B's generated 2048/dense files, verify opt-in/default/skip exit codes, analytic value and source SHA. A candidate CI pending. Not an accepted or released feature.


## 2026-11-25 JST — R20 / F019-01限定受入

#151 B `0ab8defe358c6928f6df00da03836a9638c82eb7` 5CI、#152候補 `910ada89ecf3285d1a45559e39542229fadd0639` 5CI、統合dev `7e8bd21994a3b12dc1282fedc3ceceb4230e6860` 独立7CI成功。Python45566806276、Windows45566806261、Blender45566806341、Chromium45566806269、Handoff45566806324、Kit45566806376、Skill45566806258。実Blender jobs139043471425/139043471439/139043471125、3版各69 lifecycle、R19保持、R20 expanded/CLI marker・archive SHA検証。

2048/sceneの合成GLBのZ=.25/別分割/開口、既定512維持、2049超過と密集4M評価停止、CLI exit2・元SHA不変を確認。2048面中央値（親roundtrip warmup+3）3.904/4.057/4.303秒、131872 samples/2241824 node visits/1054976 exact evals。上限131872/8M/4M、BVH2構築共有。密集停止時測定値なし。速度比較の保証やnative memory、任意実モデルは未確認。旧glb-regression、matcher/viewer上限は不変。研究採用なし。F019-01の今回の限定目標は達成したが、v0.19全体は未完、F019-02/03は残る。#125 rev9 paused、B/C/D待機。次ラウンド自動発行なし。正式v0.17.0/main/last_verified/44要件/24 NEXT状態不変。
