from datetime import date, timedelta, timezone, datetime
from decimal import Decimal
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.models.platform_tenant import PlatformTenant, PlatformTenantMembership
from app.models.commercial import CommercialContract, CommercialInvoice, RevenueLedgerEvent
from app.models.growth import BillingOccurrence, PartnerAccrual, CommercialDelivery, GrowthLead, GrowthTask, GrowthAssignment
from app.schemas.commercial import OfferCreate, ContractCreate, PaymentRecord, RefundRecord
from app.schemas.growth import PolicyCommand, ExperimentCommand, LeadUpdate, SettlementCommand
from app.services import commercial_service as commerce, growth_billing as billing, growth_service as growth

ROOT = '/api/v1/platform/growth'


@pytest.fixture
def setup(db, make_user):
    admin = make_user(role='admin'); owner = make_user(role='instructor'); partner = make_user(role='instructor')
    tenant = PlatformTenant(slug='growth-academy', name='Growth Academy', status='active', created_by=admin.id)
    db.add(tenant); db.flush()
    db.add(PlatformTenantMembership(tenant_id=tenant.id, user_id=owner.id, role='owner', status='active'))
    db.commit()
    return SimpleNamespace(admin=admin, owner=owner, partner=partner, tenant=tenant)


def agreement(db, s, model='one_time', amount='1000.00', vertical='meiporul', stream='asset_licensing'):
    from app.models.three_d import ThreeDModel
    asset = ThreeDModel(owner_id=s.admin.id,title='Licensed test asset',file_path='test-only.glb')
    db.add(asset); db.flush()
    offer = commerce.create_offer(db, OfferCreate(sku=f'TEST-{db.query(CommercialContract).count()}', business_vertical=vertical,
        revenue_stream=stream, name='Sample licensed asset', billing_model=model, unit_amount=amount), s.admin.id)
    contract = commerce.create_contract(db, ContractCreate(tenant_id=s.tenant.id, offer_id=offer['id'], starts_on=billing.today(),
        billing_interval='monthly' if model == 'subscription' else None), s.admin.id)
    policy = PolicyCommand(tax_profile={'supplier_name':'Sasha Test', 'supplier_address':'Test address Chennai',
        'supplier_gstin':'33ABCDE1234F1Z5', 'supplier_state':'33', 'customer_name':'Academy Test', 'customer_address':'Test Chennai address',
        'place_of_supply':'33', 'hsn_sac':'9992', 'rate_bps':1800, 'reviewed_by':'Test-only profile'}, resource_type='asset_license',
        resource_reference=str(asset.id), partner_id=s.partner.id, partner_bps=2000, automation_enabled=model=='subscription')
    billing.set_policy(db, contract['id'], policy, s.admin)
    return offer, db.get(CommercialContract, contract['id'])


def pay(db, s, invoice):
    return commerce.record_payment(db, invoice['id'], PaymentRecord(source_event_key='test:payment:'+str(invoice['id']),
        payment_reference='test-payment', occurred_at=growth.now(), reason='Test payment'), s.admin.id)


def test_tax_split_and_interstate_rounding():
    assert billing.tax_breakdown(Decimal('100'), {'rate_bps':1800,'supplier_state':'33','place_of_supply':'33'})['total'] == '18.00'
    assert billing.tax_breakdown(Decimal('100'), {'rate_bps':1800,'supplier_state':'33','place_of_supply':'29'})['igst'] == '18.00'
    assert billing.advance(date(2026,1,31), 'monthly',31) == date(2026,2,28)
    assert billing.advance(date(2026,2,28), 'monthly',31) == date(2026,3,31)


def test_invoice_capture_delivery_and_refund_are_idempotent(db, setup):
    _, contract = agreement(db, setup)
    invoice = billing.issue(db, contract.id, 'initial', setup.admin.id)
    assert invoice['total_amount'] == 1180
    assert billing.issue(db, contract.id, 'initial', setup.admin.id)['id'] == invoice['id']
    with pytest.raises(HTTPException): billing.issue(db, contract.id, 'duplicate', setup.admin.id)
    event = pay(db, setup, invoice)
    pay(db, setup, invoice)
    assert db.query(CommercialDelivery).count() == 1
    assert db.query(PartnerAccrual).one().amount == Decimal('200')
    delivery = db.query(CommercialDelivery).one()
    billing.complete_delivery(db, delivery.id, 'License delivered and accepted', setup.admin)
    for i, amount in enumerate(('590','590')):
        commerce.record_refund(db, event['id'], RefundRecord(source_event_key=f'test:refund:{i}', refund_reference=f'refund-{i}', amount=amount,
            tax_amount='90', occurred_at=growth.now(), reason='Verified test refund'), setup.admin.id)
    assert sum(a.amount for a in db.query(PartnerAccrual)) == 0
    assert delivery.status == 'revoked'
    assert db.get(CommercialInvoice, invoice['id']).status == 'refunded'


