from io import BytesIO
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from pypdf import PdfReader

from app.config import Settings
from app.main import create_app
from app.models import Analysis, SkillRequirement, Job
from app.services.pdf import create_pdf, read_pdf, PDFError
from app.services.scoring import profile_text


def sample_pdf():
    out=BytesIO();c=canvas.Canvas(out)
    c.drawString(60,780,'DEMO TEST RESUME - Demo Candidate')
    c.drawString(60,760,'demo@example.com | +91 9000000000')
    c.drawString(60,740,'Skills: Python, JavaScript, SQL')
    c.drawString(60,720,'Education: Demo University')
    c.save();return out.getvalue()


class FakeAI:
    """An explicit test double; never used by the application."""
    def __init__(self,profile):self.profile=profile;self.extractions=0;self.analyses=0
    def extract(self,data):self.extractions+=1;return self.profile
    def analyse(self,profile,job):
        self.analyses+=1
        return Analysis(required=[SkillRequirement(skill='Python',evidence='Python required'),SkillRequirement(skill='Java',evidence='Java required')])
    def tailor(self,profile,job,analysis):return profile,['education','projects','experience'],[],True


def test_complete_local_workflow_and_persistence(profile,tmp_path,monkeypatch):
    fake=FakeAI(profile)
    settings=Settings(_env_file=None,data_dir=tmp_path,gemini_api_key='',greenhouse_boards='',lever_boards='')
    app=create_app(settings,ai=fake)
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        assert client.get('/api/state').json()['candidate'] is None
        assert client.post('/api/resume',files={'file':('resume.txt',b'not PDF')},data={'preferred_role':'Intern'}).status_code==422
        response=client.post('/api/resume',files={'file':('resume.pdf',sample_pdf(),'application/pdf')},data={'preferred_role':'Software Intern'})
        assert response.status_code==200,response.text
        assert client.get('/api/resume/original').headers['content-type']=='application/pdf'
        # Persist an explicit fixture listing for route tests, never a live-job claim.
        job=Job(id='lever:demo:test',source='lever',board='demo',company='Demo Test Company',title='Software Intern',location='Remote',description='Python required. Java required.',url='https://example.com/test-job')
        app.state.store.save_jobs([job])
        saved=[]
        for _ in range(2):
            response=client.post('/api/jobs/lever:demo:test/analyse')
            assert response.status_code==200,response.text
            record=response.json();saved.append(record['id'])
            assert record['original_score']['percentage']==50
            assert record['tailored_score']['percentage']==50
            assert 'original_path' not in record
            pdf=client.get(f'/api/history/{record["id"]}/pdf')
            text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
            assert profile.email in text
            assert all(f.text in text.replace('\n',' ') for f in profile.facts)
        assert len(set(saved))==2 and fake.extractions==1
        assert len(client.get('/api/history').json())==2
        assert client.post(f'/api/test-receiver/{saved[0]}',json={'name':'Demo','email':'bad','work_authorization':'Test','availability':'Now'}).status_code==422
        receipt=client.post(f'/api/test-receiver/{saved[0]}',json={'name':'Demo','email':'demo@example.com','work_authorization':'Test only','availability':'Now'}).json()
        assert receipt['status']=='simulated' and 'No employer' in receipt['message']
        assert len(client.get(f'/api/history/{saved[0]}').json()['simulations'])==1
        assert len(client.get(f'/api/history/{saved[1]}').json()['simulations'])==0
        # Editing does not mutate the history snapshot.
        changed=profile.model_copy(update={'name':'Edited Candidate'})
        assert client.put('/api/profile',json={'profile':changed.model_dump(),'preferred_role':'Developer'}).status_code==200
        assert client.get(f'/api/history/{saved[0]}').json()['original_profile']['name']=='Demo Candidate'
        assert client.post('/api/test-receiver/missing',json={'name':'D','email':'d@example.com','work_authorization':'yes','availability':'now'},headers={'Origin':'https://evil.example'}).status_code==403
    # A fresh app instance reads the same SQLite history and downloadable files.
    with TestClient(create_app(settings,ai=fake)) as reopened:
        assert len(reopened.get('/api/history').json())==2
        assert reopened.get(f'/api/history/{saved[0]}/pdf').status_code==200
        assert reopened.get('/api/history/../../.env/pdf').status_code==404


