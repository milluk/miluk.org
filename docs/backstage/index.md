# Miluk project operations

The source repository and GitHub work records remain authoritative. A hosted developer portal provides navigation and shared context; it does not own the source, editorial decisions, or recovery format.

## Distinct software components

- **miluk.org** is the public website deployed from `main` by GitHub Pages.
- **Miluk dictionary restoration** is the development edition, integrated on `dictionary-1990-reproducibility-repair` through draft PR #1. Experimental lifecycle describes its release status, not the cultural status of the language.

The dictionary publication hold is explicit in `tools/dictionary/PUBLICATION_HOLD.md`. Removing it or publishing the dictionary requires Troy's explicit authorization. Catalog registration, documentation changes, or a PR marked ready do not grant that authorization.

## Work and decisions

Track changes in GitHub issues and pull requests. Record the exact branch and commit for each review; “merged” must identify its destination branch. Preserve original documentary evidence and correction records. Do not hand-edit generated dictionary pages.

Use `catalog-info.yaml` for software identities and relationships. It uses open-source Backstage entity formats without proprietary workspace IDs. The owner reference `user:default/troy` is a catalog reference, not a sign-in permission or authentication configuration.

These pages are ordinary Markdown and can be read directly from GitHub. `mkdocs.yml` also supports rendering them with Backstage TechDocs where its standard builder is available.

See [Portability and recovery](portability.md) for custody and exit expectations.
