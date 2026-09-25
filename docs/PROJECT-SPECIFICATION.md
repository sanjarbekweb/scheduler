# Maktab Jadval — specification

Release: local single-operator application for an ordinary public school in Uzbekistan. Multi-class scheduling, fictional demonstration data, configurable requirements. Runtime: Python, FastAPI, OR-Tools CP-SAT, SQLite; browser interface without a frontend build step.

## First-release workflow

School setup → teachers / rooms / classes / subjects → teaching requirements → rules → input check → generate → inspect / move / lock → save version → publish snapshot → export / print.

## Data model

- School: name, academic year, curriculum reference, policy review note, six named days, shift-specific bell periods.
- Class: grade, teaching language, student count, active days, shift, daily/weekly limits; named subject-specific partitions whose group sizes total class size.
- Teacher: qualified subject IDs, unavailable clock ranges, maximum teaching periods per day and week.
- Room: capacity, type, unavailable clock ranges.
- Subject: name, display color, optional category for split eligibility guidance.
- Requirement: class, subject, sessions per week, duration (one/two consecutive periods), daily maximum, one whole-class part or two synchronized group parts. Each part has its fixed teacher and eligible rooms.
- Rule: name, enable state, type, scope (class, subject, teacher, group), time selection, hard/preferred strength and penalty, source/note. Types: forbid time, prefer time, avoid time, maximum matching periods per day.
- Schedule: occurrence IDs, day, starting period, assigned rooms, locks, solver status, objective breakdown, independently checked violations, immutable input snapshot.

## Core acceptance criteria

1. Every required occurrence is assigned exactly once.
2. No teacher, room or class can overlap in real time, including different shifts.
3. A synchronized split reserves both teachers and rooms and moves/locks as one session.
4. Each split partition covers the class and has positive group sizes; insufficient room capacity or teacher qualification is rejected.
5. Required rules are respected by generation, manual moves and publication.
6. Preference violations are visible and measured, rather than disguised as hard failures.
7. Invalid references, unsupported rules, broken locks and malformed imports are rejected.
8. No available placement produces a specific diagnosis; a global unsatisfiable model reports a non-minimal conflict explanation; search timeout remains UNKNOWN.
9. Existing placements are a soft stability preference; locked placements are mandatory.
10. Editing inputs marks the draft stale. A stale or invalid draft cannot be published.
11. Published snapshots and saved versions survive application restarts; restored versions are drafts.
12. Users can maintain data through forms, create rules, change availability, import/export project JSON, export timetable CSV and print to PDF.
13. The interface shows the development stage tracker and research limitations.

## Verification cases

Whole-class schedule; parallel groups; insufficient teacher availability; forbidden Monday; soft Monday preference; teacher overlap between shifts; room capacity; group count mismatch; wrong teacher qualification; impossible locked pair; daily limits; double periods; duplicate/missing occurrence; manual conflict; invalid import; stale publication; version restore; JSON round trip; browser form/generate/rule/move/lock/export flows.

## Explicit later work

Student-level electives and independently timed subgroups, mixed-subject rotation bundles, co-teaching, combined classes, date exceptions/holiday expansion, first-grade seasonal profiles, automatic room sharing, teacher portals and roles, authentication, cloud deployment, XLSX integrations, official electronic-journal integrations, production load benchmarks, calendar feeds, external backups and monitoring. These are tracked as later stages, not represented as completed capabilities.

## Pilot inputs still needed

Real class list and teaching language; current approved subject hours and teacher allocations; actual rooms; bell schedules and shifts; subject-specific group sizes; teacher availability and limits; additional school rules. The application remains useful with fictional sample data while these are unavailable.
