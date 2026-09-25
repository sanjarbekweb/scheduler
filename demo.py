from models import Project


def demo_project():
    subjects = [
        ('algebra', 'Algebra', '#4668c9', 'general'),
        ('geometry', 'Geometriya', '#577cda', 'general'),
        ('english', 'Ingliz tili', '#9b62bd', 'foreign'),
        ('russian', 'Rus tili', '#b86f93', 'russian'),
        ('it', 'Informatika', '#2a928d', 'informatics'),
        ('physics', 'Fizika', '#bb8b30', 'general'),
        ('chemistry', 'Kimyo', '#bd7044', 'general'),
        ('literature', 'Adabiyot', '#688659', 'general'),
        ('history', 'Tarix', '#91744f', 'general'),
        ('pe', 'Jismoniy tarbiya', '#529889', 'pe'),
        ('future', 'Kelajak soati', '#777da4', 'general'),
    ]
    teachers = []
    for i, (sid, name, _, _) in enumerate(subjects):
        for n in range(2 if sid in ('english', 'russian', 'it', 'pe') else 1):
            teachers.append(dict(id=f't_{sid}_{n}', name=f'{name} — ustoz {n+1}', subjects=[sid], max_daily=6, max_weekly=30, unavailable=[]))
    rooms = [dict(id=f'r{i}', name=f'{i}-xona', capacity=32, kind='general') for i in range(201, 205)]
    rooms += [dict(id=f'lab{i}', name=f'IT xona {i}', capacity=18, kind='computer') for i in (1, 2)]
    rooms += [dict(id=f'gym{i}', name=f'Sport maydoni {i}', capacity=20, kind='sport') for i in (1, 2)]
    classes, requirements = [], []
    for cid in ('10A', '10B'):
        partitions = []
        for sid in ('english', 'russian', 'it', 'pe'):
            partitions.append(dict(id=f'{cid}_{sid}', name=f'{sid} guruhlari', groups=[dict(id=f'{cid}_{sid}_{n}', name=f'{n}-guruh', size=15) for n in (1, 2)]))
        classes.append(dict(id=cid, name=cid, grade=10, language='uz', size=30, shift_id='morning', max_daily=6, max_weekly=36, partitions=partitions))
        for sid, name, _, _ in subjects:
            split = sid in ('english', 'russian', 'it', 'pe')
            room_ids = ['lab1', 'lab2'] if sid == 'it' else ['gym1', 'gym2'] if sid == 'pe' else [f'r{i}' for i in range(201,205)]
            requirements.append(dict(id=f'{cid}_{sid}', name=f'{cid} · {name}', class_id=cid, subject_id=sid, weekly=3 if sid in ('algebra','english') else 1 if sid=='future' else 2, max_daily=1, partition_id=f'{cid}_{sid}' if split else None, parts=[dict(group_id=f'{cid}_{sid}_{n+1}' if split else '*', teacher_id=f't_{sid}_{n}', room_ids=room_ids) for n in range(2 if split else 1)]))
    return Project.model_validate(dict(school=dict(name='Maktab · namuna', shifts=[dict(id='morning', name='1-smena', periods=[dict(start=s,end=e) for s,e in [('08:00','08:45'),('08:55','09:40'),('09:50','10:35'),('10:55','11:40'),('11:50','12:35'),('12:45','13:30')]])]), subjects=[dict(id=i,name=n,color=c,category=k) for i,n,c,k in subjects], teachers=teachers, rooms=rooms, classes=classes, requirements=requirements, rules=[dict(id='no_monday_it',name='Informatika: dushanba emas',kind='forbid',subject_id='it',days=[0]),dict(id='morning_algebra',name='Algebra: 2–4-dars afzal',kind='prefer',strength='preferred',subject_id='algebra',periods=[2,3,4],weight=10)]))
