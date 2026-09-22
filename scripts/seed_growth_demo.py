"""Synthetic Growth OS scenarios, called only by the isolated SaaS demo seeder."""
from datetime import timedelta
from decimal import Decimal


def seed_growth(db, admin, owner, partner, tenant_id):
    from app.core.config import get_settings
    if 'saas-demo' not in str(get_settings().DATABASE_URL) or get_settings().ENVIRONMENT == 'production':
        raise RuntimeError('Growth demo fixtures are restricted to the isolated saas-demo database')
    from app.models.commercial import CommercialOffer, CommercialContract
    from app.models.growth import GrowthLead, GrowthValidation, GrowthExperiment, PartnerAccrual, MarketingSpend
    from app.schemas.commercial import OfferCreate, ContractCreate, PaymentRecord
    from app.schemas.growth import PolicyCommand, ExperimentCommand
    from app.services import commercial_service as commerce, growth_billing as billing, growth_service as growth
    from app.models.three_d import ThreeDModel
    from app.models.growth import CommercialDelivery
    asset = db.query(ThreeDModel).order_by(ThreeDModel.id).first()
    today = billing.today()
    for index, (kind, (vertical, stream)) in enumerate(billing.RESOURCE_STREAMS.items()):
        sku = 'DEMO-GROWTH-' + kind.upper()
        existing = db.query(CommercialOffer).filter_by(sku=sku).first()
        old_contract = db.query(CommercialContract).filter_by(offer_id=existing.id).first() if existing else None
        if old_contract:
            # Repair only known synthetic showroom references from an earlier seed.
            from app.models.growth import BillingPolicy, BillingOccurrence
            reference = str(asset.id) if kind == 'asset_license' and asset else 'campus' if kind == 'institution_saas' else None
            if reference and (old_contract.terms or {}).get('synthetic'):
                policy = db.get(BillingPolicy,old_contract.id)
                if policy:
                    policy.resource_reference = reference
                for occurrence in db.query(BillingOccurrence).filter_by(contract_id=old_contract.id):
                    occurrence.snapshot = {**occurrence.snapshot,'resource_reference':reference}
                    delivery = db.query(CommercialDelivery).filter_by(invoice_id=occurrence.invoice_id).first()
                    if delivery:
                        delivery.resource_reference = reference
                        if delivery.status == 'pending':
                            billing.complete_delivery(db,delivery.id,'Synthetic demo fulfillment scenario',admin)
                db.commit()
            continue
        recurring = kind in {'amc', 'institution_saas', 'franchise', 'managed_service'}
        offer = {'id':existing.id} if existing else commerce.create_offer(db, OfferCreate(sku=sku, business_vertical=vertical, revenue_stream=stream,
            name='Demo · ' + kind.replace('_',' ').title(), description='Synthetic showroom service. Not a live purchasable offer.',
            billing_model='subscription' if recurring else 'milestone' if kind=='lab_deployment' else 'one_time',
            unit_amount=Decimal(1000 + index*1500)), admin.id)
        contract = commerce.create_contract(db, ContractCreate(tenant_id=tenant_id, offer_id=offer['id'], starts_on=today,
            billing_interval='monthly' if recurring else None, terms={'synthetic':True,
            'attribution':{'last_touch':{'source':'demo-search','campaign':'three-pillars-demo'}}}), admin.id)
        reference = str(asset.id) if kind == 'asset_license' and asset else 'campus' if kind == 'institution_saas' else f'DEMO-SERVICE-{index+1}'
        billing.set_policy(db, contract['id'], PolicyCommand(resource_type=kind,resource_reference=reference,
            partner_id=partner.id if kind=='creator_commerce' else None,partner_bps=2000 if kind=='creator_commerce' else 0,
            automation_enabled=recurring, tax_profile={'supplier_name':'SashaInfinity DEMO ONLY','supplier_address':'Synthetic Chennai address',
                'supplier_state':'33','customer_name':'Demo Academy','customer_address':'Synthetic academy address','place_of_supply':'33',
                'hsn_sac':'9992','rate_bps':0,'exemption_reason':'Synthetic fixture only; NOT a production tax determination','reviewed_by':'Demo fixture'}), admin)
        invoice = billing.issue(db, contract['id'], 'cycle:'+today.isoformat() if recurring else 'demo-initial', admin.id)
        if index % 2 == 0 or kind=='creator_commerce':
            commerce.record_payment(db, invoice['id'], PaymentRecord(source_event_key=f'synthetic:growth:{invoice["id"]}',
                payment_reference='DEMO-NOT-A-REAL-PAYMENT',occurred_at=growth.now(),reason='Synthetic showroom scenario only',metadata={'synthetic':True}),admin.id)
            if kind == 'asset_license' and asset:
                delivery = db.query(CommercialDelivery).filter_by(invoice_id=invoice['id']).one()
                billing.complete_delivery(db,delivery.id,'Synthetic demo asset access scenario',admin)
    if not db.query(GrowthLead).filter_by(source='synthetic-demo').first():
        for i, (vertical, stage, score) in enumerate([('meiporul','new',0),('seyappaduporul','contacted',30),('utporul','qualified',70),('meiporul','proposal',100)]):
            db.add(GrowthLead(tenant_id=tenant_id,user_id=owner.id,business_vertical=vertical,name=f'Demo buyer {i+1}',
                email=f'growth-demo-{i+1}@example.org',company=f'Synthetic academy {i+1}',source='synthetic-demo',campaign='three-pillars-demo',
                stage=stage,score=score,expected_amount=(i+1)*25000,consent_at=growth.now(),next_follow_up=today,
                signals={'budget_confirmed':score>=30,'decision_maker':score>=70,'demo_attended':score==100}))
    if not db.query(MarketingSpend).filter_by(source_key='synthetic-growth-spend').first():
        db.add(MarketingSpend(source_key='synthetic-growth-spend',source='demo-search',campaign='three-pillars-demo',
            business_vertical='meiporul',incurred_on=today,amount=2500,currency='INR'))
    if not db.query(GrowthValidation).filter_by(release_ref='synthetic-demo-only').first():
        for area in ['payments','ai','tax','postgres_restore','worker_failover','load']:
            db.add(GrowthValidation(area=area,environment='local',status='blocked',evidence='Synthetic demo fixture. Real acceptance evidence has not been supplied.',
                release_ref='synthetic-demo-only',recorded_by=admin.id))
    db.commit()
    if not db.query(GrowthExperiment).first():
        offer = db.query(CommercialOffer).filter_by(sku='DEMO-GROWTH-ASSET_LICENSE').one()
        experiment = growth.create_experiment(db, ExperimentCommand(name='Demo immersive offer copy',kind='landing',offer_id=offer.id,
            variants=[{'key':'control','headline':'Explore immersive learning','message':'Bring curriculum to life.'},
                {'key':'variant','headline':'Make learning experiential','message':'Give every learner a new perspective.'}]),admin)
        growth.experiment_status(db,experiment['id'],'running',admin)
    growth.maintenance(db)