def test_recurring_billing_cannot_double_charge_period(db, setup):
    _, contract = agreement(db, setup, 'subscription')
    assert billing.run_billing(db)['invoices_issued'] == 1
    assert billing.run_billing(db)['invoices_issued'] == 0
    assert db.query(BillingOccurrence).count() == 1
    with pytest.raises(HTTPException): billing.issue(db, contract.id, 'invented-period', setup.admin.id)


def test_milestones_exhaust_exact_value(db, setup):
    _, contract = agreement(db, setup, 'milestone', '0.05')
    values = [billing.issue(db, contract.id, f'milestone-{i}', setup.admin.id, milestone_bps=bps)['subtotal'] for i,bps in enumerate((3333,3333,3334))]
    assert sum(Decimal(str(v)) for v in values) == Decimal('.05')
    with pytest.raises(HTTPException): billing.issue(db, contract.id, 'extra', setup.admin.id, milestone_bps=1)


def test_auth_and_tenant_isolation(client, db, setup, make_user, as_user):
    _, contract = agreement(db, setup)
    invoice = billing.issue(db, contract.id, 'first', setup.admin.id)
    from app.core.security import create_access_token
    student = make_user(role='student')
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(student.id)})
    assert client.get(ROOT+'/admin').status_code == 403
    assert client.post(f'{ROOT}/invoices/{invoice["id"]}/checkout').status_code == 403
    assert client.get(f'{ROOT}/invoices/{invoice["id"]}/document').status_code == 403
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(setup.owner.id)})
    assert client.get(ROOT+'/my-billing').json()['invoices'][0]['id'] == invoice['id']
    pdf = client.get(f'{ROOT}/invoices/{invoice["id"]}/document')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(setup.admin.id)})
    response = client.get(ROOT+'/admin')
    assert response.status_code == 200, response.text
    assert response.json()['analytics']['cac'] is None


def test_provider_capture_checks_amount_and_idempotency(db, setup):
    _, contract = agreement(db, setup)
    invoice = billing.issue(db, contract.id, 'first', setup.admin.id)
    row = db.get(CommercialInvoice, invoice['id']); row.gateway_order_id='order_verified'; db.commit()
    entity = {'id':'pay_verified','status':'captured','order_id':'order_verified','amount':118000,'currency':'INR'}
    with pytest.raises(HTTPException): billing.capture(db, row, {**entity, 'amount':1})
    with pytest.raises(HTTPException): billing.capture(db, row, {**entity, 'status':'authorized'})
    billing.capture(db, row, entity); billing.capture(db, row, entity)
    assert db.query(RevenueLedgerEvent).count() == 1


def test_timeout_does_not_create_duplicate_gateway_order(db, setup, monkeypatch):
    from unittest.mock import Mock
    _, contract=agreement(db,setup)
    invoice=billing.issue(db,contract.id,'first',setup.admin.id)
    client=Mock();client.order.create.side_effect=TimeoutError();client.order.all.return_value={'items':[]}
    monkeypatch.setattr(billing,'gateway',lambda:(client,'rzp_test_example','private-secret'))
    with pytest.raises(HTTPException): billing.checkout(db,invoice['id'],setup.owner)
    with pytest.raises(HTTPException): billing.checkout(db,invoice['id'],setup.owner)
    assert client.order.create.call_count == 1
    client.order.all.return_value={'items':[{'id':'order_recovered','receipt':f'commercial-{invoice["id"]}','amount':118000,'currency':'INR','notes':{'tenant_id':str(setup.tenant.id)}}]}
    assert billing.checkout(db,invoice['id'],setup.owner)['order_id'] == 'order_recovered'
    assert client.order.create.call_count == 1


def test_partner_settlement_hold_and_dedupe(db, setup):
    _, contract = agreement(db, setup)
    pay(db, setup, billing.issue(db, contract.id, 'first', setup.admin.id))
    cmd = SettlementCommand(partner_id=setup.partner.id, expected_amount=200, reference='bank-payout-001')
    with pytest.raises(HTTPException): billing.settle(db, cmd, setup.admin)
    db.query(PartnerAccrual).one().available_on = billing.today(); db.commit()
    first = billing.settle(db, cmd, setup.admin)
    assert billing.settle(db, cmd, setup.admin)['id'] == first['id']


