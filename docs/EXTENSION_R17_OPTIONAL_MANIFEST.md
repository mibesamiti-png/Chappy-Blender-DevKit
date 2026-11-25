# EXT-001 R17 — optional manifest fields

Scope: data-only offline manifest review, not source authentication or extension publishing.

The existing required fields and six strict official CLI fixture cases remain unchanged. The supported optional subset adds:

- `blender_version_max`: an optional exclusive upper bound; the local policy accepts three ASCII numeric components, no leading zeros, and requires a value greater than a syntactically valid minimum. Omission is not a missing owner input.
- `permissions`: optional table of known add-on keys (files, network, clipboard, camera, microphone). Local bounded descriptions are printable, trimmed, 1–64 characters, ending in a letter/digit or closing bracket. Empty table is accepted locally. Nonempty theme declarations, legacy arrays, unknown keys and non-string reasons are rejected locally. These are bounded local review rules, not a claim that every Blender CLI version enforces all of them.
- Unknown top-level fields outside this subset require official validation. Their names and values are redacted, including in direct dictionary-level review, TOML review and official diagnostic comparisons. Known optional diagnostic field identifiers are retained; original paths/reasons/values are never emitted.
- A supplied permission purpose is a declaration, not confirmation of actual need, actual network/filesystem safety, or user consent. Owner inputs (version, maintainer, licensing and real permission needs) and release decisions stay separate from syntactic checking.

Official references: https://developer.blender.org/docs/features/extensions/schema/1.0.0/ and https://docs.blender.org/manual/en/4.5/advanced/extensions/getting_started.html . Actual version-specific CLI evidence is tracked separately.

## CI acceptance

The pre-existing six strict data-only fixtures stay mandatory. Seven additional synthetic fixtures exercise valid optional declarations, malformed/equal maximum, non-table permissions, unknown permission, legacy array and an out-of-subset website. The supported positive must agree with the official validator. Other results explicitly distinguish agreement, disagreement, partial/unclassified observation or outside-supported-subset; these are observations, not additional approval. No arbitrary code, package build, installation, or new network access is introduced; the fixture init sentinel must never be imported.

The existing seven preview archives and 16 MiB archive / 2 MiB member / 64 member limits remain unchanged. No production preview metadata is invented. Actual permissions, remaining optional fields (website, tags, platforms, wheels, build and others), real source and rights, real Extension manifest generation/ZIP/install, GUI and public release remain separate unresolved items. EXT-001 remains partial; no further race research is assigned in this batch.
