import pytest
from app.models import Profile, Fact


@pytest.fixture
def profile():
    return Profile(name='Demo Candidate', email='demo@example.com', phone='+91 9000000000',
                   skills=['Python', 'JavaScript', 'SQL'],
                   facts=[Fact(id='f1', section='education', text='B.Tech in Computer Science, Demo University, 2023-2027.'),
                          Fact(id='f2', section='projects', text='Built a Python and SQL library catalog with 3 search filters.'),
                          Fact(id='f3', section='experience', text='Developed a JavaScript dashboard for a student club.')])