def test_experiments_stable_assignment_and_mutually_exclusive_activation(db, setup):
    offer, _ = agreement(db, setup)
    command = ExperimentCommand(name='Price trial', kind='pricing', offer_id=offer['id'], minimum_sample=30,
        variants=[{'key':'control','headline':'Learn now','message':'Original offer','discount_bps':0}, {'key':'variant','headline':'Learn more','message':'Trial offer','discount_bps':1000}])
    first = growth.create_experiment(db, command, setup.admin)
    growth.experiment_status(db, first['id'], 'running', setup.admin)
    second = growth.create_experiment(db, command, setup.admin)
    with pytest.raises(HTTPException): growth.experiment_status(db, second['id'], 'running', setup.admin)
    q = growth.quote(db, offer['id'], setup.owner); db.commit()
    assert q == growth.quote(db, offer['id'], setup.owner)
    assert db.query(GrowthAssignment).count() == 1
    assert q['quoted_amount'] in (900,1000)
    result = growth.experiment_results(db, first['id'])
    assert result['decision'] == 'insufficient_data'
    assert sum(v['converted'] for v in result['results']) == 0


def test_lead_scoring_version_and_followup_dedupe(db, setup):
    lead = GrowthLead(tenant_id=setup.tenant.id,business_vertical='meiporul',name='Buyer',email='buyer@example.test',
        consent_at=growth.now(),next_follow_up=billing.today())
    db.add(lead); db.commit()
    cmd = LeadUpdate(version=1,stage='contacted',budget_confirmed=True,decision_maker=True,demo_attended=True,next_follow_up=billing.today())
    growth.update_lead(db, lead.id, cmd, setup.admin)
    assert lead.score == 100
    with pytest.raises(HTTPException): growth.update_lead(db, lead.id, cmd, setup.admin)
    growth.maintenance(db); growth.maintenance(db)
    assert lead.stage == 'qualified'
    assert db.query(GrowthTask).count() == 1
    with pytest.raises(HTTPException): growth.update_lead(db, lead.id, LeadUpdate(version=lead.version,stage='won'), setup.admin)


def test_pretenant_lead_can_link_workspace_with_version_check(client,db,setup,as_user):
    lead=GrowthLead(business_vertical='meiporul',name='New prospect',email='new@example.test',consent_at=growth.now())
    db.add(lead);db.commit();as_user(setup.admin)
    response=client.put(f'{ROOT}/leads/{lead.id}/workspace',json={'tenant_id':setup.tenant.id,'version':1})
    assert response.status_code == 200,response.text
    assert response.json()['tenant_id'] == setup.tenant.id
    assert client.put(f'{ROOT}/leads/{lead.id}/workspace',json={'tenant_id':setup.tenant.id,'version':1}).status_code == 409


def test_ai_rejects_untrusted_offer_and_keeps_prices(db, setup, monkeypatch):
    offer, _ = agreement(db, setup)
    from app.services import llm_provider
    monkeypatch.setattr(llm_provider,'llm_configured',lambda:True)
    monkeypatch.setattr(llm_provider,'call_glm',lambda *a,**k:'{"recommendations":[{"offer_id":9999,"kind":"pricing","reason":"Unverified suggestion","discount_bps":1000}]}')
    with pytest.raises(HTTPException): growth.recommend(db, setup.tenant.id, setup.admin)
    assert commerce.list_offers(db)[0]['unit_amount'] == offer['unit_amount']


