from app.config import Settings
from app.models import Profile, Tailoring, TailoredFact, Verification, VerifiedRewrite
from app.services.gemini import Gemini, AIError, wording_is_grounded, serving_schema


def proposal():
    return Tailoring(facts=[
        TailoredFact(source_id='f2',text='Built a Python and SQL library catalog with 30 search filters.',reason='Add impact'),
        TailoredFact(source_id='invented',text='Led a team of 20 at Google.',reason='Invented'),
        TailoredFact(source_id='f3',text='Developed a JavaScript dashboard for a student club.',reason='Relevant'),
        TailoredFact(source_id='f3',text='Duplicate fact',reason='Duplicate'),
    ],section_order=['projects','experience','education'],rationale='Reorder')


def test_unknown_facts_metrics_duplicates_and_omissions(profile,monkeypatch,tmp_path):
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    # Even a verifier that mistakenly approves the rewrite cannot add a metric.
    monkeypatch.setattr(ai,'ask',lambda *args,**kw: Verification(results=[VerifiedRewrite(source_id='f2',supported=True)]))
    tailored,order,changes,verified=ai.validate_tailoring(profile,proposal())
    assert {f.id for f in tailored.facts}=={f.id for f in profile.facts}
    assert len(tailored.facts)==len(profile.facts)
    assert next(f.text for f in tailored.facts if f.id=='f2')==profile.facts[1].text
    assert tailored.email==profile.email and tailored.skills==profile.skills
    assert '30 search' not in str(tailored)


def test_verifier_outage_falls_back(profile,monkeypatch,tmp_path):
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    def fail(*args,**kwargs):raise AIError('Test outage')
    monkeypatch.setattr(ai,'ask',fail)
    tailored,_,changes,verified=ai.validate_tailoring(profile,proposal())
    assert verified is False
    assert {f.id:f.text for f in tailored.facts}=={f.id:f.text for f in profile.facts}


def test_new_tools_and_descriptive_claims_are_blocked():
    assert wording_is_grounded('Built a Python application.','Developed an application using Python.')
    assert not wording_is_grounded('Built a Python application.','Built a scalable Python application with Docker.')
    assert not wording_is_grounded('Built a Python application.','Built a Python application at Google.')
    assert not wording_is_grounded('Built a Python application as a fictional test.','Built a Python application.')


def test_serving_schema_keeps_types_but_not_expensive_bounds():
    schema=serving_schema(Profile.model_json_schema())
    assert schema['properties']['skills']['items']['type']=='string'
    assert 'maxItems' not in schema['properties']['skills']
    assert 'maxLength' not in schema['properties']['name']


def test_verified_paraphrase_can_change_sentence_structure(profile,monkeypatch,tmp_path):
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    monkeypatch.setattr(ai,'ask',lambda *a,**k: Verification(results=[VerifiedRewrite(source_id='f2',supported=True)]))
    rewritten='Developed a library catalog using Python and SQL, including 3 search filters.'
    proposal=Tailoring(facts=[TailoredFact(source_id='f2',text=rewritten,reason='Lead with the relevant project and retain its scope.')],
                       section_order=['projects','education','experience'],rationale='Relevant project first')
    tailored,_,changes,_=ai.validate_tailoring(profile,proposal)
    assert next(f.text for f in tailored.facts if f.id=='f2')==rewritten
    assert len(tailored.facts)==len(profile.facts)
    assert any(c['kind']=='wording' for c in changes)


def test_unverified_paraphrase_cannot_bypass_fact_check(profile,monkeypatch,tmp_path):
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    monkeypatch.setattr(ai,'ask',lambda *a,**k: Verification(results=[VerifiedRewrite(source_id='f2',supported=False)]))
    proposal=Tailoring(facts=[TailoredFact(source_id='f2',text='Developed a library catalog using Python and SQL, including 3 search filters.',reason='Rewrite')],
                       section_order=['projects'],rationale='Reorder')
    tailored,_,changes,_=ai.validate_tailoring(profile,proposal)
    assert next(f.text for f in tailored.facts if f.id=='f2')==profile.facts[1].text
