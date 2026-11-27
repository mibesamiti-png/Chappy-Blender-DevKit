# R29 A integration stage 1 — B/C projection bridge

Base 8f0659c19e89869f600403bd8422b50b25af273c; specialist blobs collected unchanged in 13600da84dba7b4d4543f4dd1eec3b06f9120ef0 (12/12). B #200, C #201, D #202: 19 workflow successes. No dev merge.

A introduces parts/blender/joint_panel_bridge_r29.py: explicit registration after existing preview, translation of B availability/selection/ADOPT to C, read-only comparison to configured provider paths and history latch. Existing operators still own execution and actual measurement. No disk hashing or loading on draw; cached provider identity only, as in existing configure. Current candidate selector passed to B. C discards old candidate rows outside READY/NO_CANDIDATE (including ADOPTED_DIMENSION_ONLY); supports complete no-candidate data. Restored state uses START, matching B/D, with explicit restore retained. Specialist stub expected binding updated accordingly.

Stage 1 is not integrated acceptance. Native real-provider panel observations and D independent evidence remain pending, including stale/unavailable behavior, failure/cancel/retry, registration, exact provider identity, protected scene, and three-version checks. No Windows GUI / panel-click claim. No default registration, main/release, arbitrary model, R30 or auto-adoption.
