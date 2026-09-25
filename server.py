"""Local single-operator API. Immutable versions; optimistic revision checks."""
import csv
import hashlib
import io
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from models import Project, Placement, GenerateRequest, MoveRequest, RevisionRequest, LockRequest, SaveRequest, VersionRequest, TeachingImportRequest, Requirement
from demo import demo_project
from engine import solve, check_schedule, validate_project, occurrences, workload

BASE=Path(__file__).resolve().parent
DB=Path(os.environ.get('JADVAL_DB',str(BASE/'data'/'jadval.db')))
DB.parent.mkdir(parents=True,exist_ok=True)
mutex=threading.RLock()
app=FastAPI(title='Maktab Jadval',version='1.0.0')
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])


def now(): return datetime.now(timezone.utc).isoformat()
def encode(value): return json.dumps(value,ensure_ascii=False)
def fingerprint(project): return hashlib.sha256(json.dumps(project,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def connection():
    db=sqlite3.connect(DB,timeout=30)
    db.row_factory=sqlite3.Row
    return db


def initialize():
    with connection() as db:
        db.executescript('CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY, payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);')
        if not db.execute('SELECT 1 FROM state WHERE id=1').fetchone():
            db.execute('INSERT INTO state VALUES(1,?)',(encode(dict(revision=1,project=demo_project().model_dump(),draft=None,published_id=None,activity=[dict(at=now(),text='Fictional demonstration project created.')])),))


initialize()


def state():
    with connection() as db: return json.loads(db.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])


def store(s,text):
    s['revision']+=1
    s['activity']=(s['activity']+[dict(at=now(),text=text)])[-200:]
    with connection() as db: db.execute('UPDATE state SET payload=? WHERE id=1',(encode(s),))
    return s


def require_revision(s,revision):
    if revision!=s['revision']: raise HTTPException(409,'The project changed in another window. Reload before retrying.')


def current_draft(s):
    d=s['draft']
    if not d or d['input_hash']!=fingerprint(s['project']): raise HTTPException(409,'The timetable is missing or stale. Generate again using the current inputs.')
    return d


@app.middleware('http')
async def local_write_only(request:Request,call_next):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        origin=request.headers.get('origin')
        expected=f'{request.url.scheme}://{request.headers.get("host","")}'
        if origin and origin!=expected:
            return Response('Cross-origin changes are not allowed.',status_code=403)
        if int(request.headers.get('content-length','0') or 0)>5_000_000:
            return Response('Project exceeds the 5 MB request limit.',status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response


@app.get('/api/state')
def get_state(): return state()


@app.put('/api/project')
def save_project(body:SaveRequest):
    with mutex:
        s=state(); require_revision(s,body.revision)
        report=validate_project(body.project)
        # Permit incomplete setup, but never persist malformed references/constraints.
        errors=[e for e in report['errors'] if e!='Add at least one teaching requirement before generating.' and 'school plan is incomplete' not in e and 'approved allocation is' not in e]
        if errors: raise HTTPException(422,errors)
        s['project']=body.project.model_dump()
        return store(s,'School inputs saved; existing timetable requires revalidation.')


@app.post('/api/validate')
def validate(body:RevisionRequest):
    s=state(); require_revision(s,body.revision)
    return validate_project(Project.model_validate(s['project']))


@app.post('/api/generate')
def generate(body:GenerateRequest):
    with mutex:
        s=state(); require_revision(s,body.revision)
        prior=[Placement.model_validate(p) for p in (s['draft'] or {}).get('placements',[])]
    result=solve(Project.model_validate(s['project']),prior,body.seconds,body.preserve)
    if result['status'] not in ('OPTIMAL','FEASIBLE'): return dict(ok=False,result=result)
    with mutex:
        latest=state(); require_revision(latest,body.revision)
        latest['draft']=result | dict(input_hash=fingerprint(latest['project']),generated_at=now())
        return dict(ok=True,state=store(latest,'Timetable generated and independently validated.'),result=result)


@app.post('/api/move')
def move(body:MoveRequest):
    with mutex:
        s=state(); require_revision(s,body.revision); draft=current_draft(s)
        placements=[Placement.model_validate(p) for p in draft['placements']]
        target=next((p for p in placements if p.occurrence==body.occurrence),None)
        if not target: raise HTTPException(404,'Session not found.')
        if target.locked: raise HTTPException(409,'Unlock this session before moving it.')
        target.day, target.period, target.rooms=body.day,body.period,body.rooms
        if body.adapt:
            target.locked=True
    if body.adapt:
        result=solve(Project.model_validate(s['project']),placements,body.seconds,True)
        if result['status'] not in ('OPTIMAL','FEASIBLE'):
            raise HTTPException(422,result['report']['errors'])
        old={p['occurrence']:p for p in draft['placements']}
        changes=[dict(occurrence=p['occurrence'],before=old.get(p['occurrence']),after=p)
                 for p in result['placements'] if old.get(p['occurrence']) and
                 any(p[k]!=old[p['occurrence']][k] for k in ('day','period','rooms'))]
        with mutex:
            latest=state(); require_revision(latest,body.revision)
            latest['draft']=result | dict(input_hash=fingerprint(latest['project']),generated_at=now(),changes=changes)
            return store(latest,f'Adapted school timetable around {body.occurrence}; {len(changes)} sessions changed. Your choice is locked.')
    with mutex:
        require_revision(state(),body.revision)
        report=check_schedule(Project.model_validate(s['project']),placements)
        if report['errors']: raise HTTPException(422,report['errors'])
        s['draft']=dict(placements=[p.model_dump() for p in placements],report=report,status='MANUAL_VALIDATED',input_hash=draft['input_hash'],generated_at=now())
        return store(s,f'Moved {body.occurrence}; all parallel parts moved together.')


@app.get('/api/workload')
def get_workload():
    s=state()
    current=s['draft'] and s['draft']['input_hash']==fingerprint(s['project'])
    placements=[Placement.model_validate(p) for p in s['draft']['placements']] if current else []
    return workload(Project.model_validate(s['project']),placements) | {'current':bool(current)}


@app.post('/api/import/teaching-preview')
def teaching_preview(body:TeachingImportRequest):
    s=state(); require_revision(s,body.revision)
    project=Project.model_validate(s['project'])
    reader=csv.DictReader(io.StringIO(body.csv_text.lstrip('\ufeff')))
    required={'id','class_id','subject_id','weekly','teacher_id','room_ids'}
    if not required.issubset(reader.fieldnames or []):
        raise HTTPException(422,'Required CSV columns: '+', '.join(sorted(required)))
    rows=[]; errors=[]; allocations={}
    for line,row in enumerate(reader,2):
        try:
            for teacher_key,hours_key in [('teacher_id','approved_weekly'),('teacher_2_id','teacher_2_approved_weekly')]:
                if row.get(hours_key,'').strip():
                    teacher_id=row.get(teacher_key,'').strip(); hours=int(row[hours_key])
                    teacher=next((t for t in project.teachers if t.id==teacher_id),None)
                    if not teacher or not 0<=hours<=120: raise ValueError('Invalid approved teacher allocation.')
                    if teacher_id in allocations and allocations[teacher_id]!=hours: raise ValueError('Conflicting approved allocations for '+teacher_id)
                    allocations[teacher_id]=hours
                    teacher.assigned_weekly=hours
            parts=[dict(teacher_id=row['teacher_id'].strip(),room_ids=row['room_ids'].strip().split('|'),group_id=row.get('group_id','').strip() or '*')]
            if row.get('teacher_2_id','').strip():
                parts.append(dict(teacher_id=row['teacher_2_id'].strip(),room_ids=row.get('room_2_ids','').strip().split('|'),group_id=row.get('group_2_id','').strip()))
            rows.append(Requirement(id=row['id'].strip(),name=row.get('name','').strip() or row['id'],
                class_id=row['class_id'].strip(),subject_id=row['subject_id'].strip(),weekly=int(row['weekly']),
                duration=int(row.get('duration') or 1),max_daily=int(row.get('max_daily') or 1),
                partition_id=row.get('partition_id','').strip() or None,parts=parts))
        except (ValueError,TypeError,AttributeError) as exc:
            errors.append(f'CSV line {line}: {exc}')
    if errors: raise HTTPException(422,errors)
    if len(rows)>1500: raise HTTPException(422,'At most 1,500 teaching requirements are supported.')
    project.requirements=rows
    return dict(project=project.model_dump(),report=validate_project(project),workload=workload(project))


@app.post('/api/lock')
def lock(body:LockRequest):
    with mutex:
        s=state(); require_revision(s,body.revision)
        # Unlocking stale sessions must remain possible after an input change.
        draft=s['draft']
        if not draft: raise HTTPException(404,'No draft exists.')
        if body.locked: current_draft(s)
        target=next((p for p in draft['placements'] if p['occurrence']==body.occurrence),None)
        if not target: raise HTTPException(404,'Session not found.')
        target['locked']=body.locked
        return store(s,('Locked ' if body.locked else 'Unlocked ')+body.occurrence)


@app.get('/api/versions')
def versions():
    with connection() as db: return [dict(r) for r in db.execute('SELECT id,name,created,kind FROM versions ORDER BY id DESC')]


def snapshot(body,kind):
    with mutex:
        s=state(); require_revision(s,body.revision); d=current_draft(s)
        report=check_schedule(Project.model_validate(s['project']),[Placement.model_validate(p) for p in d['placements']])
        if report['errors']: raise HTTPException(422,report['errors'])
        payload=dict(project=s['project'],draft=d,report=report)
        with connection() as db:
            vid=db.execute('INSERT INTO versions(name,created,kind,payload) VALUES(?,?,?,?)',(body.name,now(),kind,encode(payload))).lastrowid
        if kind=='published': s['published_id']=vid
        return store(s,f'{kind.capitalize()} immutable version {vid}: {body.name}')


@app.post('/api/versions')
def save_version(body:VersionRequest): return snapshot(body,'saved')


@app.post('/api/publish')
def publish(body:VersionRequest): return snapshot(body,'published')


@app.get('/api/versions/{vid}')
def version(vid:int):
    with connection() as db: row=db.execute('SELECT * FROM versions WHERE id=?',(vid,)).fetchone()
    if not row: raise HTTPException(404,'Version not found.')
    return dict(row) | {'payload':json.loads(row['payload'])}


@app.post('/api/versions/{vid}/restore')
def restore(vid:int,body:RevisionRequest):
    with mutex:
        s=state(); require_revision(s,body.revision)
        v=version(vid)['payload']
        Project.model_validate(v['project'])
        s['project'],s['draft']=v['project'],v['draft']
        return store(s,f'Restored version {vid} into the draft; published snapshot is unchanged.')


@app.get('/api/export/project')
def export_project():
    return Response(encode(state()['project']),media_type='application/json',headers={'Content-Disposition':'attachment; filename="maktab-project.json"'})


@app.get('/api/export/timetable')
def export_timetable(vid:int|None=None):
    if vid:
        data=version(vid)['payload']; project=Project.model_validate(data['project']); draft=data['draft']
    else:
        s=state(); draft=current_draft(s); project=Project.model_validate(s['project'])
    occ=occurrences(project)
    lookup={key:{x.id:x.name for x in getattr(project,key)} for key in ('classes','subjects','teachers','rooms')}
    def safe(value):
        text=str(value)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    out=io.StringIO(newline=''); writer=csv.writer(out)
    writer.writerow(['Class','Subject','Day','Period','Duration','Group','Teacher','Room','Locked'])
    for item in draft['placements']:
        r=occ[item['occurrence']]
        for i,part in enumerate(r.parts):
            writer.writerow([safe(v) for v in [lookup['classes'][r.class_id],lookup['subjects'][r.subject_id],['Dushanba','Seshanba','Chorshanba','Payshanba','Juma','Shanba'][item['day']],item['period'],r.duration,part.group_id,lookup['teachers'][part.teacher_id],lookup['rooms'][item['rooms'][i]],item['locked']]])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="maktab-timetable.csv"'})


@app.get('/api/stages')
def stages():
    file=BASE.parent/'PROJECT-STAGES.md'
    return {'text':file.read_text(encoding='utf-8') if file.exists() else 'Project tracker not found.'}


@app.get('/api/research')
def research():
    file=BASE.parent/'UZBEKISTAN-RESEARCH.md'
    return {'text':file.read_text(encoding='utf-8') if file.exists() else 'Research file not found.'}


app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')


@app.get('/')
def home(): return FileResponse(BASE/'static'/'index.html')


@app.get('/app')
def workspace(): return FileResponse(BASE/'static'/'index.html')


@app.get('/en')
def landing(): return FileResponse(BASE/'static'/'landing.html')
