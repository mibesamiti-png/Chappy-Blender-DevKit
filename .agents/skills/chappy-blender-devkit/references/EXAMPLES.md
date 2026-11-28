# When to invoke the CBDK skill

Use on requests such as:

- 「CBDKの開発をGitHubから引き継いで続けて」
- 「今のv0.18の残タスクをまとめて実装して」
- 「UI-001の生成パネルの挙動をBlender 3版で検証して」
- 「EXT-001のextension-preflightがリリース不可と判定する理由を調べて」
- 「GLB-020/021/022の合成差分を見て誤検出を減らして」
- 「Codexでの進捗・CI・Notion同期まで実施して」
- "Continue CBDK from its GitHub state, implement and verify a batch."

Do not invoke just for:

- An unrelated Blender modeling or sculpting tutorial.
- Buying products, painting 3D prints or searching for 3D meshes.
- Running arbitrary third-party source without explicit review.
- General Python development in a different repository.

Expected behavior for "CBDKの開発を続けて":
read the *live* GitHub handoff and project state; choose the most
valuable open safe batch; implement and test it; distinguish Python,
real Blender, Chromium and human GUI results; update state/handoff
and progress; preserve draft PR/preview-only gates; sync public-safe
milestone to existing Notion page if connected. If blocked, describe
the exact missing evidence and next action. Do not silently invent
rights or close real-data tasks with synthetic-only evidence.
