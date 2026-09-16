# Portability and recovery

## Custody rules

1. Keep code, corpus provenance, correction ledgers, catalog YAML, and public technical documentation in this repository.
2. Keep private workspace exports, agent transcripts, review records, and account-specific operating policies in a separate private archive. This repository is public: no subdirectory or branch in it provides privacy.
3. Store accepted knowledge as Markdown and structured records as JSON/YAML. Preserve source identifiers, URLs, timestamps, revision numbers, and the distinction between accepted content and pending suggestions.
4. Preserve PR/issue bodies and discussion snapshots in addition to links. Links alone do not preserve their contents.
5. Export before accepting or replacing generated knowledge and after meaningful decisions or work. A backup is only current as of its recorded capture time.
6. Keep a second copy outside the hosted portal and outside GitHub; verify it with checksums. Record export gaps explicitly rather than calling an incomplete snapshot a full backup.

## Recover without Spotify Portal

- Clone the source repository and restore the private archive from its independent copy.
- Register `catalog-info.yaml` in open-source Backstage. Supply the owner entity `user:default/troy` or deliberately map that owner reference to an existing local identity. Do not import vendor authentication IDs or grant sign-in permissions as part of metadata recovery.
- Read exported Markdown directly, or render it with a local Markdown/MkDocs/TechDocs viewer. Convert workspace wiki links to relative Markdown links in the readable export while retaining original Markdown separately.
- Use GitHub or exported issue/PR records for work tracking. Proprietary workspace tasks, PR cards, and graph views are projections of those records, not the only copy.
- Resume work using the source checkout and exported task/session handoff notes. Raw agent transcripts are useful evidence but may not be natively resumable by a different agent runtime.

## Limits of an OSS fallback

Standard Backstage catalog descriptors and Markdown are portable. This does not establish feature parity for Spotify Portal's workspace UI, automatic Wiki synthesis, Xirp orchestration, or licensed plugins such as Soundcheck. Preserve their useful outputs and rule definitions independently. Replacing their execution engines may require additional tools or implementation.

Catalog ingestion and Markdown readability should be tested locally before relying on an exit plan. Restoring metadata is not a test of full Portal feature parity.

## References

- [Backstage entity descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format/)
- [Register a component in Backstage](https://backstage.io/docs/getting-started/register-a-component/)
- [Portal YAML-managed catalog](https://backstage.spotify.com/docs/portal/core-features-and-plugins/catalog)
