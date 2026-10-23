import asyncio
import json
import logging
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import ROOT, get_settings
from app.models import Profile, ProfileUpdate, Job, Analysis, DiscoverRequest, ApplicationAnswers
from app.services.gemini import Gemini, AIError
from app.services.store import Store, now
from app.services.pdf import read_pdf, create_pdf, PDFError
from app.services.scoring import SCORING_VERSION, coverage, profile_text, readability
from app.services.discovery import discover
from app.services.content import clean_profile

MAX_UPLOAD = 10 * 1024 * 1024


def create_app(settings=None, ai=None):
    settings = (settings or get_settings()).prepare()
    store = Store(settings.data_dir)
    gemini = ai or Gemini(settings)

    app = FastAPI(title='CareerLens', version='1.0.0', docs_url='/api/docs', redoc_url=None)
    app.state.store = store
    app.state.gemini = gemini
    app.state.ai_lock = asyncio.Lock()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', '[::1]', 'testserver'])

    @app.middleware('http')
    async def local_security(request: Request, call_next):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': 'Cross-origin writes are disabled for this local application.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(AIError)
    async def ai_error(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=exc.status)

    @app.exception_handler(PDFError)
    async def pdf_error(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    def candidate_required(confirmed=False):
        candidate = store.candidate()
        if not candidate:
            raise HTTPException(409, 'Upload a resume first.')
        if confirmed and not candidate['confirmed']:
            raise HTTPException(409, 'Review and confirm your profile before finding or analysing jobs.')
        return candidate

    def idle_required():
        if app.state.ai_lock.locked():
            raise HTTPException(409, 'An operation is already running. Wait for it to finish.')

    def job_version(job):
        return hashlib.sha256(json.dumps({k: job[k] for k in ('id', 'title', 'description', 'url')},
                                         sort_keys=True).encode()).hexdigest()

    def assessment_required(record_id):
        record = store.assessment(record_id)
        if not record:
            raise HTTPException(404, 'This saved assessment was not found.')
        return record

    def public_record(record):
        result = dict(record)
        for key in ('original_path', 'tailored_path'):
            result.pop(key, None)
        # Old assessments retain their saved scores in SQLite. Present a clearly
        # labelled current calculation from the same saved PDF text/requirements,
        # without regenerating a document or overwriting the historical record.
        if record.get('scoring_version', 1) < SCORING_VERSION:
            result['saved_scores'] = {'original': record['original_score'], 'tailored': record['tailored_score']}
            required = record['analysis']['required']
            result['original_score'] = coverage(record['original_text'], required)
            result['tailored_score'] = coverage(record['tailored_text'], required)
            result['scoring_recalculated'] = True
        return result

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'gemini_configured': bool(settings.gemini_api_key), 'model': settings.gemini_model}

    @app.get('/api/state')
    def state():
        candidate = store.candidate()
        history = store.history()
        return {'candidate': {'profile': clean_profile(Profile.model_validate(candidate['profile'])).model_dump(), 'preferred_role': candidate['preferred_role'],
                              'confirmed': candidate['confirmed'], 'profile_version': candidate['profile_version'],
                              'updated_at': candidate['updated_at'], 'has_original': Path(candidate['upload_path']).is_file()} if candidate else None,
                'history': [public_record(r) for r in history],
                'gemini_configured': bool(settings.gemini_api_key), 'model': settings.gemini_model,
                'sources': {'greenhouse': settings.greenhouse_boards, 'lever': settings.lever_boards},
                'scoring_version': SCORING_VERSION}

    @app.post('/api/resume')
    async def upload_resume(file: UploadFile = File(...), preferred_role: str = Form(...)):
        idle_required()
        role = preferred_role.strip()
        if not 2 <= len(role) <= 150:
            raise HTTPException(422, 'Enter a preferred role between 2 and 150 characters.')
        data = await file.read(MAX_UPLOAD + 1)
        await file.close()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, 'The resume must be 10 MB or smaller.')
        original_text, _ = await run_in_threadpool(read_pdf, data)
        idle_required()
        async with app.state.ai_lock:
            profile = clean_profile(await run_in_threadpool(gemini.extract, data))
            upload_path = settings.data_dir / 'uploads' / f'{uuid4().hex}.pdf'
            upload_path.write_bytes(data)
            store.save_candidate(profile.model_dump(), role, upload_path, original_text)
        return {'profile': profile.model_dump(), 'preferred_role': role,
                'message': 'Resume extracted and saved. Review and confirm your profile next.'}

    @app.put('/api/profile')
    async def update_profile(payload: ProfileUpdate):
        idle_required()
        async with app.state.ai_lock:
            candidate = candidate_required()
            if (payload.expected_version is not None or payload.confirm) and payload.expected_version != candidate['profile_version']:
                raise HTTPException(409, 'Your profile changed. Reload and review the latest version.')
            profile = clean_profile(payload.profile)
            store.save_candidate(profile.model_dump(), payload.preferred_role.strip(),
                                 candidate['upload_path'], candidate['original_text'], confirmed=payload.confirm)
        return {'profile': profile.model_dump(), 'preferred_role': payload.preferred_role.strip(),
                'confirmed': payload.confirm, 'profile_version': store.candidate()['profile_version']}

    @app.get('/api/resume/original')
    def original_resume():
        candidate = candidate_required()
        path = Path(candidate['upload_path'])
        if not path.is_file():
            raise HTTPException(404, 'The original PDF is missing. Upload it again.')
        return FileResponse(path, media_type='application/pdf', filename='original-resume.pdf', content_disposition_type='inline')

    @app.post('/api/jobs/discover')
    async def discover_jobs(payload: DiscoverRequest):
        idle_required()
        async with app.state.ai_lock:
            candidate = candidate_required(confirmed=True)
            profile = Profile.model_validate(candidate['profile'])
            result = await discover(settings, profile, payload)
            latest = candidate_required(confirmed=True)
            if latest['profile_version'] != candidate['profile_version']:
                raise HTTPException(409, 'Your profile changed during discovery. Find jobs again.')
            store.save_jobs(result['jobs'])
        return {**result, 'jobs': [{**j.model_dump(), 'job_version': job_version(j.model_dump())} for j in result['jobs']], 'fetched_at': now()}

    @app.post('/api/jobs/{job_id}/analyse')
    async def analyse_job(job_id: str, reuse_assessment: str | None = None,
                          expected_version: str | None = None, expected_job: str | None = None):
        idle_required()
        previous = assessment_required(reuse_assessment) if reuse_assessment else None
        if previous and previous['job']['id'] != job_id:
            raise HTTPException(400, 'The saved assessment belongs to a different job.')
        raw = previous['job'] if previous else store.job(job_id)
        if not raw:
            raise HTTPException(404, 'Find this job again before analysing it.')
        if expected_job and expected_job != job_version(raw):
            raise HTTPException(409, 'This job description changed. Find jobs again and review it.')
        job = Job.model_validate(raw)
        if len(job.description) > 100_000:
            raise HTTPException(422, 'This listing is too long to analyse reliably.')
        async with app.state.ai_lock:
            candidate = candidate_required(confirmed=True)
            if expected_version and expected_version != candidate['profile_version']:
                raise HTTPException(409, 'Your profile changed. Review it and find jobs again.')
            profile = clean_profile(Profile.model_validate(candidate['profile']))
            analysis = (Analysis.model_validate(previous['analysis']) if previous else
                        await run_in_threadpool(gemini.analyse, profile, job))
            tailored, order, changes, verified = await run_in_threadpool(gemini.tailor, profile, job, analysis)
            record_id = uuid4().hex
            tailored_path = settings.data_dir / 'resumes' / f'{record_id}.pdf'
            try:
                tailored_text, pdf_meta = await run_in_threadpool(create_pdf, tailored, tailored_path, order)
                # Native PDF text is the original baseline; scanned PDFs use the saved transcription.
                original_text = candidate['original_text']
                baseline = 'Original PDF text'
                if len(original_text.strip()) < 30:
                    original_text = profile_text(profile)
                    baseline = 'Gemini transcription (source PDF has little or no extractable text)'
                record = {
                    'id': record_id, 'job': job.model_dump(), 'analysis': analysis.model_dump(),
                    'original_profile': profile.model_dump(), 'tailored_profile': tailored.model_dump(),
                    'original_text': original_text, 'tailored_text': tailored_text, 'baseline': baseline,
                    'section_order': order, 'changes': changes, 'verification_available': verified,
                    'profile_version': candidate['profile_version'],
                    'enhancement_status': ('enhanced' if any(c['kind'] == 'wording' for c in changes) else
                                           'selected' if any(c['kind'] == 'omission' for c in changes) else
                                           'reordered' if any(c['kind'] == 'order' for c in changes) else 'unchanged'),
                    'original_score': coverage(original_text, analysis.required),
                    'tailored_score': coverage(tailored_text, analysis.required),
                    'scoring_version': SCORING_VERSION,
                    'pdf_style': {'font': 'DejaVu Sans', 'body_pt': 10.2, 'heading_pt': 10,
                                  'name_pt': 22, 'contact_pt': 9, 'page': 'A4', 'layout': 'Single column'},
                    'original_checks': readability(candidate['original_text'], profile),
                    'tailored_checks': readability(tailored_text, tailored, pdf_meta),
                    'original_path': candidate['upload_path'], 'tailored_path': str(tailored_path),
                    'created_at': now(), 'simulations': [],
                }
                if previous:
                    record['previous_version_id'] = previous['id']
                store.save_assessment(record)
            except Exception:
                tailored_path.unlink(missing_ok=True)
                raise
        return public_record(record)

    @app.get('/api/history')
    def history():
        return [public_record(r) for r in store.history()]

    @app.get('/api/history/{record_id}')
    def get_record(record_id: str):
        return public_record(assessment_required(record_id))

    @app.get('/api/history/{record_id}/pdf')
    def download_pdf(record_id: str, original: bool = False, inline: bool = False):
        record = assessment_required(record_id)
        path = Path(record['original_path'] if original else record['tailored_path'])
        if not path.is_file():
            raise HTTPException(404, 'This saved PDF is missing from the local data directory.')
        label = 'original' if original else 'tailored'
        return FileResponse(path, media_type='application/pdf', filename=f'careerlens-{label}-{record_id[:8]}.pdf',
                            content_disposition_type='inline' if inline else 'attachment')

    @app.post('/api/test-receiver/{record_id}')
    def simulate(record_id: str, answers: ApplicationAnswers):
        record = assessment_required(record_id)
        if not Path(record['tailored_path']).is_file():
            raise HTTPException(409, 'The attached PDF is missing. Prepare another resume first.')
        return store.save_simulation(uuid4().hex, record_id, answers.model_dump())

    app.mount('/static', StaticFiles(directory=ROOT / 'app' / 'static'), name='static')

    @app.get('/')
    def index():
        return FileResponse(ROOT / 'app' / 'static' / 'index.html')

    return app


app = create_app()
