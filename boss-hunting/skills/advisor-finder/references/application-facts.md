# Official application facts

Read this reference after the research-fit shortlist is available.

## Search scope

Collect application facts only for shortlisted advisor-program combinations.
Reuse facts already captured while reading advisor, lab, or prospective-student
pages. Query only missing or stale fields.

Use sources in this order:

1. Official graduate-school and program admissions pages.
2. Official university tuition and fee pages.
3. Official university, government, or funder scholarship pages.
4. Verified advisor or laboratory pages for advisor-specific recruiting and
   contact requirements.
5. Official QS pages only for a user-requested ranking edition; medical mode
   does not fetch rank/H-index simply to fill legacy columns.

Do not use community posts to assert deadlines, tuition, materials, or formal
eligibility.

## Required fields

- School name.
- QS overall rank and edition only when requested.
- Program name in English and Chinese when an official translation exists.
- Degree, intake, and official program URL.
- Application deadline, including timezone when stated.
- Tuition with currency and charging period.
- Scholarships, coverage, eligibility, and application path.
- Application requirements and materials in one multiline field.
- Research proposal length or format; use `not_found` if the named official
  sources were checked and no requirement was stated.
- Advisor recruiting and contact requirements in one multiline field.
- Source URLs and last verified date.

Do not translate an unofficial program name as though it were official. Mark a
helpful translation as `assistant translation`.

## Objective feasibility

Keep objective feasibility separate from research fit.

Hard failure examples:

- The official deadline has passed for the target intake.
- The program or advisor explicitly excludes the target degree.
- A stated mandatory qualification is clearly absent from the candidate
  profile.
- A user-declared hard constraint is contradicted.

Warnings, not automatic failures:

- Recruiting or funding is unclear.
- The official page does not state an RP limit.
- A ranking or budget preference is missed unless the user made it a hard
  constraint.
- Sources conflict or appear stale.

Return `eligible`, `ineligible`, or `needs_confirmation`, plus exact reasons.

## Medical application branch

Medical discovery may finish without a program or intake. Mark application
fields `not_checked`/“本次未核验”; do not manufacture IDs or declare eligibility.
Medical application screening accepts a real CV or sufficient structured
`applicantBackground`; preserve whether it is self-reported or documented.
Absence of a CV file alone is not an eligibility failure. Missing a specific
qualification fact leaves that judgment `needs_confirmation`.

For each authentic degree/intake route separately verify:

- Research PhD/DPhil versus clinical professional training, registration or
  combined degrees. `Clinical`, `MD`, a hospital appointment or a medical-school
  name does not establish a licensing prerequisite.
- Current membership of the program's eligible supervisors. Professor/chief/PI
  titles alone do not prove doctoral supervision authority.
- Supervisor agreement, committee admissions, advertised position or structured
  program route; record rotation separately. Country location does not prove a
  route. No PI advert is not a closed committee/rotation program.
- Current doctoral recruitment specifically; postdoc/RA adverts are not PhD
  openings. Last year's expired vacancy closes only that vacancy/intake.
- Program, scholarship and vacancy deadlines independently, with source,
  applicable intake and stated timezone; unknown timezone stays unknown.
- Doctoral tuition/stipend coverage, duration, eligibility, conditions and an
  actual commitment versus a competitive scholarship possibility. PI research
  grant money is not a personal funding guarantee.

Ask citizenship/residency/fee-status only when a concrete official clause needs
it; never infer it from name, language or location. A project with no extra user
hard constraints has no invented constraint, but that does not mean all official
qualifications pass. Recheck opportunity, dates and funding before action.
