import pytest
from app.models import SkillRequirement
from app.services.scoring import contains_skill, coverage, profile_text


@pytest.mark.parametrize('text,skill,expected',[
    ('JavaScript and C++', 'Java', False), ('JavaScript and C++', 'C', False),
    ('C++ and C#', 'C++', True), ('C# and C++', 'C#', True),
    ('Java and Python', 'Java', True), ('Worked with React.js','React',True),
    ('Built on AWS', 'Amazon Web Services', True), ('PostgreSQL','SQL',False),
    ('HTML5', 'ML', False), ('Machine learning models', 'ML', True),
])
def test_skill_boundaries(text,skill,expected):
    assert contains_skill(text,skill) is expected


def test_real_formula_and_dedup():
    req=[SkillRequirement(skill=s,evidence=s+' required') for s in ['Python','SQL','React','python']]
    result=coverage('Python, SQL',req)
    assert {k:v for k,v in result.items() if k!='evidence'}=={'percentage':66.7,'matched_count':2,'total':3,'matched':['Python','SQL'],'missing':['React']}
    assert coverage('Python SQL React',[])['percentage'] is None


def test_no_artificial_improvement(profile):
    req=[SkillRequirement(skill=s,evidence=s) for s in ['Python','Java','SQL']]
    source=profile_text(profile)
    reordered=profile_text(profile,['projects','experience','education'])
    assert coverage(source,req)==coverage(reordered,req)


def test_broad_programming_requirement_has_explicit_language_evidence():
    req=[SkillRequirement(skill=s,evidence=s) for s in ['programming','written communication skills','AI tools']]
    result=coverage('Skills\nPython, JavaScript\nBuilt a React dashboard.',req)
    assert result['percentage']==33.3
    assert result['matched']==['programming']
    assert result['evidence'][0]['method']=='explicit evidence: Python'
    assert 'Python' in result['evidence'][0]['evidence']


def test_category_matching_does_not_invent_soft_skills_or_ai_tools():
    req=[SkillRequirement(skill=s,evidence=s) for s in ['programming','written communication skills','AI tools']]
    result=coverage('Student projects using React, PyTorch and XGBoost.',req)
    assert result['percentage']==0
    assert result['matched']==[]
    assert coverage('Skills: ChatGPT',req)['matched']==['AI tools']
    assert coverage('Python@candidate.example\nhttps://example.com/Python',req)['matched']==[]


def test_written_communication_alias():
    assert coverage('Skills: Technical writing',[{'skill':'written communication skills'}])['percentage']==100
