"""No network: exercise money boundaries, single-paper delivery and staff sources."""
import hashlib
import hmac
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.core.security import create_access_token
from app.models.exam_paper import ExamPaper, ExamPriceSlab
from app.models.payment import Payment, Order
from app.models.sileos_pack import BankQuestion
from app.services import exam_paper_service as svc


def headers(user):
    return {'Authorization': 'Bearer '+create_access_token({'sub': str(user.id)})}


@pytest.fixture
def setup(db, make_user, monkeypatch, TestingSessionLocal):
    from app.models.user import InstructorProfile
    from app.routers import payments
    admin = make_user('admin'); student = make_user(); teacher = make_user('instructor')
    db.add(InstructorProfile(user_id=teacher.id, is_approved=True)); db.commit()
    gateway = Mock()
    gateway.order.create.side_effect = lambda body: {'id': 'order_'+body['receipt']}
    monkeypatch.setattr(payments, '_razorpay_client', lambda: gateway)
    monkeypatch.setattr(payments, '_razorpay_creds', lambda: ('test_key', 'test_secret'))
    monkeypatch.setattr(svc.llm_provider, 'llm_configured', lambda: True)
    import app.core.database as core
    monkeypatch.setattr(core, 'SessionLocal', TestingSessionLocal)
    return SimpleNamespace(admin=admin, student=student, teacher=teacher, gateway=gateway)


def slab(client, user, **changes):
    body = {'exam':'JEE','title':'Short practice','min_questions':5,'max_questions':20,'price_paise':2500,'active':True, **changes}
    return client.post('/api/v1/exam-papers/admin/slabs', json=body, headers=headers(user))


def create(client, user, **changes):
    return client.post('/api/v1/exam-papers', json={'exam':'JEE','count':5,'topic':'Algebra', **changes}, headers=headers(user))


