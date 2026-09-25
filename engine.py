"""Constraint solver plus a separate result checker; neither trusts UI validation."""
from collections import Counter, defaultdict
from itertools import combinations
from ortools.sat.python import cp_model
from models import Project, Placement, minutes


def indexes(project):
    return {key: {item.id: item for item in getattr(project, key)} for key in ('classes', 'subjects', 'teachers', 'rooms', 'requirements')}


def occurrences(project):
    return {f'{r.id}:{i+1}': r for r in project.requirements for i in range(r.weekly)}


def interval(project, requirement, day, period):
    c = next(c for c in project.classes if c.id == requirement.class_id)
    shift = next(s for s in project.school.shifts if s.id == c.shift_id)
    p = period - 1
    return day * 1440 + minutes(shift.periods[p].start), day * 1440 + minutes(shift.periods[p + requirement.duration - 1].end)


def blocked(unavailable, day, start, end):
    return any(b.day == day and start < day * 1440 + minutes(b.end) and day * 1440 + minutes(b.start) < end for b in unavailable)


def matches(rule, req):
    return ((not rule.class_id or rule.class_id == req.class_id)
            and (not rule.subject_id or rule.subject_id == req.subject_id)
            and any((not rule.teacher_id or p.teacher_id == rule.teacher_id)
                    and (not rule.group_id or p.group_id == rule.group_id) for p in req.parts))


def selected(rule, req, day, period):
    return (not rule.days or day in rule.days) and (not rule.periods or any(p in rule.periods for p in range(period, period + req.duration)))


def slot_penalty(rule, req, day, period):
    # Preference for a period range means every occupied period must be in range.
    if rule.kind == 'prefer':
        inside = (not rule.days or day in rule.days) and (not rule.periods or all(p in rule.periods for p in range(period, period + req.duration)))
        return 0 if inside else rule.weight
    return rule.weight if selected(rule, req, day, period) else 0


def rule_bucket(rule, req):
    # Teacher-scoped limits count across all their classes; other limits are per class.
    return rule.teacher_id or req.class_id


