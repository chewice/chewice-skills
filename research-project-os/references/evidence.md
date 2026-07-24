# Evidence

Promote deliberately:

```text
raw output → observation → hypothesis → candidate → verified evidence
→ approved decision → stable policy
```

Evidence records need an `EVID-` ID, claim boundary, inputs, generating code,
validation results, environment manifest and lock, Git commit, exclusions,
limitations, and dataset-overlap status. Add random seed and multiple-testing
family when relevant.

Verify only when provenance is explicit, execution is reproducible from the
project root, the environment is locked, overwrite behavior is defined, and
claim-relevant tests or sensitivity checks passed. Structural audit never
establishes scientific truth.

For literature evidence, record query, sources, run date, deduplication,
exclusions, identifiers, and whether support came from metadata, abstract, or
full text.
