"""Opt-in LIVE test: uses Gemini credits and actual public boards.

All candidate content is labelled test data and stored under tmp/live-smoke.
Never seeds the user's main workspace. Run from the project root.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.models import Profile, Fact
from app.services.pdf import create_pdf


def run():
    root=Path(__file__).resolve().parent.parent
    directory=root/'tmp'/'live-smoke'
    directory.mkdir(parents=True,exist_ok=True)
    profile=Profile(name='Demo Candidate - TEST ONLY',email='demo@example.com',location='Bengaluru, India',
                    skills=['Python','JavaScript','SQL','React','Git','REST APIs'],
                    facts=[Fact(id='f1',section='education',text='B.Tech in Computer Science, Demo University, 2023-2027. This is fictional test data.'),
                           Fact(id='f2',section='projects',text='Built a Python and SQL library catalog with 3 search filters.'),
                           Fact(id='f3',section='projects',text='Built a React and JavaScript dashboard for tracking student club events.'),
                           Fact(id='f4',section='experience',text='Used Git for version control in coursework and built REST APIs with Python.')])
    source=directory/'demo-test-resume.pdf'
    create_pdf(profile,source)
    settings=Settings(data_dir=directory)
    app=create_app(settings)
    checks={}
    with TestClient(app) as client:
        with source.open('rb') as stream:
            response=client.post('/api/resume',files={'file':('demo-test-resume.pdf',stream,'application/pdf')},data={'preferred_role':'Software Engineer'})
        assert response.status_code==200,response.text
        extracted=response.json()['profile']
        assert 'Python' in extracted['skills'],extracted
        checks['native_gemini_pdf_extraction']={'ok':True,'skills':len(extracted['skills']),'facts':len(extracted['facts'])}
        print(json.dumps(checks),flush=True)
        response=client.post('/api/jobs/discover',json={'role':'Software Engineer','entry_only':False})
        assert response.status_code==200,response.text
        found=response.json()
        assert found['jobs'],'No live matching roles returned: '+str(found['sources'])
        checks['public_job_discovery']={'ok':True,'matched':len(found['jobs']),'fetched':found['fetched_count'],'sources':found['sources']}
        print(json.dumps({'public_job_discovery':checks['public_job_discovery']}),flush=True)
        job=found['jobs'][0]
        response=client.post('/api/jobs/'+job['id']+'/analyse')
        assert response.status_code==200,response.text
        record=response.json()
        assert len(record['tailored_profile']['facts'])==len(record['original_profile']['facts'])
        assert record['tailored_profile']['email']==record['original_profile']['email']
        assert record['original_score']['total']==record['tailored_score']['total']
        checks['analysis_tailoring_and_coverage']={'ok':True,'company':job['company'],'title':job['title'],
            'original':record['original_score'],'tailored':record['tailored_score'],'changes':len(record['changes']),
            'tailored_checks':record['tailored_checks']}
        pdf=client.get('/api/history/'+record['id']+'/pdf')
        assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
        checks['pdf_download']={'ok':True,'bytes':len(pdf.content)}
        receipt=client.post('/api/test-receiver/'+record['id'],json={'name':'Demo Test','email':'demo@example.com','work_authorization':'Test answer only','availability':'Test only'})
        assert receipt.status_code==200 and receipt.json()['status']=='simulated'
        checks['simulated_local_receiver']={'ok':True}
        (directory/'latest-assessment.json').write_text(json.dumps(record,indent=2))
    with TestClient(create_app(settings)) as reopened:
        assert reopened.get('/api/history/'+record['id']).status_code==200
        assert reopened.get('/api/history/'+record['id']+'/pdf').status_code==200
        assert reopened.get('/api/history/'+record['id']).json()['simulations']
        checks['history_survives_restart']={'ok':True}
    (directory/'report.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(checks,indent=2),flush=True)


if __name__=='__main__':run()
