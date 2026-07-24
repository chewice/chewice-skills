# Evidence Model

Use the promotion chain:

```text
raw output
→ observation
→ working hypothesis
→ candidate conclusion
→ verified evidence
→ approved decision
→ stable project policy
```

Every evidence record must include:

- a unique `EVID-` ID;
- the claim boundary;
- input and generating code paths;
- validation commands and results;
- environment identity and Git commit; for a managed environment, reference
  its manifest, resolved lock or equivalent snapshot, and a validation command;
- random seed when relevant;
- exclusions and multiple-testing family when relevant;
- dataset overlap status;
- limitations.

Archive a report as a time-specific evidence snapshot, not as an old-file
dump. Record its data version, environment, commit, validation state, and
limitations.

For literature evidence, also record the source query, databases or indexes,
run date, deduplication and exclusion rules, persistent identifiers, and
whether each supported claim was checked against metadata, abstract, or full
text. Do not describe abstract-only evidence as full-text appraisal.