def capture(client, setup, paper, **changes):
    payment_id = 'pay_'+paper['id']
    entity = {'id':payment_id,'order_id':paper['gateway_order_id'],'status':'captured','currency':'INR','amount':paper['amount_paise'], **changes}
    setup.gateway.payment.fetch.return_value = entity
    signature = hmac.new(b'test_secret', f"{paper['gateway_order_id']}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    response = client.post(f"/api/v1/exam-papers/{paper['id']}/verify", json={'razorpay_order_id':paper['gateway_order_id'],'razorpay_payment_id':payment_id,'razorpay_signature':signature}, headers=headers(setup.student))
    return response, entity


def questions(count=5):
    return [{'question_title':f'Solve equation {i}', 'question_type':'multiple_choice','question_mark':4,'options':['1','2','3','4'],'correct_answer':0,'answer_explanation':'Worked explanation','difficulty':'medium'} for i in range(count)]


def test_admin_ranges_and_frontend_visibility(client, setup):
    assert slab(client, setup.student).status_code == 403
    row = slab(client, setup.admin).json()
    assert slab(client, setup.admin, min_questions=20,max_questions=30).status_code == 409
    assert slab(client, setup.admin, exam='NEET').status_code == 201
    assert slab(client, setup.admin, min_questions=40,max_questions=30).status_code == 422
    assert slab(client, setup.admin, price_paise=0).status_code == 422
    assert client.delete(f"/api/v1/exam-papers/admin/slabs/{row['id']}",headers=headers(setup.admin)).status_code == 200
    visible=client.get('/api/v1/exam-papers/pricing',headers=headers(setup.student)).json()['slabs']
    assert [s['exam'] for s in visible] == ['NEET']
    assert create(client,setup.student).status_code == 409


def test_payment_required_private_and_immutable_quote(client, db, setup):
    slabrow=slab(client,setup.admin).json()
    paper=create(client,setup.student).json()['paper']
    assert client.post(f"/api/v1/exam-papers/{paper['id']}/generate",headers=headers(setup.student)).status_code == 402
    assert client.get(f"/api/v1/exam-papers/{paper['id']}",headers=headers(setup.teacher)).status_code == 404
    assert create(client,setup.student,source_text='private source').status_code == 403
    db.get(ExamPriceSlab,slabrow['id']).price_paise=9000; db.commit()
    client.delete(f"/api/v1/exam-papers/admin/slabs/{slabrow['id']}",headers=headers(setup.admin))
    response,_=capture(client,setup,paper)
    assert response.status_code == 200, response.text
    assert response.json()['amount_paise'] == 2500
    assert capture(client,setup,paper)[0].status_code == 200
    assert db.query(Payment).count() == db.query(Order).count() == 1


@pytest.mark.parametrize('changes',[{'amount':1},{'currency':'USD'},{'status':'authorized'},{'order_id':'other'},{'amount_refunded':1}])
def test_invalid_capture_never_unlocks(client,db,setup,changes):
    slab(client,setup.admin); paper=create(client,setup.student).json()['paper']
    assert capture(client,setup,paper,**changes)[0].status_code == 409
    assert db.query(Payment).count() == 0


def test_forged_signature_and_wrong_owner(client, setup):
    slab(client,setup.admin); paper=create(client,setup.student).json()['paper']
    body={'razorpay_order_id':paper['gateway_order_id'],'razorpay_payment_id':'pay_x','razorpay_signature':'forged'}
    assert client.post(f"/api/v1/exam-papers/{paper['id']}/verify",json=body,headers=headers(setup.student)).status_code == 400
    assert client.post(f"/api/v1/exam-papers/{paper['id']}/verify",json=body,headers=headers(setup.teacher)).status_code == 404
    setup.gateway.payment.fetch.assert_not_called()


def test_staff_sources_background_validation_and_paid_retry(client,db,setup,monkeypatch):
    captured=[]
    def provider(system,prompt): captured.append(prompt); return json.dumps(questions())
    monkeypatch.setattr(svc.llm_provider,'call_glm',provider)
    upload=client.post('/api/v1/exam-papers/sources',files={'file':('chapter.txt',b'Fractions and algebra')},headers=headers(setup.teacher))
    assert upload.status_code == 200
    paper=create(client,setup.teacher,source_text=upload.json()['text']).json()['paper']
    assert paper['amount_paise'] == 0
    assert client.post(f"/api/v1/exam-papers/{paper['id']}/generate",headers=headers(setup.teacher)).status_code == 202
    result=client.get(f"/api/v1/exam-papers/{paper['id']}",headers=headers(setup.teacher)).json()
    assert result['status']=='completed' and len(result['questions'])==5
    assert db.query(BankQuestion).count()==5 and 'Fractions and algebra' in captured[0]
    slab(client,setup.admin); paid=create(client,setup.student).json()['paper']; capture(client,setup,paid)
    monkeypatch.setattr(svc.llm_provider,'call_glm',lambda *args: '[]')
    client.post(f"/api/v1/exam-papers/{paid['id']}/generate",headers=headers(setup.student))
    assert client.get(f"/api/v1/exam-papers/{paid['id']}",headers=headers(setup.student)).json()['status']=='failed'
    monkeypatch.setattr(svc.llm_provider,'call_glm',provider)
    client.post(f"/api/v1/exam-papers/{paid['id']}/generate",headers=headers(setup.student))
    result=client.get(f"/api/v1/exam-papers/{paid['id']}",headers=headers(setup.student)).json()
    assert result['status']=='completed' and result['bank_id'] is None
    client.post(f"/api/v1/exam-papers/{paid['id']}/generate",headers=headers(setup.student))
    assert db.query(Payment).count()==1 and db.query(BankQuestion).count()==5


def test_webhook_recovery_and_refund_hides_paper(client,db,setup):
    from app.services.webhook_processor import _handle_payment_captured, _handle_refund_processed
    slab(client,setup.admin); paper=create(client,setup.student).json()['paper']
    entity={'id':'pay_recovered','order_id':paper['gateway_order_id'],'amount':2500,'currency':'INR','status':'captured'}
    event=SimpleNamespace(event_id='test', payload={'payload':{'payment':{'entity':entity}}})
    _handle_payment_captured(db,event); db.commit()
    _handle_payment_captured(db,event); db.commit()
    row=db.get(ExamPaper,paper['id']); row.status='completed'; row.questions=questions(); db.commit()
    _handle_refund_processed(db,SimpleNamespace(event_id='refund',payload={'payload':{'refund':{'entity':{'payment_id':'pay_recovered','id':'refund_1'}}}})); db.commit(); db.expire_all()
    result=client.get(f"/api/v1/exam-papers/{paper['id']}",headers=headers(setup.student)).json()
    assert result['status']=='refunded' and result['questions'] is None
    assert client.post(f"/api/v1/exam-papers/{paper['id']}/generate",headers=headers(setup.student)).status_code==402
    assert db.query(Payment).count()==1


def test_unavailable_provider_prevents_checkout_and_sources_are_validated(client,setup,monkeypatch):
    monkeypatch.setattr(svc.llm_provider,'llm_configured',lambda:False)
    assert create(client,setup.student).status_code==503
    setup.gateway.order.create.assert_not_called()
    for filename,data in [('fake.pdf',b'bad'),('file.exe',b'hello'),('empty.txt',b'')]:
        assert client.post('/api/v1/exam-papers/sources',files={'file':(filename,data)},headers=headers(setup.teacher)).status_code==422
    assert client.post('/api/v1/exam-papers/sources',files={'file':('test.txt',b'hello')},headers=headers(setup.student)).status_code==403
    from reportlab.pdfgen import canvas
    stream=io.BytesIO(); c=canvas.Canvas(stream);c.drawString(60,720,'Physics source chapter');c.save()
    assert 'Physics' in svc.extract_source(stream.getvalue(),'source.pdf')


def test_interrupted_generation_becomes_retryable_and_superseded_worker_exits(client,db,setup,monkeypatch,TestingSessionLocal):
    from datetime import timedelta
    paper=create(client,setup.teacher).json()['paper']
    row=db.get(ExamPaper,paper['id']);row.status='generating';row.generation_id='old';row.started_at=svc.now()-timedelta(hours=2);db.commit()
    result=client.get(f"/api/v1/exam-papers/{paper['id']}",headers=headers(setup.teacher)).json()
    assert result['status']=='failed' and 'without paying again' in result['error']
    provider=Mock();monkeypatch.setattr(svc.llm_provider,'call_glm',provider)
    svc.run_paper(paper['id'],'old',TestingSessionLocal)
    provider.assert_not_called()
