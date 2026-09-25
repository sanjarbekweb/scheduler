# Maktab Jadval — project stages

Updated: 2026-09-14. Target: ordinary public school in Uzbekistan.
User authorized research followed by implementation, with updates at every completed stage.

| Stage | Status | Completion evidence |
|---|---|---|
| 1. Research and source register | Complete for first release | UZBEKISTAN-RESEARCH.md; remaining national-compliance questions explicitly recorded |
| 2. Product specification and acceptance criteria | Complete | PROJECT-SPECIFICATION.md includes 13 acceptance criteria and later scope |
| 3. Scheduling engine and independent validation | Complete | `outputs/scheduler/engine.py`; seven passing engine tests |
| 4. Working administration application | Complete for local release | `outputs/scheduler/server.py` and `static/`; browser generated 46-session timetable |
| 5. Tests and browser verification | Complete for local release | `test_engine.py`: 7 passed; Playwright browser flow: generation, rules screen, API validate/export/lock/version/publish |
| 6. Local delivery and operating instructions | Complete | `outputs/scheduler/README.md`, pinned `requirements.txt` |
| 7. Real-school pilot and production rollout | Not started | Requires actual school data, confirmed curriculum and hosting decisions |
| 8. Whole-school accounting and adaptive edits | Complete for local release | Approved teacher allocation checks; class/teacher workload dashboard; transactional manual repair; 20-class shared-resource regression |
| 9. Bulk teaching-plan import | Complete for structured CSV/JSON | CSV preview, reference validation, split-group assignments and optional approved teacher hours; arbitrary document extraction remains future work |
| 10. Raspis-inspired product surface | Complete for inspected public workflows | Indigo landing page, dashboard, dense whole-school timetable matrix, assignment matrix, class/subject setup and local navigation; private backend/account features remain out of scope |

## Scope decisions

- Build a complete local first release, with explicit limits documented separately from later production work.
- Preserve assigned teachers; automatic tariff allocation is outside this scheduler.
- Whole-class and synchronized two-group sessions are required in the first release.
- User-defined required and preferred scheduling rules are required.
- No actual student identities or screenshot teacher names will be used as demonstration data.
- Official curriculum tables will not be fabricated. Demonstration hours must be labelled as examples.
- No automatic national-compliance claim: unresolved annual and sanitary source issues must remain visible.

## Activity log

- 2026-09-14: Added default all-classes weekly table, whole-school drag targets, class-organized teaching plan, subject teaching teams and bulk class setup. Inspected Raspis public demo; comparison and remaining gaps recorded in RASPIS-ANALYSIS.md.
- 2026-09-14: Added Raspis-inspired public landing page, indigo visual system, readiness dashboard, dense class-column timetable, and class × subject assignment matrix. Verified landing page and 22-class whole-school matrix in the browser; all 11 tests and JavaScript syntax checks pass.

- 2026-09-14: Added whole-school hour reconciliation, exact approved teacher allocation checks, CSV preview and automatic regeneration after input changes. Manual moves lock the requested choice and repair the remaining timetable; failed repairs retain the saved draft. Seven original tests and four new whole-school/API regressions passed, including a 20-class, 60-session shared-resource case. This is not a full-load production benchmark.

- 2026-09-14: Confirmed ordinary public school and implementation scope with user.
- 2026-09-14: Identified subject/grade/language-dependent split eligibility in regulation 140, paragraph 29.
- 2026-09-14: Identified separate teacher-hour allocation workflow in regulation 3271.
- 2026-09-14: Identified discrepancies between sanitary source text and 2025 public guidance; preserving provenance.
- 2026-09-14: Completed initial research and scoped first-release specification. National certification remains outside the evidence available.
- 2026-09-14: Implemented the local solver, independent checker, API, SQLite persistence and administration interface.
- 2026-09-14: Installed dependencies; all seven engine tests passed.
- 2026-09-14: Browser-verified generation (46 sessions), split-group display, rules editor, validation, CSV export, lock/unlock and immutable draft/published versions.
- 2026-09-14: Relocated the completed project to `outputs/scheduler` and updated launch, test and stage references.
