# Codex向け：モデリング研究の再利用ランブック（提案）

Status: **manual runbook, not a registered skill or automation**.

Read AGENTS.md, docs/PARALLEL_DEVELOPMENT.md and the actual development branch before any repository modification. Existing CBDK skill (.agents/skills/chappy-blender-devkit/SKILL.md) governs development; this research runbook does not override it.

## A session prompt

> Work in a standalone local modeling-research project, not in CBDK's runtime source. First read docs/research/MODELING_KNOWHOW_INTAKE.md, docs/research/EXTERNAL_MODELING_REFERENCES.md and docs/research/EXPERIMENT_HANDOFF_TEMPLATE.md. Select exactly one small, reusable research hypothesis (e.g. a low-density curved quad patch or a centerline-swept strap). Search public source documentation for the underlying method; respect access and licensing constraints. Implement only a newly authored local **synthetic** minimal geometry test. Compare base-cage and evaluated counts, Subdivision levels, editing behavior, modifier order, and negative cases. Collect actual Blender-version evidence, source provenance and failures. Produce a handoff record without any private original, geometry, image or identifying local path. Do not edit CBDK's catalog, STATE, Handoff, shared CI, main, release, or third-party approval. Ask A for a narrowly scoped follow-up task if a genuinely reusable helper is justified.

## Learning loop

1. **Retrieve knowledge**: Check existing parts/, catalog/, tests/, docs and the public reference registry before choosing a new implementation.
2. **Design**: State hypothesis and measurable outputs, including what failure would look like.
3. **Prototype**: Use a small isolated synthetic scene. Preserve editable low-poly control cages and non-applied modifiers, when this serves the specific experiment.
4. **Validate**: Record exact environment and actual test results; inspect base and evaluated geometry separately. Include an adversarial counterexample.
5. **Retain**: Write one research record with failure causes, successful parameters and next checks. Keep local assets private.
6. **Transfer**: Submit only a generic redacted research handoff for A review; not a direct change to CBDK's trusted-source allowlists.
7. **Implement later**: If A assigns it, code and test a safe CBDK-authored helper on a separate branch/PR under current gates.

## Human + AI shared Blender scene

Blender MCP actions and a person's manual edits may race or overwrite each other. Do not edit a live object while the other party is modifying it. On handoff, re-fetch scene/object state and explicitly preserve user-adjusted objects. Prefer local checkpoints before destructive experiments. Tool permission to edit Blender is **not** blanket permission to publish a private scene.

## Evidence wording

- "Documentation reviewed": URLs, no execution.
- "Prototype generated": local geometry created, still not quality or generality proof.
- "Synthetic test passed": exact environment/test linked, still not user-project validated.
- "CBDK part integrated": only after correct branch/PR, owner review, CI and state updates.
- "License approved" or "release-ready": only after explicit separate decision.

## Stop rules

Stop and report if a task requires private assets in public CI, execution of scanned third-party addon code, auto-adoption of external packages, a change to another team's owned files, an unapproved source license decision, or an unsupported promise of GUI validation.

**This file is an opt-in research guide**. Do not automatically enroll unrelated Codex sessions or replace the existing CBDK Skill.