def validate_project(project: Project):
    errors, warnings = [], []
    ix = indexes(project)
    for key in ix:
        ids = [x.id for x in getattr(project, key)]
        if len(ids) != len(set(ids)):
            errors.append(f'Duplicate IDs in {key}.')
    for name, items in [('shifts', project.school.shifts), ('rules', project.rules)]:
        if len({x.id for x in items}) != len(items):
            errors.append(f'Duplicate IDs in {name}.')
    shifts = {s.id:s for s in project.school.shifts}
    all_groups = set()
    for c in project.classes:
        if c.shift_id not in shifts:
            errors.append(f'{c.name}: unknown shift.')
        pids = [p.id for p in c.partitions]
        if len(set(pids)) != len(pids):
            errors.append(f'{c.name}: duplicate partition IDs.')
        for partition in c.partitions:
            if sum(g.size for g in partition.groups) != c.size:
                errors.append(f'{c.name} / {partition.name}: group sizes must total {c.size}.')
            for g in partition.groups:
                if g.id in all_groups:
                    errors.append(f'Duplicate group ID: {g.id}.')
                all_groups.add(g.id)
        if c.grade == 1:
            warnings.append(f'{c.name}: first-grade seasonal bell times require a separate school-approved profile.')
        if c.grade >= 5 and c.days != list(range(6)):
            warnings.append(f'{c.name}: review departure from the ordinary six-day secondary-school week.')
    for t in project.teachers:
        if any(s not in ix['subjects'] for s in t.subjects):
            errors.append(f'{t.name}: unknown subject qualification.')
    for req in project.requirements:
        if req.class_id not in ix['classes'] or req.subject_id not in ix['subjects']:
            errors.append(f'{req.name}: unknown class or subject.')
            continue
        c, subject = ix['classes'][req.class_id], ix['subjects'][req.subject_id]
        if req.duration > req.max_daily:
            errors.append(f'{req.name}: duration exceeds its daily period limit.')
        if req.partition_id:
            partition = next((p for p in c.partitions if p.id == req.partition_id), None)
            if not partition or len(req.parts) != 2 or {p.group_id for p in req.parts} != {g.id for g in partition.groups}:
                errors.append(f'{req.name}: select both distinct groups from one class partition.')
            grade = c.grade
            eligible = (subject.category == 'foreign' or
                        subject.category == 'informatics' and grade >= 5 or
                        subject.category == 'pe' and grade >= 8 or
                        subject.category == 'technology' and 5 <= grade <= 9 or
                        subject.category in ('military','vocational') and grade >= 10 or
                        subject.category == 'russian' and grade >= 2 and c.language != 'ru' or
                        subject.category == 'uzbek' and grade >= 2 and c.language != 'uz')
            if c.size < 25 or not eligible:
                warnings.append(f'{req.name}: split falls outside the standard eligibility profile; confirm its school authorization (Regulation 140 §29).')
        elif len(req.parts) != 1 or req.parts[0].group_id != '*':
            errors.append(f'{req.name}: a whole-class requirement needs exactly one whole-class part.')
        if len({p.teacher_id for p in req.parts}) != len(req.parts):
            errors.append(f'{req.name}: parallel groups need different teachers.')
        for part in req.parts:
            t = ix['teachers'].get(part.teacher_id)
            if not t:
                errors.append(f'{req.name}: unknown teacher {part.teacher_id}.')
            elif req.subject_id not in t.subjects:
                errors.append(f'{req.name}: {t.name} is not qualified for this subject.')
            if len(set(part.room_ids)) != len(part.room_ids) or any(r not in ix['rooms'] for r in part.room_ids):
                errors.append(f'{req.name}: invalid or duplicate room references.')
    for rule in project.rules:
        for field, collection in [('class_id','classes'),('subject_id','subjects'),('teacher_id','teachers')]:
            value = getattr(rule, field)
            if value and value not in ix[collection]:
                errors.append(f'{rule.name}: unknown {field}.')
        if rule.group_id and rule.group_id not in all_groups:
            errors.append(f'{rule.name}: unknown group.')
        if rule.enabled and not any(matches(rule,r) for r in project.requirements):
            warnings.append(f'{rule.name}: this rule matches no teaching requirements.')
    if not project.requirements:
        errors.append('Add at least one teaching requirement before generating.')
    if sum(r.weekly for r in project.requirements) > 2000:
        errors.append('This local release supports at most 2,000 lesson sessions per week.')
    for c in project.classes:
        total = sum(r.weekly*r.duration for r in project.requirements if r.class_id == c.id)
        if not total:
            errors.append(f'{c.name}: no teaching requirements supplied; the school plan is incomplete.')
        if total > c.max_weekly or total > len(c.days)*c.max_daily:
            errors.append(f'{c.name}: {total} required periods exceed the configured class capacity.')
    for t in project.teachers:
        total = sum(r.weekly*r.duration for r in project.requirements for p in r.parts if p.teacher_id == t.id)
        if t.assigned_weekly is not None and total != t.assigned_weekly:
            errors.append(f'{t.name}: teaching plan assigns {total} periods, but approved allocation is {t.assigned_weekly}.')
        if total > t.max_weekly:
            errors.append(f'{t.name}: {total} assigned periods exceed the configured weekly limit {t.max_weekly}.')
    if project.school.policy_note:
        warnings.append(project.school.policy_note)
    return {'errors': errors, 'warnings': list(dict.fromkeys(warnings))}


def part_size(project, req, part):
    c = next(c for c in project.classes if c.id == req.class_id)
    if not req.partition_id:
        return c.size
    return next(g.size for p in c.partitions if p.id == req.partition_id for g in p.groups if g.id == part.group_id)


def candidates(project, req, ix):
    c = ix['classes'][req.class_id]
    shift = next(s for s in project.school.shifts if s.id == c.shift_id)
    result = []
    for d in c.days:
        for p in range(1, len(shift.periods) - req.duration + 2):
            # A long break separates lesson blocks; do not span it with a double lesson.
            if any(minutes(shift.periods[j+1].start)-minutes(shift.periods[j].end) >= 20 for j in range(p-1,p+req.duration-2)):
                continue
            a,b = interval(project, req, d, p)
            if any(blocked(ix['teachers'][part.teacher_id].unavailable,d,a,b) for part in req.parts):
                continue
            if any(rule.enabled and rule.kind == 'forbid' and matches(rule,req) and selected(rule,req,d,p) for rule in project.rules):
                continue
            options = [[rid for rid in part.room_ids if ix['rooms'][rid].capacity >= part_size(project,req,part) and not blocked(ix['rooms'][rid].unavailable,d,a,b)] for part in req.parts]
            if any(not o for o in options):
                continue
            if len(options)==2 and len(set(options[0]+options[1])) < 2:
                continue
            result.append((d,p,a,b,options))
    return result


