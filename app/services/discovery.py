import asyncio
import re
import httpx
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from app.services.scoring import contains_skill
from app.sources import greenhouse, lever

STOP = {'a', 'an', 'and', 'the', 'for', 'of', 'in', 'intern', 'internship', 'junior', 'entry', 'level', 'fresher'}
EXPANSIONS = {'developer': {'developer', 'engineer', 'engineering'},
              'engineer': {'developer', 'engineer', 'engineering'},
              'software': {'software', 'backend', 'frontend', 'fullstack', 'full-stack'},
              'ai': {'ai', 'machine', 'learning', 'ml', 'intelligence'},
              'ml': {'ai', 'machine', 'learning', 'ml'}}


def role_terms(role):
    terms = set()
    for token in re.findall(r'[a-z0-9+#-]+', role.lower()):
        if token not in STOP:
            terms.update(EXPANSIONS.get(token, {token}))
    return terms


def rank_jobs(jobs, profile, role, location='', entry_only=False):
    terms = role_terms(role)
    early_search = bool(re.search(r'\b(intern|internship|graduate|junior|entry|fresher)\b', role, re.I))
    scored, seen, content_seen = [], set(), set()
    for job in jobs:
        url = urlsplit(job.url)
        # Some companies distinguish every job with a query parameter (gh_jid).
        # Remove tracking only; stripping the entire query collapses real roles.
        query = sorted((k, v) for k, v in parse_qsl(url.query) if not k.startswith('utm_'))
        identity = urlunsplit((url.scheme, url.netloc, url.path.rstrip('/'), urlencode(query), ''))
        if identity in seen:
            continue
        seen.add(identity)
        fingerprint = (job.company.casefold(), job.title.casefold(), job.location.casefold(),
                       ' '.join(job.description.casefold().split()))
        if fingerprint in content_seen:
            continue
        content_seen.add(fingerprint)
        title_tokens = set(re.findall(r'[a-z0-9+#-]+', job.title.lower()))
        overlap = terms & title_tokens
        entry = bool(re.search(r'\b(intern|internship|graduate|junior|entry.level|new.grad|early.career)\b', job.title, re.I))
        if terms and not overlap:
            continue
        if entry_only and not entry:
            continue
        if location and location.lower() not in job.location.lower():
            continue
        matches = [s for s in profile.skills if contains_skill(job.description, s)]
        job.matched_skills = matches
        job.match_reasons = ([f'Role keywords: {", ".join(sorted(overlap))}'] if overlap else [])
        if matches:
            job.match_reasons.append(f'{len(matches)} of your saved skills appear in this listing')
        if entry:
            job.match_reasons.append('Early-career title')
        senior = bool(re.search(r'\b(senior|staff|principal|lead|manager|director)\b', job.title, re.I))
        if early_search and senior:
            job.match_reasons.append('Senior title: review experience requirements')
        score = len(overlap) * 5 + len(matches) * 2 + (12 if entry and early_search else 4 if entry else 0)
        if early_search and senior:
            score -= 14
        scored.append((score, job.title, job))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:10]]


async def discover(settings, profile, request):
    sources = []
    for name, values, adapter in [('greenhouse', settings.greenhouse_boards, greenhouse),
                                   ('lever', settings.lever_boards, lever)]:
        for board in dict.fromkeys(v.strip() for v in values.split(',') if v.strip()):
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', board):
                continue
            sources.append((name, board, adapter))
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers={'User-Agent': 'CareerLens-Local/1.0'}) as client:
        results = await asyncio.gather(*(adapter.fetch(client, board) for _, board, adapter in sources), return_exceptions=True)
    jobs, statuses = [], []
    for (name, board, _), result in zip(sources, results):
        if isinstance(result, Exception):
            status = getattr(getattr(result, 'response', None), 'status_code', None)
            statuses.append({'source': name, 'board': board, 'ok': False, 'count': 0,
                             'message': f'Public board unavailable{f" (HTTP {status})" if status else ""}. Check the board identifier or try again.'})
        else:
            jobs += result
            statuses.append({'source': name, 'board': board, 'ok': True, 'count': len(result), 'message': 'Live public listings fetched.'})
    return {'jobs': rank_jobs(jobs, profile, request.role, request.location, request.entry_only),
            'sources': statuses, 'fetched_count': len(jobs)}
