"""Admin-only operations dashboard and uniform listing/export contract."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.listing import paginate, csv_stream
from app.services import operations_service as svc
from app.services.business_portfolio_service import business_today as _business_today
from app.services.auth_service import AuthService

router = APIRouter(dependencies=[Depends(AuthService.require_admin)])


@router.get('/runtime')
def runtime_status(db: Session = Depends(get_db)):
    from app.services.runtime_service import snapshot
    from app.core.config import get_settings
    result = snapshot(db)
    result['mode'] = get_settings().BACKGROUND_TASK_MODE
    return result


@router.get('/telemetry')
async def runtime_telemetry():
    from app.core.runtime_telemetry import telemetry
    return await telemetry.snapshot()


@router.post('/runtime/{name}/retry')
def retry_runtime(name: str, db: Session = Depends(get_db), actor=Depends(AuthService.require_admin)):
    from app.services.runtime_service import request_retry
    return request_retry(db, name, actor)


@router.get('/readiness')
def readiness(db: Session = Depends(get_db)):
    from app.services.launch_readiness import report
    return report(db)


@router.post('/readiness/probe/{provider}')
def provider_probe(provider: str):
    if provider == 'ai':
        from app.services.llm_provider import llm_configured, call_glm
        if not llm_configured(): raise HTTPException(503,'AI provider is not configured.')
        try:
            answer=call_glm('You are a connectivity check. Reply with the word ready.',
                            'Connectivity check', max_tokens=10, feature="AI readiness probe")
            if not answer.strip():raise ValueError('Empty response')
            return {'status':'verified','detail':'AI provider returned a nonempty response. Educational output quality still requires review.'}
        except Exception:
            raise HTTPException(502,'AI connectivity check failed. Inspect server provider configuration.') from None
    if provider == 'payments':
        from app.core.config import get_settings
        import httpx
        settings=get_settings()
        key=settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
        secret=settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
        if not key or not secret:raise HTTPException(503,'Razorpay is not configured.')
        try:
            response=httpx.get('https://api.razorpay.com/v1/orders',params={'count':1},auth=(key,secret),timeout=15)
            response.raise_for_status()
            return {'status':'verified','detail':'Razorpay authenticated a read-only request. Checkout and webhook delivery still need a test-mode payment.'}
        except Exception:
            raise HTTPException(502,'Razorpay connectivity check failed. Check server credentials.') from None
    raise HTTPException(404,'Unknown provider.')


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return {"queues": svc.queues(db), "outcomes": svc.outcomes(db), "health": svc.health(db), "as_of": svc.now()}


@router.get("/revenue")
def revenue(start: date = Query(default_factory=lambda: _business_today() - timedelta(days=30)), end: date = Query(default_factory=lambda: _business_today()), db: Session = Depends(get_db)):
    if end < start or (end - start).days > 366:
        raise HTTPException(422, "Choose a date window of at most 366 days.")
    return svc.revenue(db, start, end)


@router.get("/portfolio")
def portfolio(start: date = Query(default_factory=lambda: _business_today() - timedelta(days=30)), end: date = Query(default_factory=lambda: _business_today()), db: Session = Depends(get_db)):
    if end < start or (end - start).days > 366:
        raise HTTPException(422, "Choose a date window of at most 366 days.")
    from app.services.business_portfolio_service import portfolio as build_portfolio

    return build_portfolio(db, start, end)


@router.get("/lists/{dataset}")
def rows(dataset: str, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), sort: str = "created", order: str = "desc", q: str = Query("", max_length=200), status: str = Query("", max_length=30), db: Session = Depends(get_db)):
    try:
        query, sorts, tie, serialize = svc.listing_query(db, dataset, q, status)
        items, info = paginate(query, page, page_size, sort, order, sorts, tie)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"items": [serialize(r) for r in items], **info}


@router.get("/lists/{dataset}/export.csv")
def export(dataset: str, sort: str = "created", order: str = "desc", q: str = Query("", max_length=200), status: str = Query("", max_length=30), db: Session = Depends(get_db)):
    try:
        query, sorts, tie, serialize = svc.listing_query(db, dataset, q, status)
        if sort not in sorts or order not in ("asc", "desc"): raise ValueError("Invalid sort.")
        query = query.order_by(sorts[sort].desc() if order == "desc" else sorts[sort].asc(), tie.asc())
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    # Materialize bounded batches while the request session remains open. No arbitrary table export.
    if query.count() > 100000: raise HTTPException(422, "Narrow the filters to at most 100,000 rows.")
    data = [serialize(r) for r in query.yield_per(500)]
    return StreamingResponse(csv_stream(data, ["id", "name", "detail", "status", "created", "amount"]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{dataset}.csv"', "Cache-Control": "no-store"})