def check_schedule(project, placements, previous=None):
    result = validate_project(project)
    if result['errors']:
        return result | {'penalties': [], 'score': None, 'teacher_loads': {}}
    ix, occ = indexes(project), occurrences(project)
    errors = result['errors']
    by_id = {p.occurrence:p for p in placements}
    if len(by_id) != len(placements):
        errors.append('Duplicate lesson occurrence in timetable.')
    missing, extra = set(occ)-set(by_id), set(by_id)-set(occ)
    if missing: errors.append(f'{len(missing)} required sessions are missing.')
    if extra: errors.append(f'Unknown lesson occurrences: {", ".join(sorted(extra))}.')
    resources, class_day, teacher_day, requirement_day = defaultdict(list), Counter(), Counter(), Counter()
    penalty_counts, rule_counts = Counter(), Counter()
    valid = []
    for placed in placements:
        req = occ.get(placed.occurrence)
        if not req: continue
        c = ix['classes'][req.class_id]
        shift = next(s for s in project.school.shifts if s.id == c.shift_id)
        if placed.day not in c.days or placed.period + req.duration - 1 > len(shift.periods):
            errors.append(f'{placed.occurrence}: outside the class timetable.')
            continue
        a,b = interval(project,req,placed.day,placed.period)
        if any(minutes(shift.periods[j+1].start)-minutes(shift.periods[j].end) >= 20 for j in range(placed.period-1,placed.period+req.duration-2)):
            errors.append(f'{req.name}: double lesson crosses a long break.')
        resources[('class',c.id)].append((a,b,placed.occurrence))
        class_day[c.id,placed.day] += req.duration
        requirement_day[req.id,placed.day] += req.duration
        if len(placed.rooms) != len(req.parts):
            errors.append(f'{req.name}: each lesson part needs a room.')
            continue
        for i,part in enumerate(req.parts):
            t = ix['teachers'][part.teacher_id]
            resources[('teacher',t.id)].append((a,b,placed.occurrence))
            teacher_day[t.id,placed.day] += req.duration
            if blocked(t.unavailable,placed.day,a,b): errors.append(f'{req.name}: {t.name} is unavailable.')
            rid = placed.rooms[i]
            room = ix['rooms'].get(rid)
            if rid not in part.room_ids or not room:
                errors.append(f'{req.name}: room {rid} is not allowed.')
                continue
            resources[('room',rid)].append((a,b,placed.occurrence))
            if room.capacity < part_size(project,req,part): errors.append(f'{req.name}: {room.name} is too small.')
            if blocked(room.unavailable,placed.day,a,b): errors.append(f'{req.name}: {room.name} is unavailable.')
        for rule in project.rules:
            if not rule.enabled or not matches(rule,req): continue
            if rule.kind == 'forbid' and selected(rule,req,placed.day,placed.period): errors.append(f'{req.name}: violates rule “{rule.name}”.')
            if rule.kind in ('avoid','prefer'):
                penalty_counts[rule.id] += slot_penalty(rule,req,placed.day,placed.period)
            if rule.kind == 'max_daily' and (not rule.days or placed.day in rule.days):
                rule_counts[rule.id,rule_bucket(rule,req),placed.day] += req.duration
        valid.append(placed)
    for (kind,rid), intervals in resources.items():
        for (a,b,x),(c,d,y) in combinations(intervals,2):
            if a < d and c < b: errors.append(f'{kind} {rid}: {x} overlaps {y}.')
    for (cid,d),v in class_day.items():
        if v > ix['classes'][cid].max_daily: errors.append(f'{cid}: daily class limit exceeded on day {d+1}.')
    for (tid,d),v in teacher_day.items():
        if v > ix['teachers'][tid].max_daily: errors.append(f'{ix["teachers"][tid].name}: daily teacher limit exceeded on day {d+1}.')
    for (rid,d),v in requirement_day.items():
        if v > ix['requirements'][rid].max_daily: errors.append(f'{ix["requirements"][rid].name}: daily subject limit exceeded.')
    rule_ix = {r.id:r for r in project.rules}
    for (rid,bucket,d),v in rule_counts.items():
        r = rule_ix[rid]
        if v > r.limit:
            if r.strength == 'required': errors.append(f'{r.name}: daily limit exceeded for {bucket}, day {d+1}.')
            else: penalty_counts[rid] += (v-r.limit)*r.weight
    penalties = [dict(rule_id=rid,name=rule_ix[rid].name,points=v) for rid,v in penalty_counts.items() if v]
    # Gaps are measured in unused class periods between first/last occupied period.
    slots = defaultdict(set)
    for p in valid:
        r=occ[p.occurrence]
        slots[r.class_id,p.day].update(range(p.period,p.period+r.duration))
    gaps = sum(max(s)-min(s)+1-len(s) for s in slots.values() if s)
    if gaps: penalties.append(dict(rule_id='class_gaps', name='Class timetable gaps', points=gaps*3))
    if previous:
        old = {p.occurrence:p for p in previous}
        moved = sum(p.occurrence in old and (p.day,p.period,p.rooms)!=(old[p.occurrence].day,old[p.occurrence].period,old[p.occurrence].rooms) for p in valid)
        if moved: penalties.append(dict(rule_id='stability', name='Changed existing sessions', points=moved*20))
    loads = {t.id:sum(v for (tid,d),v in teacher_day.items() if tid==t.id) for t in project.teachers}
    return dict(errors=list(dict.fromkeys(errors)),warnings=result['warnings'],penalties=penalties,score=sum(p['points'] for p in penalties),teacher_loads=loads)


