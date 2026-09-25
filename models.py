"""Explicit, versioned input contract. IDs stay stable when names change."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Entity(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=160)


def minutes(value: str) -> int:
    h, m = map(int, value.split(':'))
    return h * 60 + m


class Period(Model):
    start: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    end: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')

    @model_validator(mode='after')
    def ordered(self):
        if minutes(self.end) <= minutes(self.start):
            raise ValueError('Period end must be after its start.')
        return self


class Unavailable(Period):
    day: int = Field(ge=0, le=5)


class Shift(Entity):
    periods: list[Period] = Field(min_length=1, max_length=10)

    @model_validator(mode='after')
    def ordered(self):
        for a, b in zip(self.periods, self.periods[1:]):
            if minutes(a.end) > minutes(b.start):
                raise ValueError('Shift periods must be in order and must not overlap.')
        return self


class Group(Entity):
    size: int = Field(ge=1, le=100)


class Partition(Entity):
    groups: list[Group] = Field(min_length=2, max_length=2)


class ClassGroup(Entity):
    grade: int = Field(ge=1, le=11)
    language: str = 'uz'
    size: int = Field(ge=1, le=100)
    shift_id: str
    days: list[int] = Field(default_factory=lambda: list(range(6)))
    max_daily: int = Field(default=6, ge=1, le=10)
    max_weekly: int = Field(default=36, ge=1, le=60)
    partitions: list[Partition] = Field(default_factory=list)

    @field_validator('days')
    @classmethod
    def valid_days(cls, value):
        if not value or len(set(value)) != len(value) or any(d not in range(6) for d in value):
            raise ValueError('Choose distinct days from 0 (Monday) to 5 (Saturday).')
        return value


class Teacher(Entity):
    subjects: list[str]
    assigned_weekly: int | None = Field(default=None, ge=0, le=120)
    max_daily: int = Field(default=6, ge=1, le=20)
    max_weekly: int = Field(default=30, ge=1, le=120)
    unavailable: list[Unavailable] = Field(default_factory=list)


class Room(Entity):
    capacity: int = Field(default=30, ge=1, le=500)
    kind: str = 'general'
    unavailable: list[Unavailable] = Field(default_factory=list)


class Subject(Entity):
    color: str = Field(default='#537bdf', pattern=r'^#[0-9a-fA-F]{6}$')
    category: Literal['general', 'foreign', 'informatics', 'pe', 'technology', 'russian', 'uzbek', 'military', 'vocational'] = 'general'


class Part(Model):
    group_id: str = '*'
    teacher_id: str
    room_ids: list[str] = Field(min_length=1)


class Requirement(Entity):
    class_id: str
    subject_id: str
    weekly: int = Field(ge=1, le=40)
    duration: int = Field(default=1, ge=1, le=2)
    max_daily: int = Field(default=1, ge=1, le=10)
    partition_id: str | None = None
    parts: list[Part] = Field(min_length=1, max_length=2)


class Rule(Entity):
    enabled: bool = True
    kind: Literal['forbid', 'prefer', 'avoid', 'max_daily'] = 'forbid'
    strength: Literal['required', 'preferred'] = 'required'
    class_id: str | None = None
    subject_id: str | None = None
    teacher_id: str | None = None
    group_id: str | None = None
    days: list[int] = Field(default_factory=list)
    periods: list[int] = Field(default_factory=list)
    limit: int = Field(default=1, ge=0, le=60)
    weight: int = Field(default=10, ge=1, le=1000)
    note: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def meaningful(self):
        if len(set(self.days)) != len(self.days) or any(d not in range(6) for d in self.days):
            raise ValueError('Rule days must be distinct values 0–5.')
        if len(set(self.periods)) != len(self.periods) or any(p not in range(1, 11) for p in self.periods):
            raise ValueError('Rule periods must be distinct values 1–10.')
        if self.kind in ('prefer', 'avoid') and self.strength != 'preferred':
            raise ValueError('Prefer/avoid rules must have preferred strength.')
        if self.kind == 'forbid' and self.strength != 'required':
            raise ValueError('Forbid rules must have required strength; use avoid for a preference.')
        if self.kind != 'max_daily' and not (self.days or self.periods):
            raise ValueError('Select at least one day or period.')
        if self.kind == 'max_daily' and self.periods:
            raise ValueError('Daily-limit rules use days, not selected periods.')
        return self


class School(Model):
    name: str = Field(default='Maktab Jadval', min_length=1, max_length=160)
    year: str = '2026–2027'
    curriculum_reference: str = 'Demonstration hours — replace with approved school curriculum'
    policy_note: str = 'Bell times and load limits need school review.'
    shifts: list[Shift] = Field(min_length=1, max_length=2)


class Project(Model):
    schema_version: Literal[1] = 1
    school: School
    classes: list[ClassGroup] = Field(default_factory=list, max_length=100)
    teachers: list[Teacher] = Field(default_factory=list, max_length=300)
    subjects: list[Subject] = Field(default_factory=list, max_length=100)
    rooms: list[Room] = Field(default_factory=list, max_length=200)
    requirements: list[Requirement] = Field(default_factory=list, max_length=1500)
    rules: list[Rule] = Field(default_factory=list, max_length=300)


class Placement(Model):
    occurrence: str
    day: int = Field(ge=0, le=5)
    period: int = Field(ge=1, le=10)
    rooms: list[str]
    locked: bool = False


class GenerateRequest(Model):
    revision: int
    seconds: int = Field(default=60, ge=1, le=600)
    preserve: bool = True


class MoveRequest(Model):
    revision: int
    occurrence: str
    day: int = Field(ge=0, le=5)
    period: int = Field(ge=1, le=10)
    rooms: list[str]
    adapt: bool = True
    seconds: int = Field(default=60, ge=1, le=600)


class RevisionRequest(Model):
    revision: int


class LockRequest(RevisionRequest):
    occurrence: str
    locked: bool


class SaveRequest(RevisionRequest):
    project: Project


class VersionRequest(RevisionRequest):
    name: str = Field(min_length=1, max_length=160)


class TeachingImportRequest(RevisionRequest):
    csv_text: str = Field(max_length=2_000_000)
