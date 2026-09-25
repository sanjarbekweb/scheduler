# Uzbekistan school timetabling research

Research date: 14 September 2026. Scope: ordinary public general secondary schools. This is the source register and design basis for the local application, not certification of a school's timetable.

## Verified framework

Regulation 140, paragraphs 24–25, describes a four-quarter school year, normally 34 teaching weeks (33 for grade 1), a six-day week with a pedagogical-council five-day option for grades 1–4, 45-minute lessons, and ordinary/long breaks. Paragraph 29 permits two-group teaching when qualified staff suffice and class size is at least 25: foreign languages grades 1–11; IT 5–11; PE 8–11; technology 5–9; pre-conscription and vocational education 10–11; Uzbek 2–11 in non-Uzbek-medium schools; Russian 2–11 in non-Russian-medium schools. These are permissions, not instructions to split every eligible class. Paragraphs 31–32 connect teaching to the annual curriculum and explanatory letter. [Official current regulation 140](https://lex.uz/uz/docs/-3137130).

Regulation 3271 establishes the teaching-hour grid and pedagogical-council allocation process. Paragraph 15's revised priority order took effect on 1 August 2026. The scheduling software should receive approved teacher allocations and retain their provenance. It should not redistribute contractual teaching hours to make a timetable easier. [Official regulation 3271, paragraphs 13–20](https://lex.uz/uz/docs/4919258).

The official sanitary registry links school standard 0341-16 and amendment records. Its linked base PDF's section 10 contains rules for shifts, grade-sensitive daily loads, alternating demanding subjects, breaks and first-grade adaptation. It specifies ordinary breaks of at least 10 minutes, long breaks of 20–30 minutes, and at least 30 minutes between shifts. Some passages contain old grade ranges and tables; they must be read with amendments. [Official registry](https://gov.uz/oz/sanepid/pages/sanitariya-va-gigiena-me-yorlari-hamda-qoidalari), [linked base document](https://api-portal.gov.uz/uploads/136/2025/05/13/915b0cf5-fcfb-07d1-d76f-dbc0911edd6c_media_.pdf).

The September 2023 amendment extends several provisions to grade 11, including the first-shift provision for graduating classes and subject-difficulty tables. This demonstrates why an old PDF alone is insufficient. [Official amendment, especially items 3–8](https://lex.uz/docs/6623002).

## Evidence requiring care

1. The 2025 Sanepid public guidance gives some daily-load ranges different from the linked base standard. Regulation 140 also describes breaks differently. The application therefore records configurable school limits and exposes a policy-review notice; it does not label the sample configuration legally certified. [Sanepid guidance](https://gov.uz/oz/sanepid/news/view/79343).
2. A 2026–27 curriculum document attributed to Ministry Order 133 dated 10 April 2026 is available through a third-party education site. An issuing-authority copy was not verified during this pass. Exact national subject-hour tables are consequently not installed as approved defaults. [Located copy and attribution](https://idum.uz/uz/archives/23555).
3. The sanitary registry's 2022 amendment entry links to the 2023 amendment. A complete consolidated text and all amendment effects remain to be confirmed before national compliance can be asserted.
4. School bell times, room inventory, language of instruction, approved curriculum, staff allocations, availability, and split decisions remain school inputs.

## How a timetable is assembled

The following is a proposed product workflow derived from the documents, not a claim that every school uses identical software or procedures:

1. Select school type, academic year and language; obtain the applicable annual curriculum and explanatory letter.
2. Establish classes, student counts and teaching shifts.
3. Enter each class's subject hours from the school's approved plan.
4. Attach the school's assigned teachers and their availability.
5. Define subject-specific group partitions and the teachers for both sides.
6. Enter actual rooms, capacities, bell times and unavailable periods.
7. Add institutional constraints and preferences.
8. Generate candidate schedules across all classes together.
9. Independently check the result, review unresolved policy warnings, and revise.
10. Preserve a published version; make later revisions as separate drafts.

## What the screenshot establishes

The user identified the screenshot as one class. It shows Monday–Saturday teaching, 45-minute periods, and paired entries at identical times for certain subjects. It does not establish the class grade, group membership, authorized curriculum hours, or physical room availability. “Kabinet yo‘q” indicates no recorded room; it does not establish unlimited room capacity. The demonstration data uses fictional staff and illustrative hours.

## Design consequences

- Reserve both teachers and both rooms for a synchronized split session.
- Count one shared period once in class/student hours, but once for each teacher in staffing hours.
- Define partitions per subject; never assume the same group membership across subjects.
- Reserve the full class during a complete split bundle. This conservative first release prevents hidden subgroup conflicts without collecting student names.
- Keep rule provenance, school-year reference and validation state with school configuration.
- Check actual clock overlap across shifts, not merely matching period numbers.
- Never relax a required rule silently. A time limit is not proof of impossibility.
- Preserve input snapshots with timetable versions so later policy changes do not rewrite history.

## Open research for real-school rollout

Confirm the issuing-authority 2026–27 curriculum, consolidated sanitary amendments, first-grade seasonal schedule, the school's approved bell schedule and shift decisions, teacher workload definitions, and the school's operational approval procedure. Specialized, boarding, home instruction and combined rural classes require separate profiles.
