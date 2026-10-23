from bs4 import BeautifulSoup
import html
from app.models import Job


def plain(value):
    soup = BeautifulSoup(html.unescape(value or ''), 'html.parser')
    for node in soup(['script', 'style']):
        node.decompose()
    return '\n'.join(line.strip() for line in soup.get_text('\n').splitlines() if line.strip())


async def fetch(client, board):
    response = await client.get(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs', params={'content': 'true'})
    response.raise_for_status()
    jobs = []
    for item in response.json().get('jobs', []):
        location = item.get('location', {}).get('name', 'Not specified')
        if location.lower() in {'in-office', 'in office', 'hybrid', 'on-site', 'onsite'}:
            offices = list(dict.fromkeys(o.get('name', '') for o in item.get('offices', []) if o.get('name')))
            if offices:
                location += ' · ' + ', '.join(offices)
        jobs.append(Job(id=f'greenhouse:{board}:{item["id"]}', source='greenhouse', board=board,
                        title=item['title'], company=board.replace('-', ' ').title(),
                        location=location,
                        description=plain(item.get('content', '')), url=item['absolute_url']))
    return jobs
