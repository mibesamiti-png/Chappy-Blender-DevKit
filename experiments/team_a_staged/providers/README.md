# Team A reviewed CJM input

The repository owner authorized public inclusion of CJM on 2026-11-27 JST.
This directory is reserved for the original reviewed **chappy_joint_maker_v042_debug_fix.zip**, SHA-256
`91700f02210e03940eee38f1939f6a7d9778ed9406f902e9359f73bf5f4a88c1`.

The original unmodified archive is present. Keep its digest unchanged.
The separate provider-backed Blender matrix step verifies its digest, fetches the frozen GL commit
recorded in ../gl_manifest.json, and uses the existing native smoke. No provider-backed pass is
claimed until actual logs are reviewed. A missing ZIP skips that step; a present but wrong digest
fails it. Provider-backed CI has passed 72 observations across four environments on ac1e2de353f4a62de0386ef56446e3180e566d7f. Linux GUI ordinary Undo/Redo passed separately; Windows GUI and production sidebar clicks remain unverified. The Windows kit builder must exclude this directory; a packaging regression assertion verifies that boundary. This does not enable the provider in packaged CBDK releases or approve a merge. Do not add other local files.
No new license grant beyond the owner's permission to publish is asserted.
