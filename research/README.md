# Research metadata

`sources.json` is the committed provenance manifest for CzechCore research.
Downloaded material lives in `.reference/research/` and is excluded from Git.

Validate the manifest schema in any checkout:

```powershell
.venv\Scripts\python -m tools.research.validate_sources --schema-only
```

After provisioning the local research cache, verify every file hash, Git revision,
model-card revision, and collection count:

```powershell
.venv\Scripts\python -m tools.research.validate_sources
```

The manifest records access and license constraints. A source being downloadable
does not imply that CzechCore may redistribute it.

`ijc-outline.json` contains the 22 official IJP chapters and all 202 linked
general explanations as metadata. `geccc-error-types.json` contains aggregate
counts for all 65 Czech ERRANT types in GECCC handle `11234/1-4861`.

`taxonomy.json` joins those two evidence systems into 13 families and 101
correction/reference phenomena. Validate complete one-to-one section/type
assignment with:

```powershell
.venv\Scripts\python -m tools.research.validate_taxonomy
```

`coverage.json` joins every taxonomy phenomenon to current acceptance evidence
and inherited GECCC proxy types. It records missing positive, negative, and
ambiguity evidence instead of treating an untested area as supported.
`benchmark-mapping.json` is the reviewed link between benchmark categories and
phenomena. Rebuild and verify the matrix with:

```powershell
.venv\Scripts\python -m tools.research.build_coverage
.venv\Scripts\python -m tools.research.build_coverage --check
```