def workload(project, placements=None):
    occ = occurrences(project)
    counts = Counter(p.occurrence for p in (placements or []))
    def row(item, requirements):
        required = sum(r.weekly*r.duration for r in requirements)
        scheduled = sum(counts[eid]*r.duration for eid,r in occ.items() if r in requirements)
        approved = getattr(item, 'assigned_weekly', None)
        return dict(id=item.id, name=item.name, approved=approved, required=required,
                    scheduled=scheduled, remaining=required-scheduled,
                    allocation_difference=None if approved is None else required-approved)
    return dict(classes=[row(c,[r for r in project.requirements if r.class_id==c.id]) for c in project.classes],
                teachers=[row(t,[r for r in project.requirements if any(p.teacher_id==t.id for p in r.parts)]) for t in project.teachers])


def solve(project, previous=None, seconds=12, preserve=True):
    previous = previous or []
    initial = validate_project(project)
    if initial['errors']:
        return dict(status='INVALID_INPUT',placements=[],report=initial)
    ix, occ = indexes(project), occurrences(project)
    old = {p.occurrence:p for p in previous}
    invalid_locks = [p.occurrence for p in previous if p.locked and p.occurrence not in occ]
    if invalid_locks:
        return dict(status='INVALID_INPUT',placements=[],report={'errors':['Locked sessions no longer exist: '+', '.join(invalid_locks)],'warnings':initial['warnings']})
    model = cp_model.CpModel()
    choices, room_choices = {}, {}
    domain_cache = {}
    resource_intervals = defaultdict(list)
    class_day, teacher_day, req_day, rule_day, occupancies = [defaultdict(list) for _ in range(5)]
    terms=[]
    rules={r.id:r for r in project.rules if r.enabled}
    for eid,req in occ.items():
        if req.id not in domain_cache:
            domain_cache[req.id] = candidates(project,req,ix)
        domain=domain_cache[req.id]
        prior=old.get(eid)
        if prior and prior.locked:
            domain=[c for c in domain if (c[0],c[1])==(prior.day,prior.period) and len(prior.rooms)==len(req.parts) and all(r in c[4][i] for i,r in enumerate(prior.rooms))]
        if not domain:
            names=[r.name for r in rules.values() if r.kind=='forbid' and matches(r,req)]
            error=f'{req.name} ({eid}) has no valid placement. Check simultaneous teacher availability, eligible room capacity, active days, double-period breaks and locks.'
            if names: error+=' Applicable required time rules: '+', '.join(names)+'.'
            return dict(status='INFEASIBLE',placements=[],report={'errors':[error],'warnings':initial['warnings']})
        options=[]
        for d,p,a,b,room_options in domain:
            x=model.new_bool_var(f'{eid}_{d}_{p}')
            choices[eid,d,p]=x
            options.append(x)
            time_interval=model.new_optional_fixed_size_interval_var(a,b-a,x,f'i_{eid}_{d}_{p}')
            resource_intervals['class',req.class_id].append(time_interval)
            class_day[req.class_id,d].append(x*req.duration)
            req_day[req.id,d].append(x*req.duration)
            for q in range(p,p+req.duration): occupancies[req.class_id,d,q].append(x)
            for i,part in enumerate(req.parts):
                resource_intervals['teacher',part.teacher_id].append(time_interval)
                teacher_day[part.teacher_id,d].append(x*req.duration)
                ys=[]
                for rid in room_options[i]:
                    if prior and prior.locked and rid!=prior.rooms[i]: continue
                    y=model.new_bool_var(f'room_{eid}_{i}_{rid}_{d}_{p}')
                    room_choices[eid,i,rid,d,p]=y
                    ys.append(y)
                    ri=model.new_optional_fixed_size_interval_var(a,b-a,y,f'ri_{eid}_{i}_{rid}_{d}_{p}')
                    resource_intervals['room',rid].append(ri)
                model.add(sum(ys)==x)
            for rule in rules.values():
                if not matches(rule,req): continue
                if rule.kind in ('prefer','avoid'): terms.append(x*slot_penalty(rule,req,d,p))
                elif rule.kind=='max_daily' and (not rule.days or d in rule.days): rule_day[rule.id,rule_bucket(rule,req),d].append(x*req.duration)
        model.add_exactly_one(options)
        if preserve and prior:
            equal=[]
            d,p=prior.day,prior.period
            if (eid,d,p) in choices and len(prior.rooms)==len(req.parts):
                equal=[room_choices.get((eid,i,rid,d,p)) for i,rid in enumerate(prior.rooms)]
            if equal and all(v is not None for v in equal):
                same=model.new_bool_var('same_'+eid)
                model.add_min_equality(same,equal)
                terms.append(20*(1-same))
            else: terms.append(20)
    for values in resource_intervals.values(): model.add_no_overlap(values)
    for (cid,d),values in class_day.items(): model.add(sum(values)<=ix['classes'][cid].max_daily)
    for (tid,d),values in teacher_day.items(): model.add(sum(values)<=ix['teachers'][tid].max_daily)
    for (rid,d),values in req_day.items(): model.add(sum(values)<=ix['requirements'][rid].max_daily)
    for (rid,bucket,d),values in rule_day.items():
        rule=rules[rid]
        if rule.strength=='required': model.add(sum(values)<=rule.limit)
        else:
            excess=model.new_int_var(0,20000,f'excess_{rid}_{bucket}_{d}')
            model.add_max_equality(excess,[0,sum(values)-rule.limit])
            terms.append(excess*rule.weight)
    for c in project.classes:
        shift=next(s for s in project.school.shifts if s.id==c.shift_id)
        for d in c.days:
            occupied=[]
            for p in range(1,len(shift.periods)+1):
                o=model.new_bool_var(f'occ_{c.id}_{d}_{p}')
                model.add(o==sum(occupancies[c.id,d,p]))
                occupied.append(o)
            for p in range(1,len(occupied)-1):
                before=model.new_bool_var(f'b_{c.id}_{d}_{p}')
                after=model.new_bool_var(f'a_{c.id}_{d}_{p}')
                model.add_max_equality(before,occupied[:p])
                model.add_max_equality(after,occupied[p+1:])
                gap=model.new_bool_var(f'g_{c.id}_{d}_{p}')
                model.add(gap>=before+after-occupied[p]-1)
                model.add(gap<=before)
                model.add(gap<=after)
                model.add(gap+occupied[p]<=1)
                terms.append(gap*3)
    model.minimize(sum(terms))
    solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=1
    solver.parameters.random_seed=42
    status=solver.solve(model)
    status_name=solver.status_name(status)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        error=('The combined requirements are impossible under the current teachers, rooms, limits, locks and required rules. No rule was relaxed. This is not a minimal conflict set.' if status==cp_model.INFEASIBLE else 'No complete timetable was found within the search limit. This does not prove the requirements are impossible.' if status==cp_model.UNKNOWN else 'Solver model validation failed: '+model.validate())
        return dict(status=status_name,placements=[],report={'errors':[error],'warnings':initial['warnings']})
    placed=[]
    for (eid,d,p),x in choices.items():
        if not solver.value(x): continue
        req=occ[eid]
        rooms=[next(rid for rid in part.room_ids if (eid,i,rid,d,p) in room_choices and solver.value(room_choices[eid,i,rid,d,p])) for i,part in enumerate(req.parts)]
        placed.append(Placement(occurrence=eid,day=d,period=p,rooms=rooms,locked=bool(old.get(eid) and old[eid].locked)))
    placed.sort(key=lambda p:(p.day,p.period,p.occurrence))
    report=check_schedule(project,placed,previous if preserve else None)
    report['workload']=workload(project,placed)
    if report['errors']: return dict(status='VALIDATION_FAILED',placements=[],report=report)
    return dict(status=status_name,placements=[p.model_dump() for p in placed],report=report,objective=solver.objective_value,best_bound=solver.best_objective_bound,wall_seconds=round(solver.wall_time,3))
