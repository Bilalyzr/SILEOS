"""Role-gated source inputs, admin pricing and verified single-paper purchases."""
import hashlib
import hmac
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.exam_paper import ExamPaper, ExamPriceSlab
from app.models.payment import Payment, PaymentStatus
from app.schemas.exam_paper import SlabIn, PaperIn, PaperVerification
from app.services.auth_service import AuthService
from app.services import exam_paper_service as svc, llm_provider

router = APIRouter()
active = AuthService.get_current_active_user


def participant(user=Depends(active)):
    if user.role not in svc.STAFF | {'student'}:
        raise HTTPException(403, 'Student or teaching-staff access required.')
    return user


def staff_member(user=Depends(active)):
    if user.role not in svc.STAFF:
        raise HTTPException(403, 'Teaching-staff access required.')
    return user


@router.get('/pricing')
def pricing(db: Session = Depends(get_db), user=Depends(participant)):
    rows = db.query(ExamPriceSlab).filter_by(active=True, deleted=False).order_by(ExamPriceSlab.exam, ExamPriceSlab.min_questions).all()
    return {'slabs':[svc.slab_out(r) for r in rows], 'staff_access':user.role in svc.STAFF,
            'generation_available':llm_provider.llm_configured(), 'currency':'INR'}


@router.get('/admin/slabs')
def admin_slabs(db: Session = Depends(get_db), user=Depends(AuthService.require_admin)):
    return {'slabs':[svc.slab_out(r) for r in db.query(ExamPriceSlab).filter_by(deleted=False).order_by(ExamPriceSlab.exam, ExamPriceSlab.min_questions)]}


def save_slab(db, body, ident=None):
    # Claim the SQLite write lock before checking overlap, not after the read.
    if db.bind.dialect.name == 'postgresql': db.execute(text('SELECT pg_advisory_xact_lock(481927)'))
    elif db.bind.dialect.name == 'sqlite': db.execute(text('BEGIN IMMEDIATE'))
    row = db.get(ExamPriceSlab, ident) if ident else ExamPriceSlab()
    if ident and (not row or row.deleted): raise HTTPException(404, 'Pricing slab not found.')
    overlap = db.query(ExamPriceSlab).filter(ExamPriceSlab.exam == body.exam, ExamPriceSlab.deleted.is_(False),
               ExamPriceSlab.active.is_(True), ExamPriceSlab.min_questions <= body.max_questions, ExamPriceSlab.max_questions >= body.min_questions)
    if ident: overlap = overlap.filter(ExamPriceSlab.id != ident)
    if body.active and overlap.first(): raise HTTPException(409, 'An active slab already covers part of this question-count range.')
    for key, value in body.model_dump().items(): setattr(row, key, value.strip() if key == 'title' else value)
    if not row.title: raise HTTPException(422, 'Slab title is required.')
    db.add(row); db.commit(); db.refresh(row)
    return svc.slab_out(row)


@router.post('/admin/slabs', status_code=201)
def create_slab(body: SlabIn, db: Session = Depends(get_db), user=Depends(AuthService.require_admin)):
    return save_slab(db, body)


@router.put('/admin/slabs/{ident}')
def update_slab(ident: int, body: SlabIn, db: Session = Depends(get_db), user=Depends(AuthService.require_admin)):
    return save_slab(db, body, ident)


@router.delete('/admin/slabs/{ident}')
def delete_slab(ident: int, db: Session = Depends(get_db), user=Depends(AuthService.require_admin)):
    row = db.get(ExamPriceSlab, ident)
    if not row or row.deleted: raise HTTPException(404, 'Pricing slab not found.')
    row.active = False; row.deleted = True; db.commit()
    return {'deleted':True}


@router.post('/sources')
def source(file: UploadFile = File(...), user=Depends(staff_member)):
    try:
        content = file.file.read(10 * 1024 * 1024 + 1)
        extracted = svc.extract_source(content, file.filename or '')
        return {'text':extracted, 'characters':len(extracted), 'filename':file.filename}
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(422, 'This source file could not be read. Try a text PDF or paste the source.')
    finally:
        file.file.close()


@router.get('')
def papers(db: Session = Depends(get_db), user=Depends(participant)):
    recover_interrupted(db, user.id)
    rows = db.query(ExamPaper).filter_by(user_id=user.id).order_by(ExamPaper.created_at.desc()).limit(50).all()
    return {'papers':[svc.paper_out(r, detail=False) for r in rows]}


def recover_interrupted(db, user_id):
    changed = db.query(ExamPaper).filter(ExamPaper.user_id == user_id, ExamPaper.status == 'generating',
        ExamPaper.started_at < svc.now()-timedelta(minutes=60)).update(
        {'status':'failed', 'generation_id':None, 'error':'Generation was interrupted. Retry this paper without paying again.'}, synchronize_session=False)
    if changed: db.commit()


