from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from app.core.security import create_access_token
from app.models.course import Course
from app.models.payment import Order, Payment, PaymentStatus
from app.models.learning_planner import LearningGoal, LearningIntervention, LearningPlanTask
from app.services import operations_service as svc

def auth(client,user):
    client.headers['Authorization']='Bearer '+create_access_token({'sub':str(user.id)})

def test_admin_tables_access_filter_pagination_and_csv(client, db, make_user, student_user):
    auth(client,student_user)
    assert client.get('/api/v1/admin/operations/lists/courses').status_code==403
    admin=make_user(role='admin',email='operations@example.com'); auth(client,admin)
    db.add_all([Course(post_author=admin.id,post_title=name,post_status='draft') for name in ['=Formula','100% complete','Ordinary']]); db.commit()
    url='/api/v1/admin/operations/lists/courses'
    result=client.get(url,params={'q':'%'}).json()
    assert result['total']==1 and result['items'][0]['name']=='100% complete'
    result=client.get(url,params={'page_size':1,'page':2,'sort':'name','order':'asc'}).json()
    assert result['total']==3 and len(result['items'])==1
    assert client.get(url,params={'sort':'DROP TABLE'}).status_code==422
    csv=client.get(url+'/export.csv').text
    assert "'=Formula" in csv
    assert client.get('/api/v1/admin/operations/summary').status_code==200

def test_revenue_uses_refund_processing_date(db,make_user):
    user=make_user(email='revenue@example.com'); order=Order(user_id=user.id,order_key='revenue-order'); db.add(order);db.flush()
    db.add_all([Payment(payment_method="test",order_id=order.id,user_id=user.id,amount=Decimal('120'),currency='INR',payment_status=PaymentStatus.REFUNDED,payment_date=datetime(2026,1,1,tzinfo=timezone.utc),refund_processed_at=datetime(2026,2,1,tzinfo=timezone.utc)),Payment(payment_method="test",order_id=order.id,user_id=user.id,amount=Decimal('50'),currency='INR',payment_status=PaymentStatus.COMPLETED,payment_date=datetime(2026,2,2,tzinfo=timezone.utc))]);db.commit()
    result=svc.revenue(db,date(2026,2,1),date(2026,2,28))
    assert result['currencies']==[{'currency':'INR','captured':50.0,'refunded':120.0,'net_cash':-70.0}]

def test_outcomes_exclude_insufficient_or_reversed_checks(db,make_user):
    user=make_user(email='outcomes@example.com'); course=Course(post_author=user.id,post_title='Course');db.add(course);db.flush()
    goal=LearningGoal(user_id=user.id,course_id=course.id,title='Goal',target_date=date.today());db.add(goal);db.flush()
    intervention=LearningIntervention(goal_id=goal.id,concept='fractions',reason='Evidence',latest_score=20,followup_score=100);db.add(intervention);db.flush()
    start=datetime.now(timezone.utc)
    for kind,score,offset,enough in [('practice',50,0,True),('followup',90,3,False)]:
        db.add(LearningPlanTask(goal_id=goal.id,intervention_id=intervention.id,task_key=kind,kind=kind,title=kind,reason='Check',minutes=10,due_date=date.today(),not_before=date.today(),status='done',completed_at=start+timedelta(days=offset),outcome={'score':score,'enough_evidence':enough}))
    db.commit();assert svc.outcomes(db)['paired_interventions']==0
    task=db.query(LearningPlanTask).filter_by(kind='followup').one();task.outcome={'score':90,'enough_evidence':True};db.commit()
    assert svc.outcomes(db)['mean_delayed_change']==40
    task.completed_at=start-timedelta(days=1);db.commit();assert svc.outcomes(db)['paired_interventions']==0
def test_missing_upload_volume_keeps_health_available(db, monkeypatch):
    from app.services import operations_service

    def missing_volume(_path):
        raise FileNotFoundError("Synthetic missing upload mount")

    monkeypatch.setattr(operations_service.shutil, "disk_usage", missing_volume)
    result = operations_service.health(db)
    assert result["database"] == "ok"
    assert result["storage"]["status"] == "unavailable"
    assert result["storage"]["free_bytes"] is None
    assert result["storage"]["free_percent"] is None
