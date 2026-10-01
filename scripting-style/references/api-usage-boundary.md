# API usage boundaries

Read only when the user or current project supplies an API contract.

Treat the API as an existing opaque capability. The analysis owns visible scientific input preparation and decisions, not the API's hidden algorithms.

## Keep the call understandable

1. Identify the documented import, `source()`, or command; required inputs; scientifically meaningful parameters; and return structure.
2. Keep filtering, grouping, feature choice, sample selection, and other scientific preparation in the main analysis.
3. Load the API near first use using the current project convention.
4. Pass only known arguments. A project API may legitimately read technical constants defined immediately above it; do not claim every example passes all values explicitly.
5. Inspect the returned object using ordinary operations for the target file type.
6. Save only results or derived evidence needed by the next scientific step.

Do not inspect excluded implementations, infer hidden behavior from a function name, copy source into the analysis, build cross-project adapters, or reimplement the API without authorization. Ask the smallest necessary question if a missing contract changes scientific meaning.

A narrow wrapper is justified only by a stable technical repetition needed now, never to support an obsolete signature or hide a defective implementation. Keep cutoffs, groups, targets, lineages, database choices, and other scientific decisions outside it. Fix owned implementation defects and affected known callers within scope. If the cause belongs to an opaque or out-of-scope API, report the mismatch rather than inventing fallback behavior. Explicit conversion to a documented current input format is permitted; make assumptions and information loss visible.