@router.post('', status_code=201)
def create_paper(body: PaperIn, db: Session = Depends(get_db), user=Depends(participant)):
    if not llm_provider.llm_configured(): raise HTTPException(503, 'Paper generation is temporarily unavailable. No payment has been taken.')
    staff = user.role in svc.STAFF
    if not staff and body.source_text: raise HTTPException(403, 'Source-document authoring is available to teaching staff.')
    slab = None
    if not staff:
        slab = db.query(ExamPriceSlab).filter_by(exam=body.exam, active=True, deleted=False).filter(
            ExamPriceSlab.min_questions <= body.count, ExamPriceSlab.max_questions >= body.count).first()
        if not slab: raise HTTPException(409, 'The admin has not enabled a price for this question count.')
    row = ExamPaper(id=str(uuid.uuid4()), user_id=user.id, slab_id=slab.id if slab else None, exam=body.exam,
                    title=f'{body.exam} · {body.topic.strip() or "Mixed practice"}'[:200], question_count=body.count,
                    input_json=body.model_dump(), amount_paise=slab.price_paise if slab else 0, status='ready' if staff else 'awaiting_payment')
    db.add(row); db.commit()
    try:
        if not staff:
            from app.routers.payments import _razorpay_client, _razorpay_creds
            client = _razorpay_client()
            order = client.order.create({'amount':row.amount_paise, 'currency':'INR', 'receipt':'ep-'+row.id[:32],
                                          'notes':{'exam_paper_id':row.id,'user_id':str(user.id)}})
            row.gateway_order_id = order['id']; db.commit()
            return {'paper':svc.paper_out(row), 'checkout':{'key':_razorpay_creds()[0], 'order_id':order['id'], 'amount':row.amount_paise, 'currency':'INR'}}
        return {'paper':svc.paper_out(row), 'checkout':None}
    except Exception:
        row.status='checkout_failed'; db.commit()
        raise HTTPException(503, 'Checkout could not start. No generation credit was consumed.')


@router.get('/{ident}')
def paper(ident: str, db: Session = Depends(get_db), user=Depends(participant)):
    recover_interrupted(db, user.id)
    return svc.paper_out(svc.owned(db, ident, user))


@router.post('/{ident}/verify')
def verify(ident: str, body: PaperVerification, db: Session = Depends(get_db), user=Depends(participant)):
    row = svc.owned(db, ident, user)
    if body.razorpay_order_id != row.gateway_order_id: raise HTTPException(400, 'Checkout does not belong to this paper.')
    from app.routers.payments import _razorpay_client, _razorpay_creds
    secret = _razorpay_creds()[1]
    expected = hmac.new(secret.encode(), f'{row.gateway_order_id}|{body.razorpay_payment_id}'.encode(), hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(expected, body.razorpay_signature): raise HTTPException(400, 'Invalid payment signature.')
    try:
        entity = _razorpay_client().payment.fetch(body.razorpay_payment_id)
        svc.fulfill_capture(db, row, entity); db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc))
    except IntegrityError:
        db.rollback(); raise HTTPException(409, 'Payment is being verified. Refresh this paper; do not pay again.')
    except Exception:
        db.rollback(); raise HTTPException(503, 'Payment verification is pending. Refresh this paper; do not pay again.')
    return svc.paper_out(row)


@router.post('/{ident}/reconcile')
def reconcile(ident: str, db: Session = Depends(get_db), user=Depends(participant)):
    row = svc.owned(db, ident, user)
    if row.status != 'awaiting_payment' or not row.gateway_order_id: return svc.paper_out(row)
    from app.routers.payments import _razorpay_client
    try:
        captures = _razorpay_client().order.payments(row.gateway_order_id).get('items', [])
        for entity in captures:
            if entity.get('status') == 'captured': svc.fulfill_capture(db, row, entity); db.commit(); break
    except Exception:
        db.rollback(); raise HTTPException(503, 'Payment status is temporarily unavailable. Do not pay again.')
    return svc.paper_out(row)


@router.post('/{ident}/generate', status_code=202)
def generate(ident: str, background: BackgroundTasks, db: Session = Depends(get_db), user=Depends(participant)):
    row = svc.owned(db, ident, user)
    if row.status == 'completed': return svc.paper_out(row)
    if row.amount_paise and (not row.gateway_payment_id or not db.query(Payment).filter_by(gateway_payment_id=row.gateway_payment_id, payment_status=PaymentStatus.COMPLETED).first()):
        raise HTTPException(402, 'A verified payment for this paper is required.')
    if row.status == 'generating' and row.started_at:
        started = row.started_at.replace(tzinfo=svc.now().tzinfo) if row.started_at.tzinfo is None else row.started_at
        if started < svc.now()-timedelta(minutes=60): row.status='failed'; db.commit()
    if row.status not in ('ready','failed'): raise HTTPException(409, 'Paper is already generating or is not available.')
    if not llm_provider.llm_configured(): raise HTTPException(503, 'Generation is temporarily unavailable. Your paid paper remains available.')
    generation_id = str(uuid.uuid4())
    changed = db.query(ExamPaper).filter(ExamPaper.id == ident, ExamPaper.status.in_(['ready','failed'])).update(
        {'status':'generating','started_at':svc.now(),'error':None,'generation_id':generation_id}, synchronize_session=False)
    if not changed: raise HTTPException(409, 'Generation already started.')
    db.commit(); db.refresh(row)
    background.add_task(svc.run_paper, ident, generation_id)
    return svc.paper_out(row)
