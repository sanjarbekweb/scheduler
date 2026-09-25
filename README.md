# Maktab Jadval

Local timetable planner for an ordinary public school in Uzbekistan. It keeps the school's approved teacher allocations, places whole-class and synchronized two-group lessons, evaluates required and preferred rules, checks the result independently, and preserves saved or published versions.

## Start on Windows

From the project folder (`D:\Academic\scheduler`):

```powershell
Set-Location D:\Academic\scheduler
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8765
```

If the virtual environment does not exist, install the pinned dependencies first:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). The database is stored in `data/jadval.db`; set `JADVAL_DB` to an explicit path when another local database is needed.

## First use

### Whole-school workflow

#### Split-class lessons: two teachers and two rooms

A split lesson remains one class period. The class students are divided into exactly two halves (normally half plus half); each half receives its own teacher and room, and both halves run at the same day and period. The solver keeps the parts synchronized, prevents teacher and room collisions, and moves both halves together when the lesson is edited.

The timetable now defaults to **All classes · whole week**. Every configured class appears in grade order in one scrollable table. Drag a lesson within its class row and apply **Move & adapt school**; the class assignment itself is changed through Teaching plan.

Teaching plan is organized by class with grade navigation, subject hours, assigned teachers and subject teaching teams. **Add classes** offers missing names from 1A through 11B for bulk setup. Review student counts and shifts before saving; no additional school records are created until you apply the form. Select a subject team to maintain its qualified teachers. Each class assignment then chooses from that subject's teachers, displaying their existing workload.

Create every class, subject, teacher, room and shift in School resources, or import their project JSON. In School hours, paste teaching-plan CSV and review the preview before applying. Resource IDs must match existing resources. Required CSV columns: `id,class_id,subject_id,weekly,teacher_id,room_ids`. Optional columns: `name,duration,max_daily,approved_weekly,partition_id,group_id,teacher_2_id,group_2_id,room_2_ids,teacher_2_approved_weekly`. Separate eligible rooms with `|`. Split groups must refer to an existing class partition. Import replaces the teaching plan; existing versions remain available.

`weekly` is the number of sessions; `duration` is periods per session. Approved teacher hours are weekly teaching periods, not clock hours. The same teacher's approved total must agree across imported rows. School hours compares approved, planned and scheduled totals. Missing class requirements and mismatched supplied teacher allocations prevent generation. Unspecified approved totals remain visibly unspecified; they cannot be independently verified.

Changing inputs automatically attempts regeneration when a draft exists. Failed regeneration leaves the previous timetable visible as stale and reports the issue. Moving a session uses **Move & adapt school**: the requested time and rooms become locked, other unlocked sessions are rearranged, and changed sessions are listed. Existing locks remain required. A failed manual repair makes no saved change. Unlock a session before changing that choice again.

Scheduling uses a constraint algorithm with independent validation. Required conditions are enforced; preferences and preserving existing placements are weighted objectives. FEASIBLE does not mean globally optimal. A timeout does not prove impossibility. The UI allows 120 seconds for generation; API limits can be set up to 600 seconds. Structured CSV/JSON import is implemented; automatic extraction from arbitrary Excel/PDF layouts or free-text rules is not.

Verification includes 20 classes and 60 sessions sharing five teachers and five rooms, plus transactional repair and allocation regressions. Declared input limits are not a performance guarantee for a fully loaded school; benchmark the actual dataset before operational use.

The app starts with fictional demonstration data. Replace it with the school's approved curriculum, actual teacher allocations, student counts, partitions, rooms and bell times. The research screen links to the source register; it deliberately shows policy-review notes where national requirements were not fully consolidated.

1. Review School resources and School settings.
2. Replace demonstration subject hours in Teaching plan.
3. Define two-group partitions from the requirement editor. Both parts are one synchronized session.
4. Add rules such as “never schedule Informatics on Monday” in Rules.
5. Generate and read the health report.
6. Lock reviewed sessions; move unlocked sessions by clicking or dragging.
7. Save a version. Publish only after the school has reviewed the draft.

## What is implemented

- Whole-class requirements and synchronized two-group requirements
- Subject-specific partitions with group sizes
- Two shifts with clock-time overlap checks
- Teacher qualification and availability checks
- Room capacity, type and availability checks
- Required forbids and preferred/avoid rules
- Maximum daily limits for classes, teachers, requirements and rules
- Consecutive double periods
- Independent result validation and conflict reporting
- Manual move, lock/unlock, version history, restore-as-draft
- Project JSON import/export, timetable CSV export, print stylesheet
- Research register and stage tracker screens

## Current limits

The local release supports up to 100 classes, 300 teachers, 200 rooms, 1,500 requirements and 2,000 weekly sessions. It supports two groups per split requirement. Student-level electives, independently timed subgroup activities, combined rural classes, automated tariff allocation, authentication, cloud deployment and electronic-journal integrations are later stages.

## Verification

Run the tests from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest test_engine.py -q
.\.venv\Scripts\python.exe -m pytest test_school.py -q
```

The tests cover seven cases: validation, generation, Monday prohibition, teacher/room conflict detection, lock preservation, required-rule infeasibility, and stale manual schedules.

## Data and privacy

This is a local single-operator application. It has no external database or upload path. Do not place real student personal data in demonstration files. Before school-wide use, add authentication, backups, access controls and the school's data-retention policy.
