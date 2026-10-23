"""Small shared helpers for existing resume facts; no fuzzy content deletion."""
import re
import unicodedata


def key(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip(' \t\n.;')


def lines(text):
    result, seen = [], set()
    for line in text.splitlines():
        line = re.sub(r'^\s*[-•*]\s+', '', line).strip()
        if not line:
            continue
        # Remove exact repeated sentences, not similar claims or technology names.
        sentences, sentence_keys = [], set()
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])', line):
            identity = key(sentence)
            if identity in sentence_keys:
                continue
            sentence_keys.add(identity)
            sentences.append(sentence)
        line = ' '.join(sentences)
        identity = key(line)
        if identity not in seen:
            result.append(line)
            seen.add(identity)
    return result


def split_entry(fact):
    parts = lines(fact.text)
    if fact.section not in ('projects', 'experience', 'education') or not parts:
        return '', parts
    action = r'^(?:built|developed|created|implemented|used|designed|integrated|tested|wrote|worked|collaborated|contributed|maintained|engineered|architected|trained|added)\b'
    if len(parts) > 1 and not re.match(action, parts[0], re.I):
        return parts[0].rstrip(':'), parts[1:]
    if ': ' in parts[0] and fact.section != 'education':
        heading, body = parts[0].split(': ', 1)
        if not re.match(action, heading, re.I):
            return heading, [body, *parts[1:]]
    return '', parts


def grouped_entries(facts):
    entries, headings = [], {}
    for fact in facts:
        heading, body = split_entry(fact)
        identity = key(heading)
        entry = headings.get(identity) if heading else None
        if entry is None:
            entry = {'heading': heading, 'items': [], 'ids': [], 'seen': set()}
            entries.append(entry)
            if heading:
                headings[identity] = entry
        entry['ids'].append(fact.id)
        for text in body:
            identity = key(text)
            if identity not in entry['seen']:
                entry['items'].append(text)
                entry['seen'].add(identity)
    return entries


def clean_profile(profile):
    """Normalize new/current profiles only. Historical snapshots are untouched."""
    skills, skill_keys = [], set()
    for skill in profile.skills:
        if skill.strip() and key(skill) not in skill_keys:
            skills.append(skill.strip())
            skill_keys.add(key(skill))
    facts, seen = [], set()
    # Keep section order and each first source ID while grouping repeated headings.
    for section in dict.fromkeys(f.section for f in profile.facts):
        section_facts = [f for f in profile.facts if f.section == section]
        by_id = {f.id: f for f in section_facts}
        for entry in grouped_entries(section_facts):
            text = '\n'.join(([entry['heading']] if entry['heading'] else []) + entry['items'])
            identity = key(text)
            if not text or identity in seen:
                continue
            seen.add(identity)
            facts.append(by_id[entry['ids'][0]].model_copy(update={'text': text}))
    return profile.model_copy(update={'skills': skills, 'facts': facts}, deep=True)
