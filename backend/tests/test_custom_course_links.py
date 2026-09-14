import pytest
from sqlalchemy.exc import IntegrityError
from app.core.security import create_access_token
from app.models.course import Course

def auth(user): return {'Authorization':'Bearer '+create_access_token({'sub':str(user.id)})}

def test_custom_link_create_conflict_availability_and_stable_title(client,db,make_user):
    teacher=make_user('admin'); h=auth(teacher)
    body={'title':'Physics','description':'Study physics','category':'Science','slug':'my-physics'}
    created=client.post('/api/v1/courses',json=body,headers=h)
    assert created.status_code==200,created.text
    course=created.json(); assert course['slug']=='my-physics'
    assert client.get('/api/v1/courses/slug-availability?slug=MY-PHYSICS',headers=h).json()['available'] is False
    assert client.get(f"/api/v1/courses/slug-availability?slug=my-physics&exclude_course_id={course['id']}",headers=h).json()['available'] is True
    assert client.post('/api/v1/courses',json=body,headers=h).status_code==409
    updated=client.put(f"/api/v1/courses/{course['id']}",json={'title':'New physics title'},headers=h)
    assert updated.status_code==200 and updated.json()['slug']=='my-physics'
    assert client.put(f"/api/v1/courses/{course['id']}",json={'slug':'physics-lab'},headers=h).json()['slug']=='physics-lab'
    assert client.get('/api/v1/courses/PHYSICS-LAB',headers=h).status_code==200
    other=Course(post_author=teacher.id,post_title='Other',post_name='PHYSICS-LAB');db.add(other)
    with pytest.raises(IntegrityError):db.commit()
    db.rollback()

@pytest.mark.parametrize('slug',['123','new','categories','two--hyphens','../path','a','x'*121])
def test_invalid_course_links_rejected(client,make_user,slug):
    teacher=make_user('admin')
    response=client.post('/api/v1/courses',json={'title':'x','description':'x','category':'x','slug':slug},headers=auth(teacher))
    assert response.status_code==422
