# Verification Policy

Promote a candidate to verified only when:

- inputs and provenance are explicit;
- code is reproducible from the project root;
- the environment is locked;
- expected outputs and overwrite behavior are defined;
- tests, QC, or sensitivity checks relevant to the claim passed;
- exclusions, random seed, and multiple-testing family are recorded when
  applicable;
- dataset overlap relevant to the claim is resolved;
- limitations and interpretation boundary are written;
- a Git commit anchors the evidence.

Hooks and audits may check deterministic structure. They must not decide
whether a scientific conclusion is true.
