# Status Model

Use separate status systems.

| Object | States |
| --- | --- |
| Project | `proposed`, `active`, `on_hold`, `completed`, `archived` |
| Task | `backlog`, `ready`, `in_progress`, `blocked`, `done`, `cancelled` |
| Analysis | `draft`, `exploratory`, `candidate`, `verified`, `stable`, `legacy`, `deprecated`, `rejected` |
| Question | `open`, `investigating`, `answered`, `deferred` |
| Observation | `recorded`, `corroborated`, `invalidated` |
| Hypothesis | `proposed`, `testing`, `supported`, `not_supported`, `retired` |
| Evidence | `observed`, `candidate`, `verified`, `invalidated` |
| Decision | `proposed`, `approved`, `rejected`, `superseded` |

Execution does not imply validation. Observation does not imply evidence.
Evidence does not imply an approved decision. An Agent may propose `stable` or
`approved`, but human review grants those states.