def test_pdf_validation_and_long_content(profile,tmp_path):
    path=tmp_path/'long.pdf'
    from app.models import Fact
    facts=[Fact(id=f'f{i}',section='projects',text=f'Project {i}: Built a Python and SQL application. '+('Documented the design and implementation. '*20)) for i in range(30)]
    long=profile.model_copy(update={'facts':facts})
    text,meta=create_pdf(long,path)
    assert meta['pages']>1
    assert 'Project 29:' in text and 'Project 0:' in text
    assert profile.email in text
    assert all(c['status']=='pass' for c in __import__('app.services.scoring',fromlist=['readability']).readability(text,long,meta))


def test_old_score_is_recalculated_without_changing_the_saved_record(profile,tmp_path):
    from app.services.store import now
    settings=Settings(_env_file=None,data_dir=tmp_path,gemini_api_key='')
    app=create_app(settings,ai=FakeAI(profile))
    old_score={'percentage':0,'matched_count':0,'total':3,'matched':[],
               'missing':['programming','written communication skills','AI tools']}
    old={'id':'legacy','job':{'id':'test:job'},'created_at':now(),
         'original_text':'Skills: Python, JavaScript', 'tailored_text':'Built a Python application.',
         'analysis':{'required':[{'skill':skill,'evidence':skill} for skill in old_score['missing']]},
         'original_score':old_score,'tailored_score':old_score}
    app.state.store.save_assessment(old)
    before=app.state.store.assessment('legacy')
    with TestClient(app) as client:
        result=client.get('/api/history/legacy').json()
        assert result['scoring_recalculated'] is True
        assert result['original_score']['percentage']==33.3
        assert result['tailored_score']['percentage']==33.3
        assert result['saved_scores']['original']['percentage']==0
        assert len(client.get('/api/history').json())==1
    assert app.state.store.assessment('legacy')==before


def test_generated_font_preserves_greek_characters(profile,tmp_path):
    from app.models import Fact
    from app.services.scoring import readability
    unicode_profile=profile.model_copy(update={'facts':[Fact(id='f1',section='projects',text='Built an ΑΡΙ integration with Python.')]})
    text,meta=create_pdf(unicode_profile,tmp_path/'unicode.pdf')
    assert 'ΑΡΙ' in text
    assert all(check['status']=='pass' for check in readability(text,unicode_profile,meta))


def test_updated_resume_reuses_requirements_and_preserves_prior_pdf(profile,tmp_path):
    fake=FakeAI(profile)
    app=create_app(Settings(_env_file=None,data_dir=tmp_path,gemini_api_key=''),ai=fake)
    with TestClient(app) as client:
        client.post('/api/resume',files={'file':('resume.pdf',sample_pdf(),'application/pdf')},data={'preferred_role':'Developer'})
        job=Job(id='lever:demo:one',source='lever',board='demo',company='Demo',title='Developer',location='Remote',description='Python required. Java required.',url='https://example.com/1')
        app.state.store.save_jobs([job])
        first=client.post('/api/jobs/lever:demo:one/analyse').json()
        pdf=client.get(f'/api/history/{first["id"]}/pdf').content
        response=client.post('/api/jobs/lever:demo:one/analyse',params={'reuse_assessment':first['id']})
        assert response.status_code==200,response.text
        updated=response.json()
        assert updated['id']!=first['id']
        assert updated['previous_version_id']==first['id']
        assert updated['analysis']==first['analysis']
        assert updated['tailored_score']['total']==first['tailored_score']['total']
        assert fake.analyses==1 and fake.extractions==1
        assert updated['pdf_style']['font']=='DejaVu Sans'
        assert client.get(f'/api/history/{first["id"]}/pdf').content==pdf
        assert len(client.get('/api/history').json())==2
        assert client.post('/api/jobs/wrong:job/analyse',params={'reuse_assessment':first['id']}).status_code==400
