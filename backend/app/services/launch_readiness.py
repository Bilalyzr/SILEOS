"""Read-only readiness signals. Configured is never reported as end-to-end verified."""
import os
from pathlib import Path
from sqlalchemy import text
from app.core.config import get_settings


def report(db):
    settings=get_settings()
    from app.services.llm_provider import llm_configured
    from app.services.transcription_provider import configuration
    checks=[]
    def add(key,label,ready,detail):checks.append({'key':key,'label':label,'status':'configured' if ready else 'blocked','detail':detail})
    db.execute(text('SELECT 1'))
    add('database','Database connectivity',True,'Read query succeeded. Restore rehearsal is checked separately.')
    key=settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
    secret=settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
    add('payments','Razorpay credentials',bool(key and secret),'Credentials present; complete a real test-mode checkout before launch.' if key and secret else 'Configure Razorpay key and secret on the server.')
    add('webhook','Payment webhook',bool(settings.RAZORPAY_WEBHOOK_SECRET),'Webhook secret configured; delivery and signature tests still required.' if settings.RAZORPAY_WEBHOOK_SECRET else 'Configure the Razorpay webhook secret.')
    ai_ready = llm_configured()
    add('ai','AI question generation',ai_ready,'An active provider key is available; use the provider vault health check to verify connectivity.' if ai_ready else 'Add a GLM or Gemini key in Admin → AI Provider Vault.')
    stable=all(len(os.environ.get(k,'').strip())>=32 and not os.environ.get(k,'').startswith('your-') for k in ('SECRET_KEY','JWT_SECRET'))
    add('auth','Persistent signing keys',stable,'Environment keys present. Rotate through your deployment secret manager.' if stable else 'Set persistent SECRET_KEY and JWT_SECRET in deployment secrets.')
    root=Path(settings.UPLOAD_DIR)
    add('uploads','Upload storage',root.is_dir() and os.access(root,os.W_OK),'Upload directory exists and is writable.' if root.is_dir() and os.access(root,os.W_OK) else 'Create a writable uploads directory.')
    from app.models.exam_paper import ExamPriceSlab
    count=db.query(ExamPriceSlab).filter_by(active=True,deleted=False).count()
    add('pricing','Exam pricing slabs',count>0,f'{count} configured slabs. Admins control student pricing and publication.')
    return {'checks':checks,'transcription':configuration(),'note':'Configured means setup was detected. It does not certify live payments, AI output quality, production capacity, or physical AR/VR.'}
