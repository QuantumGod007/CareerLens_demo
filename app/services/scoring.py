"""Deterministic, boundary-aware coverage. No employer ATS claims."""
import re
import unicodedata

from app.models import Profile
from app.services.content import split_entry

SCORING_VERSION = 2

ALIASES = {
    'javascript': ['javascript', 'js'], 'typescript': ['typescript', 'ts'],
    'python': ['python', 'python3'], 'c++': ['c++', 'cpp'],
    'c#': ['c#', 'csharp'], 'node.js': ['node.js', 'nodejs', 'node js'],
    'react': ['react', 'react.js', 'reactjs'], 'postgresql': ['postgresql', 'postgres'],
    'machine learning': ['machine learning', 'ml'],
    'artificial intelligence': ['artificial intelligence', 'ai'],
    'amazon web services': ['amazon web services', 'aws'],
    'google cloud': ['google cloud', 'gcp', 'google cloud platform'],
    'scikit-learn': ['scikit-learn', 'sklearn', 'scikit learn'],
    'pytorch': ['pytorch', 'torch'], 'rest': ['rest', 'restful'],
    'natural language processing': ['natural language processing', 'nlp'],
    'written communication': ['written communication', 'written communication skills', 'technical writing'],
}

# These narrow category rules connect an explicit broad requirement with explicit
# resume evidence. They do not infer proficiency, years, eligibility or soft skills.
PROGRAMMING_LABELS = {'programming', 'programming skills', 'programming fundamentals',
                      'programming languages', 'coding', 'coding skills'}
PROGRAMMING_LANGUAGES = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#',
                         'C', 'Rust', 'Ruby', 'Swift', 'Kotlin', 'Scala', 'Dart',
                         'PHP', 'Golang', 'Solidity', 'MATLAB', 'Perl', 'Fortran']
AI_TOOL_LABELS = {'ai tools', 'generative ai tools', 'genai tools', 'ai-assisted development tools'}
AI_TOOLS = ['ChatGPT', 'GitHub Copilot', 'Claude Code', 'Gemini CLI', 'Google AI Studio',
            'Google Gemini', 'OpenAI Codex', 'Cursor IDE', 'Cursor AI']


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip()


def aliases(skill):
    target = normalize(skill)
    for key, values in ALIASES.items():
        if target == key or target in values:
            return values
    return [target]


def contains_skill(text, skill):
    text = normalize(text)
    for term in aliases(skill):
        # Keep C, C++, C#, Java, and JavaScript distinct.
        if re.search(r'(?<![\w+#])' + re.escape(term) + r'(?![\w+#])', text):
            return True
    return False


def canonical(skill):
    return aliases(skill)[0]


def match_requirement(text, skill):
    # Use content lines for category evidence so a name, email or URL cannot
    # establish programming or tool experience on its own.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    direct = next((line for line in lines if contains_skill(line, skill)), None)
    if direct:
        return {'skill': skill, 'matched': True, 'method': 'explicit text or alias',
                'evidence': direct[:350]}
    label = normalize(skill)
    content = [line for line in lines if not re.search(r'https?://|www\.|[^\s@]+@[^\s@]+', line, re.I)]
    supported_by = (PROGRAMMING_LANGUAGES if label in PROGRAMMING_LABELS else
                    AI_TOOLS if label in AI_TOOL_LABELS else [])
    for term in supported_by:
        line = next((line for line in content if contains_skill(line, term)), None)
        if line:
            return {'skill': skill, 'matched': True, 'method': f'explicit evidence: {term}',
                    'evidence': line[:350]}
    return {'skill': skill, 'matched': False, 'method': 'no explicit supporting evidence', 'evidence': ''}


def coverage(text, requirements):
    unique = {}
    for item in requirements:
        skill = item.skill if hasattr(item, 'skill') else item['skill']
        unique.setdefault(canonical(skill), skill)
    evidence = [match_requirement(text, skill) for skill in unique.values()]
    matched = [item['skill'] for item in evidence if item['matched']]
    missing = [item['skill'] for item in evidence if not item['matched']]
    total = len(unique)
    return {'percentage': round(len(matched) / total * 100, 1) if total else None,
            'matched_count': len(matched), 'total': total, 'matched': matched, 'missing': missing,
            'evidence': evidence}


def profile_text(profile: Profile, section_order=None):
    parts = [profile.name, profile.email, profile.phone, profile.location, *profile.links,
             'Skills', ', '.join(profile.skills)]
    order = section_order or ['summary', 'education', 'experience', 'projects', 'certifications', 'achievements']
    for section in order:
        facts = [f for f in profile.facts if f.section == section]
        if facts:
            parts += [section.title(), *[f.text for f in facts]]
    return '\n'.join(p for p in parts if p)


def readability(text, profile, pdf_meta=None):
    contacts = [v for v in [profile.email, profile.phone, *profile.links] if v]
    compact = lambda s: re.sub(r'\s+', '', normalize(s))
    retained = all(compact(v) in compact(text) for v in contacts)
    headings = [s.title() for s in ['education', 'experience', 'projects', 'certifications', 'achievements']
                if any(f.section == s for f in profile.facts)]
    positions = []
    for heading in headings:
        match = re.search(r'^\s*' + re.escape(heading) + r'\s*[:\-]?\s*$', text, re.I | re.M)
        if match:
            positions.append((match.start(), heading))
    headings_found = [heading for _, heading in sorted(positions)]
    # This checks actual fact retention, not just page count or a word limit.
    missing_facts = []
    for fact in profile.facts:
        heading, body = split_entry(fact)
        parts = ([heading] if heading else []) + body
        if any(compact(part) not in compact(text) for part in parts):
            missing_facts.append(fact.id)
    return [
        {'name': 'PDF text extraction', 'status': 'pass' if len(text.strip()) > 30 else 'review',
         'detail': f"{len(text.strip()):,} extractable characters" + (f" across {pdf_meta['pages']} page(s)." if pdf_meta else '.')},
        {'name': 'Contact retention', 'status': ('pass' if retained else 'review') if contacts else 'na',
         'detail': ('All saved contact details are present.' if retained else 'Some contact details need checking.') if contacts else 'No contact details were provided.'},
        {'name': 'Section order', 'status': 'pass' if len(headings_found) == len(headings) and headings else 'review',
         'detail': 'Reading order: ' + ' → '.join(headings_found) + '. Review this order against the role.' if headings_found else 'Check headings and reading order in the PDF preview.'},
        {'name': 'Content retention', 'status': 'pass' if not missing_facts else 'review',
         'detail': 'All saved facts are extractable; no content was dropped.' if not missing_facts else f'{len(missing_facts)} saved fact(s) need visual review; extraction may differ from the source.'},
    ]
