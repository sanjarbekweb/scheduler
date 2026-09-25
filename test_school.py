"""Whole-school accounting and transactional repair regressions."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fastapi.testclient import TestClient
from models import Project, Placement
from engine import solve, workload, validate_project
import server


def school(size=3):
    return Project.model_validate(dict(school=dict(shifts=[dict(id='am',name='Morning',periods=[
        dict(start='08:00',end='08:45'),dict(start='08:55',end='09:40'),dict(start='09:50',end='10:35')])]),
        classes=[dict(id=f'c{i}',name=f'Class {i}',grade=8,size=25,shift_id='am') for i in range(size)],
        subjects=[dict(id='math',name='Math')],
        teachers=[dict(id=f't{i}',name=f'Teacher {i}',subjects=['math'],assigned_weekly=3) for i in range(size)],
        rooms=[dict(id=f'r{i}',name=f'Room {i}',capacity=30) for i in range(size)],
        requirements=[dict(id=f'q{i}',name=f'Math {i}',class_id=f'c{i}',subject_id='math',weekly=3,
            parts=[dict(teacher_id=f't{i}',room_ids=[f'r{i}'])]) for i in range(size)]))


def test_approved_allocation_and_missing_class_rejected():
    p=school();p.teachers[0].assigned_weekly=4
    assert any('approved allocation is 4' in e for e in validate_project(p)['errors'])
    p.requirements.pop()
    assert any('school plan is incomplete' in e for e in validate_project(p)['errors'])


def test_twenty_classes_all_periods_accounted():
    p=school(20)
    p.teachers=p.teachers[:5]
    for t in p.teachers: t.assigned_weekly=12
    for i,r in enumerate(p.requirements):
        r.parts[0].teacher_id=f't{i%5}'
        r.parts[0].room_ids=[f'r{i%5}']
    result=solve(p,seconds=20)
    assert result['status'] in ('OPTIMAL','FEASIBLE'),result
    w=workload(p,[Placement.model_validate(x) for x in result['placements']])
    assert len(w['classes'])==20 and len(result['placements'])==60
    assert all(r['required']==r['scheduled']==3 and r['remaining']==0 for r in w['classes'])
    assert all(r['required']==r['scheduled']==12 and r['remaining']==0 for r in w['teachers'])


def test_repair_moves_other_session_and_failed_choice_is_atomic(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'school.db');server.initialize()
    p=school(2)
    # Both classes share a teacher and room, so moving one forces another to move.
    p.teachers=p.teachers[:1];p.teachers[0].assigned_weekly=6
    p.requirements[1].parts[0].teacher_id='t0';p.requirements[1].parts[0].room_ids=['r0']
    first=solve(p,seconds=10)
    assert first['status'] in ('OPTIMAL','FEASIBLE')
    s=server.state();s['project']=p.model_dump();s['draft']=first|dict(input_hash=server.fingerprint(s['project']),generated_at=server.now());server.store(s,'Test school')
    a=first['placements'][0]
    b=next(x for x in first['placements'] if x['occurrence'].split(':')[0]!=a['occurrence'].split(':')[0])
    client=TestClient(server.app)
    payload=dict(revision=s['revision'],occurrence=a['occurrence'],day=b['day'],period=b['period'],rooms=['r0'],seconds=10)
    result=client.post('/api/move',json=payload)
    assert result.status_code==200,result.text
    updated=result.json(); moved=next(x for x in updated['draft']['placements'] if x['occurrence']==a['occurrence'])
    assert moved['locked'] and (moved['day'],moved['period'])==(b['day'],b['period'])
    assert len(updated['draft']['changes'])>=2
    assert updated['draft']['report']['errors']==[]
    # Force another session into the now locked slot: infeasible, no revision/write.
    before=server.state()
    result=client.post('/api/move',json=payload|dict(revision=before['revision'],occurrence=b['occurrence']))
    assert result.status_code==422
    assert server.state()==before


def test_csv_preview_does_not_write_and_reports_allocation(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',tmp_path/'school.db');server.initialize()
    s=server.state();s['project']=school(1).model_dump();server.store(s,'Test school')
    before=server.state()
    result=TestClient(server.app).post('/api/import/teaching-preview',json=dict(revision=before['revision'],csv_text='id,class_id,subject_id,weekly,teacher_id,room_ids\nq0,c0,math,2,t0,r0'))
    assert result.status_code==200
    assert any('approved allocation is 3' in e for e in result.json()['report']['errors'])
    assert server.state()==before
