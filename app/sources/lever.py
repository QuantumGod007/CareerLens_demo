from app.models import Job
from app.sources.greenhouse import plain


async def fetch(client, board):
    response = await client.get(f'https://api.lever.co/v0/postings/{board}', params={'mode': 'json'})
    response.raise_for_status()
    jobs = []
    for item in response.json():
        categories = item.get('categories') or {}
        chunks = [item.get('descriptionPlain') or plain(item.get('description', ''))]
        for section in item.get('lists', []):
            chunks += [section.get('text', ''), plain(section.get('content', ''))]
        chunks.append(item.get('additionalPlain') or plain(item.get('additional', '')))
        jobs.append(Job(id=f'lever:{board}:{item["id"]}', source='lever', board=board,
                        title=item['text'], company=board.replace('-', ' ').title(),
                        location=categories.get('location', 'Not specified'),
                        job_type=categories.get('commitment', ''), description='\n'.join(chunks),
                        url=item.get('applyUrl') or item['hostedUrl']))
    return jobs
