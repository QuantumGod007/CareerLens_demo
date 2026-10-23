from app.models import Fact, Job, Tailoring, TailoredFact, OmittedFact, Verification, VerifiedRewrite
from app.config import Settings
from app.services.gemini import Gemini
from app.services.content import clean_profile, split_entry
from app.services.pdf import create_pdf
from app.services.scoring import readability
from app.main import create_app
from fastapi.testclient import TestClient
from test_workflow import FakeAI, sample_pdf


def confirm(client):
    c=client.get('/api/state').json()['candidate']
    result=client.put('/api/profile',json={'profile':c['profile'],'preferred_role':c['preferred_role'],
        'confirm':True,'expected_version':c['profile_version']})
    assert result.status_code==200,result.text
    return result.json()['profile_version']


def test_duplicate_project_heading_bullets_and_skills(profile,tmp_path):
    a='LibraryLens (2026): Built a Python and SQL catalog with 3 search filters.'
    b='LibraryLens (2026): Added CSV exports and documented the Python API.'
    p=profile.model_copy(update={'skills':['Python','SQL','python'], 'facts':[
        Fact(id='a',section='projects',text=a),Fact(id='b',section='projects',text=b),
        Fact(id='c',section='projects',text=a),
        Fact(id='d',section='projects',text='Other project (2026): Built a Python and SQL catalog with 3 search filters.')]})
    cleaned=clean_profile(p)
    assert cleaned.skills==['Python','SQL'] and len(cleaned.facts)==2
    text,meta=create_pdf(p,tmp_path/'deduplicated.pdf')
    assert text.count('LibraryLens (2026)')==1
    assert text.count('Built a Python and SQL catalog with 3 search filters.')==2
    assert text.count('Added CSV exports')==1
    assert all(c['status']=='pass' for c in readability(text,cleaned,meta))
    assert len(p.facts)==4 # renderer doesn't mutate its source


def test_project_selection_requires_jd_and_verified_reason(profile,tmp_path,monkeypatch):
    p=profile.model_copy(update={'facts':profile.facts+[
        Fact(id='extra',section='projects',text='PaintBoard\nBuilt a JavaScript drawing canvas.')]})
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    monkeypatch.setattr(ai,'ask',lambda *a,**k:Verification(results=[VerifiedRewrite(source_id='extra',supported=True),VerifiedRewrite(source_id='f1',supported=True)]))
    proposal=Tailoring(facts=[TailoredFact(source_id='f2',text=p.facts[1].text,reason='Relevant Python project')],
        omitted=[OmittedFact(source_id='extra',reason='Drawing UI is less relevant than the retained Python project.'),
                 OmittedFact(source_id='f1',reason='Do not omit this education qualification.')],section_order=['projects'],rationale='Select')
    job=Job(id='test',source='lever',board='test',title='Python Developer',company='Test',location='Remote',description='Python required.',url='https://example.com/test')
    tailored,_,changes,_=ai.validate_tailoring(p,proposal,job)
    assert {f.id for f in tailored.facts}=={'f1','f2','f3'}
    assert any(c['kind']=='omission' and c['source_id']=='extra' for c in changes)
    without_jd,*_=ai.validate_tailoring(p,proposal)
    assert len(without_jd.facts)==4
    monkeypatch.setattr(ai,'ask',lambda *a,**k:Verification(results=[VerifiedRewrite(source_id='extra',supported=False)]))
    rejected,*_=ai.validate_tailoring(p,proposal,job)
    assert len(rejected.facts)==4


def test_confirmation_stale_profile_job_and_busy_guards(profile,tmp_path):
    app=create_app(Settings(_env_file=None,data_dir=tmp_path),ai=FakeAI(profile))
    job=Job(id='test',source='lever',board='test',title='Developer',company='Test',location='Remote',description='Python required.',url='https://example.com/test')
    app.state.store.save_jobs([job])
    with TestClient(app) as client:
        client.post('/api/resume',files={'file':('resume.pdf',sample_pdf(),'application/pdf')},data={'preferred_role':'Developer'})
        assert client.post('/api/jobs/test/analyse').status_code==409
        assert client.post('/api/jobs/discover',json={'role':'Developer'}).status_code==409
        version=confirm(client)
        assert client.post('/api/jobs/test/analyse',params={'expected_version':'old'}).status_code==409
        assert client.post('/api/jobs/test/analyse',params={'expected_job':'old'}).status_code==409
        r=client.post('/api/jobs/test/analyse',params={'expected_version':version}).json()
        assert r['profile_version']==version and r['job']==job.model_dump()
        assert r['enhancement_status']=='unchanged'
        old=client.get('/api/state').json()['candidate']
        client.put('/api/profile',json={'profile':profile.model_dump(),'preferred_role':'Developer','expected_version':version})
        assert client.put('/api/profile',json={'profile':old['profile'],'preferred_role':'Developer','expected_version':version,'confirm':True}).status_code==409
        assert client.get('/api/history/'+r['id']).json()['profile_version']==version
        client.portal.call(app.state.ai_lock.acquire)
        try:
            assert client.post('/api/jobs/test/analyse').status_code==409
            assert client.put('/api/profile',json={'profile':profile.model_dump(),'preferred_role':'Developer'}).status_code==409
        finally:client.portal.call(app.state.ai_lock.release)


def test_whitespace_only_output_preserves_bullets(profile,tmp_path,monkeypatch):
    source='LibraryLens (2026)\nBuilt a Python catalog.\nAdded SQL search filters.'
    p=profile.model_copy(update={'facts':[Fact(id='p',section='projects',text=source)]})
    ai=Gemini(Settings(_env_file=None,data_dir=tmp_path))
    monkeypatch.setattr(ai,'ask',lambda *a,**k:Verification(results=[VerifiedRewrite(source_id='p',supported=True)]))
    proposal=Tailoring(facts=[TailoredFact(source_id='p',text=source.replace('\n',' '),reason='No content change')],section_order=['projects'],rationale='Relevant')
    result,_,changes,_=ai.validate_tailoring(p,proposal)
    assert result.facts[0].text==source
    assert not any(c['kind']=='wording' for c in changes)
    proposal.facts[0].text=source.replace('\n',' ').replace('Built','Developed')
    result,*_=ai.validate_tailoring(p,proposal)
    assert result.facts[0].text==source


def test_sentence_duplicates_do_not_remove_distinct_information(profile):
    p=profile.model_copy(update={'facts':[Fact(id='x',section='projects',text='Example\nBuilt a Python service. Built a Python service. Added SQL exports.')]})
    result=clean_profile(p)
    assert result.facts[0].text=='Example\nBuilt a Python service. Added SQL exports.'
