"""Opt-in end-to-end Gemini/public-board check in an isolated data directory.

Defaults to synthetic data. --resume explicitly tests a user-supplied PDF instead.
Never reads or changes the main workspace profile/history.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.config import Settings
from app.main import create_app
from app.services.pdf import read_pdf
from app.services.content import split_entry, key
from app.models import Profile


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--resume',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    directory=root/'tmp'/('supplied-resume-check' if args.resume else 'live-smoke-focused')
    directory.mkdir(parents=True,exist_ok=True)
    directory.chmod(0o700)
    source=args.resume or directory/'synthetic-resume.pdf'
    if not args.resume:
        # Deliberately repeat a source paragraph; extraction must not multiply it.
        paragraphs=['Jordan Vale - SYNTHETIC TEST', 'jordan@example.com | Bengaluru, India',
            'Skills: Python, SQL, JavaScript, React, Git, REST APIs', 'EDUCATION',
            'B.Tech in Computer Science, Demo University, 2023-2027. Fictional test data.',
            'PROJECTS', 'LibraryLens (2026)',
            'Built a Python and SQL library catalog with 3 search filters.',
            'Added CSV exports and documented the Python REST APIs.',
            'Built a Python and SQL library catalog with 3 search filters.',
            'EventBoard (2025)', 'Built a React and JavaScript dashboard for student club events.',
            'Used Git to track changes and documented the dashboard setup.',
            'SketchPad (2024)', 'Built a JavaScript drawing canvas with 2 brush sizes.',
            'EXPERIENCE', 'Coursework contributor (2025)',
            'Used Git for version control and wrote Python tests for REST APIs.']
        styles=getSampleStyleSheet()
        SimpleDocTemplate(str(source)).build([item for text in paragraphs for item in (Paragraph(text,styles['BodyText']),Spacer(1,7))])
    settings=Settings(data_dir=directory)
    app=create_app(settings)
    checks={}
    with TestClient(app) as client:
        with source.open('rb') as stream:
            response=client.post('/api/resume',files={'file':('test-resume.pdf',stream,'application/pdf')},data={'preferred_role':'Software Engineer'})
        assert response.status_code==200,response.text
        candidate=client.get('/api/state').json()['candidate']
        extracted=candidate['profile']
        checks['gemini_pdf_extraction']={'ok':True,'skills':len(extracted['skills']),'entries':len(extracted['facts'])}
        assert not candidate['confirmed']
        assert client.post('/api/jobs/discover',json={'role':'Software Engineer'}).status_code==409
        response=client.put('/api/profile',json={'profile':extracted,'preferred_role':candidate['preferred_role'],
            'confirm':True,'expected_version':candidate['profile_version']})
        assert response.status_code==200,response.text
        version=response.json()['profile_version']
        print(json.dumps({'extraction_and_confirmation':checks['gemini_pdf_extraction']}),flush=True)
        response=client.post('/api/jobs/discover',json={'role':'Software Engineer','entry_only':False})
        assert response.status_code==200,response.text
        found=response.json()
        assert found['jobs'],'No live matching roles returned.'
        checks['public_job_discovery']={'ok':True,'matched':len(found['jobs']),'fetched':found['fetched_count'],'sources':found['sources']}
        print(json.dumps({'public_job_discovery':checks['public_job_discovery']}),flush=True)
        # Prefer an available backend/Python role; every candidate comes from the current real response.
        job=max(found['jobs'],key=lambda j:sum(word in j['description'].casefold() for word in ('python','backend','api')))
        response=client.post('/api/jobs/'+job['id']+'/analyse',params={'expected_version':version,'expected_job':job['job_version']})
        assert response.status_code==200,response.text
        record=response.json()
        assert record['job']['description']==job['description'] and record['profile_version']==version
        assert record['tailored_profile']['email']==extracted['email']
        assert record['original_score']['total']==record['tailored_score']['total']
        assert all(c['status'] in ('pass','na') for c in record['tailored_checks']),record['tailored_checks']
        pdf=client.get('/api/history/'+record['id']+'/pdf')
        assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
        assert client.get('/api/history/'+record['id']+'/pdf?inline=true').headers['content-disposition'].startswith('inline')
        output=directory/'verified-output.pdf';output.write_bytes(pdf.content)
        text,meta=read_pdf(pdf.content)
        profile=Profile.model_validate(record['tailored_profile'])
        headings=[split_entry(f)[0] for f in profile.facts if f.section=='projects' and split_entry(f)[0]]
        assert len({key(h) for h in headings})==len(headings)
        assert all(text.count(h)==1 for h in headings)
        if not args.resume:
            assert record['tailored_text'].count('LibraryLens')==1
            assert extracted['name'].startswith('Jordan')
        checks['assessment_and_pdf']={'ok':True,'company':job['company'],'title':job['title'],
            'original':record['original_score'],'enhanced':record['tailored_score'],
            'enhancement_status':record['enhancement_status'],
            'change_kinds':[c['kind'] for c in record['changes']],
            'checks':record['tailored_checks'],'pages':meta['pages'],'bytes':len(pdf.content)}
        (directory/'latest-assessment.json').write_text(json.dumps(record,indent=2))
    with TestClient(create_app(settings)) as reopened:
        assert reopened.get('/api/history/'+record['id']).status_code==200
        assert reopened.get('/api/history/'+record['id']+'/pdf').content==pdf.content
        checks['history_survives_restart']={'ok':True}
    (directory/'report.json').write_text(json.dumps(checks,indent=2))
    print(json.dumps(checks,indent=2),flush=True)


if __name__=='__main__':run()
