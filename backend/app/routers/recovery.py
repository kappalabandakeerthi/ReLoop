import uuid
import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.device import Device
from ..models.assessment import Assessment
from ..models.recommendation import Recommendation, RecommendationScore
from ..models.provider import ServiceProvider
from ..models.recovery import RecoveryRequest, RecoveryStatusHistory
from ..schemas.recovery import (
    RecoveryRequestCreate,
    RecoveryStatusUpdate,
    RecoveryResponse,
    StatusHistoryResponse
)
from ..utils.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/recovery", tags=["Recovery Tracking"])

def _generate_tracking_code() -> str:
    random_part = secrets.token_urlsafe(18).upper()
    return f"REL-{random_part}"

def _format_recovery_response(req: RecoveryRequest) -> RecoveryResponse:
    device = req.device
    provider = req.provider

    history_items = []
    for h in req.status_history:
        history_items.append(
            StatusHistoryResponse(
                id=h.id,
                recovery_request_id=h.recovery_request_id,
                status=h.status,
                notes=h.notes,
                updated_by_user_id=h.updated_by_user_id,
                updated_by_name=h.updated_by.full_name if h.updated_by else "System",
                created_at=h.created_at
            )
        )

    return RecoveryResponse(
        id=req.id,
        user_id=req.user_id,
        device_id=req.device_id,
        device_name=device.name if device else "Unknown Device",
        device_category=device.category.name if (device and device.category) else None,
        assessment_id=req.assessment_id,
        selected_route=req.selected_route,
        provider_id=req.provider_id,
        provider_name=provider.name if provider else None,
        provider_category=provider.category if provider else None,
        current_status=req.current_status,
        tracking_code=req.tracking_code,
        notes=req.notes,
        status_history=history_items,
        created_at=req.created_at,
        updated_at=req.updated_at
    )

@router.post("", response_model=RecoveryResponse, status_code=status.HTTP_201_CREATED)
def initiate_recovery_request(
    request_data: RecoveryRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate device
    device = db.query(Device).filter(Device.id == request_data.device_id).first()
    if not device or (device.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    # Validate assessment
    assessment = db.query(Assessment).filter(Assessment.id == request_data.assessment_id).first()
    if not assessment or assessment.device_id != device.id or assessment.user_id != device.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    recommendation = db.query(Recommendation).filter(
        Recommendation.assessment_id == assessment.id,
        Recommendation.device_id == device.id
    ).first()
    eligible_route = db.query(RecommendationScore).filter(
        RecommendationScore.recommendation_id == recommendation.id,
        RecommendationScore.route == request_data.selected_route,
        RecommendationScore.is_eligible.is_(True)
    ).first() if recommendation else None
    if not eligible_route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected route is not eligible for this assessment."
        )

    # Validate provider if provided
    initial_status = "Request Created"
    if request_data.provider_id:
        provider = db.query(ServiceProvider).filter(ServiceProvider.id == request_data.provider_id).first()
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected service provider not found.")
        if provider.category != request_data.selected_route:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected provider does not offer the chosen recovery route."
            )
        initial_status = "Provider Selected"

    tracking_code = _generate_tracking_code()
    # Ensure tracking code uniqueness
    while db.query(RecoveryRequest).filter(RecoveryRequest.tracking_code == tracking_code).first():
        tracking_code = _generate_tracking_code()

    new_request = RecoveryRequest(
        user_id=device.user_id,
        device_id=device.id,
        assessment_id=assessment.id,
        selected_route=request_data.selected_route,
        provider_id=request_data.provider_id,
        current_status=initial_status,
        tracking_code=tracking_code,
        notes=request_data.notes
    )
    db.add(new_request)
    db.flush()

    # Record initial status in history
    history_entry = RecoveryStatusHistory(
        recovery_request_id=new_request.id,
        status=initial_status,
        notes=f"Recovery request initialized for {request_data.selected_route} route.",
        updated_by_user_id=current_user.id
    )
    db.add(history_entry)
    db.commit()
    db.refresh(new_request)

    return _format_recovery_response(new_request)

@router.get("/my", response_model=List[RecoveryResponse])
def get_my_recovery_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = db.query(RecoveryRequest).filter(RecoveryRequest.user_id == current_user.id).order_by(RecoveryRequest.created_at.desc()).all()
    return [_format_recovery_response(r) for r in requests]

@router.get("/track/{tracking_code}", response_model=RecoveryResponse)
def track_by_code(
    tracking_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(RecoveryRequest).filter(RecoveryRequest.tracking_code == tracking_code.upper().strip()).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recovery request found with this tracking code.")
    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return _format_recovery_response(req)

@router.get("/{recovery_id}", response_model=RecoveryResponse)
def get_recovery_request_by_id(
    recovery_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = db.query(RecoveryRequest).filter(RecoveryRequest.id == recovery_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery request not found.")
    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return _format_recovery_response(req)

@router.put("/{recovery_id}/status", response_model=RecoveryResponse)
def update_recovery_status(
    recovery_id: str,
    status_update: RecoveryStatusUpdate,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    req = db.query(RecoveryRequest).filter(RecoveryRequest.id == recovery_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery request not found.")

    status_order = [
        "Request Created",
        "Provider Selected",
        "Device Submitted / Collected",
        "Device Under Assessment",
        "Recovery in Progress",
        "Completed",
    ]
    if status_order.index(status_update.status) <= status_order.index(req.current_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recovery status can only advance to a later stage."
        )

    req.current_status = status_update.status
    req.updated_at = datetime.utcnow()

    # Append to timeline history
    history = RecoveryStatusHistory(
        recovery_request_id=req.id,
        status=status_update.status,
        notes=status_update.notes or f"Status updated to '{status_update.status}' by administrator.",
        updated_by_user_id=admin_user.id
    )
    db.add(history)
    db.commit()
    db.refresh(req)

    return _format_recovery_response(req)