def test_frozen_migration_roundtrip(tmp_path):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path=Path(__file__).parents[1]/'alembic/versions/0051_growth_commerce.py'
    spec=importlib.util.spec_from_file_location('growth_migration',path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    engine=create_engine('sqlite:///'+str(tmp_path/'growth.sqlite'))
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade(); module.upgrade()
            assert len([t for t in inspect(conn).get_table_names() if t.startswith('growth_')]) == 13
            module.downgrade()
            assert not inspect(conn).get_table_names()
    engine.dispose()


def test_paid_asset_expiry_cancellation_and_refund_preserve_other_access(db, setup, monkeypatch):
    from app.services import growth_fulfillment as access
    _, contract = agreement(db, setup, 'subscription')
    start = billing.today()
    invoice = billing.issue(db,contract.id,'cycle:'+start.isoformat(),setup.admin.id)
    event = pay(db,setup,invoice)
    delivery = db.query(CommercialDelivery).one()
    model_id = int(delivery.resource_reference)
    assert not access.asset_access(db,setup.owner.id,model_id)
    billing.complete_delivery(db,delivery.id,'Delivery accepted',setup.admin)
    assert access.asset_access(db,setup.owner.id,model_id)
    access.cancel_renewal(db,contract.id,'No renewal required',setup.owner)
    assert access.asset_access(db,setup.owner.id,model_id)
    assert billing.run_billing(db)['invoices_issued'] == 0
    expiry = delivery.valid_until
    monkeypatch.setattr(billing,'today',lambda:expiry)
    assert not access.asset_access(db,setup.owner.id,model_id)
    monkeypatch.setattr(billing,'today',lambda:start)
    commerce.record_refund(db,event['id'],RefundRecord(source_event_key='test:full-refund',refund_reference='full-refund',amount=1180,tax_amount=180,
        occurred_at=growth.now(),reason='Full test refund'),setup.admin.id)
    assert not access.asset_access(db,setup.owner.id,model_id)


def test_commercial_institution_plan_flows_into_existing_campus_access(db, setup):
    from app.models.institution import Institution
    from app.models.growth import BillingPolicy
    from app.services.campus_billing import effective_plan
    institution=Institution(name='Test campus',slug='growth-campus',academic_year='2026-27',tenant_id=setup.tenant.id)
    db.add(institution); db.commit()
    offer=commerce.create_offer(db,OfferCreate(sku='CAMPUS-PLAN',name='Campus plan',business_vertical='seyappaduporul',revenue_stream='institution_operations',billing_model='subscription',unit_amount=1000),setup.admin.id)
    contract=commerce.create_contract(db,ContractCreate(tenant_id=setup.tenant.id,offer_id=offer['id'],starts_on=billing.today(),billing_interval='monthly'),setup.admin.id)
    db.add(BillingPolicy(contract_id=contract['id'],resource_type='institution_saas',resource_reference='campus',created_by=setup.admin.id,
        tax_profile={'rate_bps':0,'supplier_state':'33','place_of_supply':'33'},partner_bps=0));db.commit()
    invoice=billing.issue(db,contract['id'],'cycle:'+billing.today().isoformat(),setup.admin.id)
    pay(db,setup,invoice)
    assert effective_plan(db,institution.id) == 'starter'
    billing.complete_delivery(db,db.query(CommercialDelivery).one().id,'Institution configured and accepted',setup.admin)
    assert effective_plan(db,institution.id) == 'campus'


def test_campus_capture_and_refund_feed_one_ledger(db, setup):
    from app.models.institution import Institution
    from app.models.campus_operations import CampusSubscription
    from app.services.growth_campus_ledger import record_charge
    from app.services.business_portfolio_service import consolidated_cash
    inst=Institution(name='Paid campus',slug='paid-campus',academic_year='2026-27',tenant_id=setup.tenant.id)
    db.add(inst);db.flush()
    sub=CampusSubscription(institution_id=inst.id,plan='campus',gateway_plan_id='plan_test',gateway_subscription_id='sub_test',status='active')
    db.add(sub);db.flush()
    through=growth.now()+timedelta(days=30);sub.paid_through=through
    payment={'id':'pay_campus_test','amount':10000,'currency':'INR','status':'captured'}
    assert record_charge(db,sub,payment,through)
    assert record_charge(db,sub,payment,through)
    db.commit()
    assert db.query(RevenueLedgerEvent).count() == 1
    assert consolidated_cash(db,billing.today(),billing.today())[0]['net_cash'] == 100
    billing.webhook_refund(db,{'id':'rfnd_campus_test','payment_id':'pay_campus_test','status':'processed','amount':10000})
    assert sub.paid_through is None
    assert consolidated_cash(db,billing.today(),billing.today())[0]['net_cash'] == 0
    assert record_charge(db,sub,payment,through) is False  # late charge replay must not revive refunded access


def test_approved_offer_publishing_respects_optin_and_price_snapshot(db, setup):
    from app.models.growth import GrowthRecommendation
    from app.models.communication_automation import CommunicationTopicPreference
    from app.models.notification import Notification
    offer,_=agreement(db,setup)
    rec=GrowthRecommendation(tenant_id=setup.tenant.id,generated_by=setup.admin.id,status='approved',payload={
        'recommendations':[{'offer_id':offer['id'],'kind':'cross_sell','reason':'Reviewed service recommendation','discount_bps':1000}],
        'base_prices':{str(offer['id']):'1000.00'}})
    db.add(rec);db.commit()
    assert growth.publish_recommendation(db,rec.id,setup.admin)['notified'] == 0
    db.add(CommunicationTopicPreference(user_id=setup.owner.id,topic='business_offers',in_app_enabled=True));db.commit()
    assert growth.publish_recommendation(db,rec.id,setup.admin)['notified'] == 1
    assert growth.publish_recommendation(db,rec.id,setup.admin)['notified'] == 0
    assert db.query(Notification).count() == 1
    contract=growth.accept_recommendation(db,rec.id,0,setup.owner)
    assert contract['unit_amount'] == 900
    assert growth.accept_recommendation(db,rec.id,0,setup.owner)['id'] == contract['id']
