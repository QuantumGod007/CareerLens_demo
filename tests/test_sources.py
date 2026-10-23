import asyncio
import httpx
from app.models import Job, DiscoverRequest
from app.config import Settings
from app.sources import greenhouse,lever
from app.services.discovery import rank_jobs, discover


def test_adapters_parse_documented_payloads():
    def handler(request):
        if 'greenhouse' in str(request.url):
            return httpx.Response(200,json={'jobs':[{'id':1,'title':'Software Intern','location':{'name':'Remote'},'absolute_url':'https://example.com/job/1','content':'&lt;p&gt;Python &amp; SQL&lt;/p&gt;'}]})
        return httpx.Response(200,json=[{'id':'abc','text':'Backend Intern','categories':{'location':'Bengaluru','commitment':'Internship'},'descriptionPlain':'Build APIs','lists':[{'text':'Requirements','content':'<ul><li>Python required</li></ul>'}],'applyUrl':'https://example.com/job/2'}])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            a=await greenhouse.fetch(client,'demo');b=await lever.fetch(client,'demo')
            assert a[0].description=='Python & SQL'
            assert 'Python required' in b[0].description
            assert b[0].job_type=='Internship'
    asyncio.run(run())


def test_filter_rank_deduplicate(profile):
    def job(id,title,location='Remote'):
        return Job(id=id,source='lever',board='demo',title=title,company='Demo',location=location,
                   description='Python and SQL required.',url=f'https://example.com/{id}')
    jobs=[job('1','Software Engineering Intern'),job('2','Senior Software Engineer'),job('3','Marketing Intern')]
    result=rank_jobs([*jobs,jobs[0]],profile,'Software Developer Intern',entry_only=True)
    assert [j.id for j in result]==['1']
    assert result[0].matched_skills==['Python','SQL']
    assert not rank_jobs(jobs,profile,'Software Developer','London')


def test_source_failure_is_visible(profile,monkeypatch,tmp_path):
    async def fail(*args):raise httpx.ConnectError('Test failure')
    monkeypatch.setattr(greenhouse,'fetch',fail)
    result=asyncio.run(discover(Settings(_env_file=None,data_dir=tmp_path,greenhouse_boards='demo',lever_boards=''),profile,DiscoverRequest(role='Developer')))
    assert result['jobs']==[]
    assert result['sources'][0]['ok'] is False


def test_query_ids_distinguish_jobs(profile):
    jobs=[Job(id=str(i),source='greenhouse',board='demo',title=f'Software Engineer {i}',company='Demo',
              location='Remote',description='Python required',url=f'https://example.com/jobs?gh_jid={i}') for i in range(3)]
    assert len(rank_jobs(jobs,profile,'Software Engineer'))==3
    duplicate=jobs[0].model_copy(update={'url':jobs[0].url+'&utm_source=test'})
    assert len(rank_jobs([*jobs,duplicate],profile,'Software Engineer'))==3


def test_identical_content_is_deduplicated_across_post_ids(profile):
    job=Job(id='1',source='greenhouse',board='demo',title='Software Engineer Intern',company='Demo',
            location='Remote',description='Python required',url='https://example.com/job/1')
    duplicate=job.model_copy(update={'id':'2','url':'https://example.com/job/2'})
    assert len(rank_jobs([job,duplicate],profile,'Software Engineer'))==1
