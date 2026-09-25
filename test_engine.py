import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))

from demo import demo_project
from engine import solve, check_schedule, validate_project
from models import Placement, Project, Rule


def test_demo_input_is_valid_but_calls_out_policy_review():
    p=demo_project(); report=validate_project(p)
    assert report['errors']==[]
    assert any('eligibility' in w.lower() or 'review' in w.lower() for w in report['warnings'])


def test_demo_solves_and_split_occurrences_have_two_rooms_and_teachers():
    p=demo_project(); result=solve(p,seconds=20)
    assert result['status'] in ('OPTIMAL','FEASIBLE'), result
    assert result['report']['errors']==[]
    for item in result['placements']:
        req=next(r for r in p.requirements if item['occurrence'].startswith(r.id+':'))
        assert len(item['rooms'])==len(req.parts)
        if len(req.parts)==2:
            assert len(set(item['rooms']))==2


def test_monday_forbidden_rule_is_never_violated():
    p=demo_project(); result=solve(p,seconds=20)
    assert result['report']['errors']==[]
    for item in result['placements']:
        req=next(r for r in p.requirements if item['occurrence'].startswith(r.id+':'))
        if req.subject_id=='it': assert item['day']!=0


def test_checker_rejects_teacher_overlap_and_bad_room():
    p=demo_project(); result=solve(p,seconds=20)
    items=[Placement.model_validate(x) for x in result['placements']]
    items[1].day,items[1].period=items[0].day,items[0].period
    items[1].rooms=['no-room']*len(items[1].rooms)
    report=check_schedule(p,items)
    assert report['errors']
    assert any('overlaps' in e or 'room' in e.lower() for e in report['errors'])


def test_locked_placement_is_preserved():
    p=demo_project(); first=solve(p,seconds=20)
    items=[Placement.model_validate(x) for x in first['placements']]
    items[0].locked=True
    second=solve(p,items,seconds=20,preserve=True)
    assert second['report']['errors']==[]
    a=next(x for x in first['placements'] if x['occurrence']==items[0].occurrence)
    b=next(x for x in second['placements'] if x['occurrence']==items[0].occurrence)
    assert (a['day'],a['period'],a['rooms'])==(b['day'],b['period'],b['rooms'])


def test_infeasible_rule_is_reported_without_relaxation():
    p=demo_project()
    # Forbid every day and period for one subject; preserve the rest of the model.
    p.rules.append(Rule(id='block_all',name='Block all Algebra',kind='forbid',subject_id='algebra',days=list(range(6)),periods=list(range(1,7))))
    result=solve(p,seconds=5)
    assert result['status']=='INFEASIBLE'
    assert 'no valid placement' in result['report']['errors'][0].lower()


def test_stale_manual_result_is_not_hidden_by_checker():
    p=demo_project(); result=solve(p,seconds=20)
    items=[Placement.model_validate(x) for x in result['placements']]
    # Double-occupy one class period with another occurrence from that class.
    first_req=next(r for r in p.requirements if items[0].occurrence.startswith(r.id+':'))
    same_class=next(i for i in items[1:] if next(r for r in p.requirements if i.occurrence.startswith(r.id+':')).class_id==first_req.class_id)
    same_class.day,same_class.period=items[0].day,items[0].period
    report=check_schedule(p,items)
    assert any('class' in e.lower() and 'overlaps' in e.lower() for e in report['errors'])
