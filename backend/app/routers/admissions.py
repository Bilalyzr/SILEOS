"""Institution admissions and learner lifecycle API.

Mount with ``prefix="/api/v1/institutions"`` so every route is rooted at
``/institutions/{institution_id}/admissions``.
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.admissions import (
    AdmissionsSummary,
    ApplicationCreate,
    ApplicationDetail,
    ApplicationPage,
    ApplicationStage,
    ApplicationUpdate,
    ConversionCreate,
    ConversionOut,
    DocumentCreate,
    DocumentUpdate,
    IntakeCreate,
    IntakeOut,
    IntakeUpdate,
    LearnerLifecycleUpdate,
    LearnerProfileOut,
    NoteCreate,
    OfferStatus,
    OfferUpdate,
    ProgramCreate,
    ProgramOut,
    ProgramUpdate,
    StageUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.services import admissions_service as service
from app.services.auth_service import AuthService


router = APIRouter()
CurrentUser = Depends(AuthService.get_current_active_user)


@router.get("/{institution_id}/admissions/summary", response_model=AdmissionsSummary)
def summary(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    """Compact, real-data admissions summary for the Campus Today surface."""
    return service.admissions_summary(db, institution_id, user)


@router.get("/{institution_id}/admissions/programs", response_model=list[ProgramOut])
def programs(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return service.list_programs(db, institution_id, user)


@router.post(
    "/{institution_id}/admissions/programs",
    response_model=ProgramOut,
    status_code=status.HTTP_201_CREATED,
)
def program_create(
    institution_id: int,
    data: ProgramCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_program(db, institution_id, user, data)


@router.patch(
    "/{institution_id}/admissions/programs/{program_id}",
    response_model=ProgramOut,
)
def program_update(
    institution_id: int,
    program_id: int,
    data: ProgramUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_program(db, institution_id, program_id, user, data)


@router.get("/{institution_id}/admissions/intakes", response_model=list[IntakeOut])
def intakes(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return service.list_intakes(db, institution_id, user)


@router.post(
    "/{institution_id}/admissions/intakes",
    response_model=IntakeOut,
    status_code=status.HTTP_201_CREATED,
)
def intake_create(
    institution_id: int,
    data: IntakeCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_intake(db, institution_id, user, data)


@router.patch(
    "/{institution_id}/admissions/intakes/{intake_id}", response_model=IntakeOut
)
def intake_update(
    institution_id: int,
    intake_id: int,
    data: IntakeUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_intake(db, institution_id, intake_id, user, data)


@router.get("/{institution_id}/admissions/applications", response_model=ApplicationPage)
def applications(
    institution_id: int,
    search: str = Query(default="", max_length=160),
    stage: ApplicationStage | None = None,
    offer_status: OfferStatus | None = None,
    intake_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.list_applications(
        db,
        institution_id,
        user,
        search=search,
        stage=stage,
        offer_status=offer_status,
        intake_id=intake_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{institution_id}/admissions/applications",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
)
def application_create(
    institution_id: int,
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_application(db, institution_id, user, data)


@router.get(
    "/{institution_id}/admissions/applications/{application_id}",
    response_model=ApplicationDetail,
)
def application_detail(
    institution_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.get_application(db, institution_id, application_id, user)


@router.patch(
    "/{institution_id}/admissions/applications/{application_id}",
    response_model=ApplicationDetail,
)
def application_update(
    institution_id: int,
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_application(db, institution_id, application_id, user, data)


@router.patch(
    "/{institution_id}/admissions/applications/{application_id}/stage",
    response_model=ApplicationDetail,
)
def application_stage(
    institution_id: int,
    application_id: int,
    data: StageUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.transition_stage(db, institution_id, application_id, user, data)


@router.post(
    "/{institution_id}/admissions/applications/{application_id}/documents",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
)
def document_create(
    institution_id: int,
    application_id: int,
    data: DocumentCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.add_document(db, institution_id, application_id, user, data)


@router.patch(
    "/{institution_id}/admissions/applications/{application_id}/documents/{document_id}",
    response_model=ApplicationDetail,
)
def document_update(
    institution_id: int,
    application_id: int,
    document_id: int,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_document(
        db, institution_id, application_id, document_id, user, data
    )


@router.post(
    "/{institution_id}/admissions/applications/{application_id}/notes",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
)
def note_create(
    institution_id: int,
    application_id: int,
    data: NoteCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.add_note(db, institution_id, application_id, user, data)


@router.post(
    "/{institution_id}/admissions/applications/{application_id}/tasks",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
)
def task_create(
    institution_id: int,
    application_id: int,
    data: TaskCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.add_task(db, institution_id, application_id, user, data)


@router.patch(
    "/{institution_id}/admissions/applications/{application_id}/tasks/{task_id}",
    response_model=ApplicationDetail,
)
def task_update(
    institution_id: int,
    application_id: int,
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_task(db, institution_id, application_id, task_id, user, data)


@router.put(
    "/{institution_id}/admissions/applications/{application_id}/offer",
    response_model=ApplicationDetail,
)
def offer_update(
    institution_id: int,
    application_id: int,
    data: OfferUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.update_offer(db, institution_id, application_id, user, data)


@router.get("/{institution_id}/admissions/applications/{application_id}/offer.pdf")
def offer_letter(
    institution_id: int,
    application_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    content = service.build_offer_pdf(db, institution_id, application_id, user)
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="admission-offer-{application_id}.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/{institution_id}/admissions/applications/{application_id}/convert",
    response_model=ConversionOut,
)
def application_convert(
    institution_id: int,
    application_id: int,
    data: ConversionCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.convert_application(db, institution_id, application_id, user, data)


@router.get(
    "/{institution_id}/admissions/learners", response_model=list[LearnerProfileOut]
)
def learners(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return service.list_learners(db, institution_id, user)


@router.get(
    "/{institution_id}/admissions/learners/{member_id}",
    response_model=LearnerProfileOut,
)
def learner_detail(
    institution_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.get_learner(db, institution_id, member_id, user)


@router.patch(
    "/{institution_id}/admissions/learners/{member_id}/lifecycle",
    response_model=LearnerProfileOut,
)
def learner_lifecycle(
    institution_id: int,
    member_id: int,
    data: LearnerLifecycleUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.transition_learner(db, institution_id, member_id, user, data)
