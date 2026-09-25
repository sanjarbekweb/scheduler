# Raspis reference analysis — 2026-09-14

Sources: [public website](https://raspis.uz/), [features](https://raspis.uz/imkoniyatlar), [public demo](https://app.raspis.uz/?demo=1). Inspected the demo dashboard, assignment matrix, assignment editor and timetable constructor. No account was created and no school data was uploaded.

## Observed in the public demo

- The assignment matrix places classes on one axis and subjects on the other. Cells contain teacher initials, weekly hours and split-group markers.
- Selecting a mathematics assignment opens a matching-teacher list with availability indicators and current/maximum workloads. It also exposes weekly hours and a group-split switch.
- A separate load panel identifies overloaded teachers. The demo reported seven load problems; this shows why completeness and workload compliance need separate indicators.
- The timetable constructor shows many classes together, with day/period rows, subject cards, teacher names and rooms. It provides class, teacher and room views, plus a focused individual selector.
- Its unplaced-lesson panel is grouped by class. The observed demo had 856 of 908 lessons placed, despite a zero-conflict indicator. Zero conflicts alone must never be presented as completion.
- Undo/redo controls, export and timetable duplication are exposed. Their behavior was not tested.
- The assignment data includes 0.5 and 1.5 weekly hours. The UI observation does not establish how these are scheduled across weeks.

## Advertised, not independently verified

The public site describes Excel list import, PDF/Excel export, two shifts, split lessons, room allocation, sharing and subject-difficulty checks. Its speed and hygiene-compliance statements are product claims, not independent evidence about solver correctness or legal compliance.

## Implications for our project

| User need | Current implementation / next work |
|---|---|
| See the entire school week | Added default All classes view with all configured classes in grade order, six day columns, period slots and sticky headings. All rows remain in one scrollable table. |
| Easier class setup | Added a grade-grouped class selector, class-specific subject tables, Add subject and bulk class-name entry prefilled for missing 1A–11B names. Class creation requires actual setup values; no fictional classes were silently inserted. |
| Several teachers per subject | Added subject-team editing; class assignment lists qualified teachers and their workload totals. |
| Drag lessons | Added whole-school drag targets and class-boundary checks. Drop opens the existing move-and-adapt editor; applying it repairs the schedule while retaining locks. |
| Assignment matrix | A useful next option alongside class-by-class editing; not yet implemented. |
| Partial schedules | Not supported by the present solver: it returns a complete validated solution or explains failure. An unplaced tray requires separate draft/partial-state semantics. |
| Alternating weeks | Needed for fractional weekly hours; current model accepts integer weekly sessions only. Do not round fractional hours. |
| Excel mapping | Current input is structured CSV/JSON. An Excel column-mapping wizard remains future work. |
| Precision | Keep completeness, load reconciliation, hard conflicts, preferences and optimality separate. Validate against real school data. |

This is a workflow comparison, not a copy of Raspis source code or a certification of either product.
