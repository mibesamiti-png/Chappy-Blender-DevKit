# Trigger examples and boundaries

## Invoke this skill

- 「このBlenderアドオン、既存のCBDK部品を再利用して作って」
- 「Surface Stampの面の処理を共通化できるか、ソースを実行せず調べて」
- 「Ball Joint Makerの修正をして、重複候補とbmeshの依存を確認して」
- 「CBDK v0.9の開発を続けて、テストしてGitHubにPRを作って」
- "Use CBDK to inspect helper reuse before building a Blender add-on."
- "The Blender 4.5 GitHub smoke job failed; diagnose it and fix the regression."

## Do not invoke this skill merely for

- General Blender modeling tips or 3D-print painting advice.
- Arbitrary Python projects not using the CBDK repo or reusable helper workflow.
- Searching for Blender addons/products online with no development task.
- Requests to run arbitrary uploaded scripts; never treat such scripts as trusted without review.

## Example expected result

Request: 「CBDKで選択メッシュのヘルパーを改善して」

Workflow: inspect current `parts/blender/context.py`, search catalog for a competing helper, preserve context/selection semantics, add Python regression tests, run actual Python test suite, run Blender smoke CI if relevant, review no private sources got committed, update progress and open/merge a PR only when permitted.

Report the verified status precisely. Do not present `selected`, `blender_smoke_passed`, or unchanged old CI evidence as an unconditional quality certification.
