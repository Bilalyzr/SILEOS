"""Meiporul deployment and service-operations API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meiporul_operations import DeviceCreate, DeviceUpdate, InspectionCreate, MilestoneCreate, MilestoneUpdate, SiteCreate, SiteUpdate, TicketCreate, TicketUpdate
from app.services import meiporul_operations_service as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.get("/sites")
def sites(tenant_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.list_sites(db, user, tenant_id=tenant_id)


@router.post("/sites", status_code=201)
def create_site(command: SiteCreate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.create_site(db, command, user)


@router.get("/sites/{site_id}")
def site(site_id: int, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.get_site(db, site_id, user)


@router.patch("/sites/{site_id}")
def update_site(site_id: int, command: SiteUpdate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.update_site(db, site_id, command, user)


@router.post("/sites/{site_id}/devices", status_code=201)
def add_device(site_id: int, command: DeviceCreate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.add_device(db, site_id, command, user)


@router.patch("/devices/{device_id}")
def update_device(device_id: int, command: DeviceUpdate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.update_device(db, device_id, command, user)


@router.post("/sites/{site_id}/inspections", status_code=201)
def add_inspection(site_id: int, command: InspectionCreate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.add_inspection(db, site_id, command, user)


@router.post("/sites/{site_id}/milestones", status_code=201)
def add_milestone(site_id: int, command: MilestoneCreate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.add_milestone(db, site_id, command, user)


@router.patch("/milestones/{milestone_id}")
def update_milestone(milestone_id: int, command: MilestoneUpdate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.update_milestone(db, milestone_id, command, user)


@router.post("/sites/{site_id}/tickets", status_code=201)
def create_ticket(site_id: int, command: TicketCreate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.create_ticket(db, site_id, command, user)


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, command: TicketUpdate, db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.update_ticket(db, ticket_id, command, user)
