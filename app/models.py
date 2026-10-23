from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Section = Literal['summary', 'experience', 'projects', 'education', 'certifications', 'achievements']
SECTION_ORDER = ['summary', 'education', 'experience', 'projects', 'certifications', 'achievements']


class Fact(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    section: Section
    text: str = Field(min_length=1, max_length=6000)


class Profile(BaseModel):
    name: str = Field(default='', max_length=200)
    email: str = Field(default='', max_length=300)
    phone: str = Field(default='', max_length=100)
    location: str = Field(default='', max_length=300)
    links: list[str] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=150)
    facts: list[Fact] = Field(default_factory=list, max_length=200)

    @model_validator(mode='after')
    def unique_ids(self):
        if len({f.id for f in self.facts}) != len(self.facts):
            raise ValueError('Each fact must have a unique identifier.')
        if not self.facts and not self.skills:
            raise ValueError('No resume facts or skills were found. Try a clearer PDF.')
        return self


class ProfileUpdate(BaseModel):
    profile: Profile
    preferred_role: str = Field(min_length=2, max_length=150)


class Job(BaseModel):
    id: str
    source: Literal['greenhouse', 'lever']
    board: str
    title: str
    company: str
    location: str
    job_type: str = ''
    description: str
    url: str
    matched_skills: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)

    @field_validator('url')
    @classmethod
    def safe_url(cls, value):
        from urllib.parse import urlparse
        parsed = urlparse(value)
        if parsed.scheme != 'https' or not parsed.hostname:
            raise ValueError('Application links must use HTTPS.')
        return value


class SkillRequirement(BaseModel):
    skill: str = Field(min_length=1, max_length=100)
    evidence: str = Field(min_length=1, max_length=1500)


class Analysis(BaseModel):
    required: list[SkillRequirement] = Field(default_factory=list)
    preferred: list[SkillRequirement] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    note: str = ''


class TailoredFact(BaseModel):
    source_id: str
    text: str
    reason: str


class Tailoring(BaseModel):
    facts: list[TailoredFact]
    section_order: list[Section]
    rationale: str


class VerifiedRewrite(BaseModel):
    source_id: str
    supported: bool


class Verification(BaseModel):
    results: list[VerifiedRewrite]


class DiscoverRequest(BaseModel):
    role: str = Field(min_length=2, max_length=150)
    location: str = Field(default='', max_length=150)
    entry_only: bool = False


class ApplicationAnswers(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=300)
    work_authorization: str = Field(min_length=2, max_length=200)
    availability: str = Field(min_length=2, max_length=300)
    additional_notes: str = Field(default='', max_length=3000)

    @field_validator('email')
    @classmethod
    def email_shape(cls, value):
        import re
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value
