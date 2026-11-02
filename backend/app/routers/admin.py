from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.user import User
from ..models.device import Device, DeviceCategory
from ..models.assessment import Assessment
from ..models.recommendation import Recommendation
from ..models.provider import ServiceProvider
from ..models.recovery import RecoveryRequest, RecoveryStatusHistory
from ..schemas.auth import UserProfileResponse
from ..schemas.provider import ProviderResponse
from ..schemas.recovery import RecoveryResponse
from ..utils.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin Management"])

@router.get("/stats")
def get_admin_dashboard_stats(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns platform operational KPIs and aggregations.
    STRICTLY OPERATIONAL DATA ONLY - No environmental or carbon statistics.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    total_assessments = db.query(func.count(Assessment.id)).scalar() or 0
    total_requests = db.query(func.count(RecoveryRequest.id)).scalar() or 0
    total_providers = db.query(func.count(ServiceProvider.id)).scalar() or 0

    # 1. Recovery requests grouped by operational status
    status_counts_raw = db.query(
        RecoveryRequest.current_status,
        func.count(RecoveryRequest.id)
    ).group_by(RecoveryRequest.current_status).all()

    all_statuses = [
        "Request Created",
        "Provider Selected",
        "Device Submitted / Collected",
        "Device Under Assessment",
        "Recovery in Progress",
        "Completed"
    ]
    status_dict = {st: 0 for st in all_statuses}
    for st, count in status_counts_raw:
        if st in status_dict:
            status_dict[st] = count
    recovery_by_status = [{"status": k, "count": v} for k, v in status_dict.items()]

    # 2. Devices grouped by category
    category_counts_raw = db.query(
        DeviceCategory.name,
        func.count(Device.id)
    ).outerjoin(Device, Device.category_id == DeviceCategory.id)\
     .group_by(DeviceCategory.name).all()

    devices_by_category = [{"category": name, "count": count} for name, count in category_counts_raw]

    # 3. Recommendations grouped by route
    routes_raw = db.query(
        Recommendation.recommended_route,
        func.count(Recommendation.id)
    ).group_by(Recommendation.recommended_route).all()

    all_routes = ["Repair", "Resell", "Donate", "Refurbish", "Recycle"]
    routes_dict = {r: 0 for r in all_routes}
    for r, count in routes_raw:
        if r in routes_dict:
            routes_dict[r] = count
    recommendations_by_route = [{"route": k, "count": v} for k, v in routes_dict.items()]

    # 4. Recent operational requests
    recent_requests = db.query(RecoveryRequest).order_by(RecoveryRequest.created_at.desc()).limit(5).all()
    recent_reqs_data = []
    for r in recent_requests:
        recent_reqs_data.append({
            "id": r.id,
            "tracking_code": r.tracking_code,
            "user_email": r.user.email if r.user else "Unknown",
            "device_name": r.device.name if r.device else "Unknown",
            "selected_route": r.selected_route,
            "current_status": r.current_status,
            "created_at": r.created_at
        })

    return {
        "kpis": {
            "total_users": total_users,
            "total_devices": total_devices,
            "total_assessments": total_assessments,
            "total_recovery_requests": total_requests,
            "total_service_providers": total_providers
        },
        "recovery_by_status": recovery_by_status,
        "devices_by_category": devices_by_category,
        "recommendations_by_route": recommendations_by_route,
        "recent_requests": recent_reqs_data
    }

@router.get("/users")
def get_all_users(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    results = []
    for u in users:
        device_count = db.query(func.count(Device.id)).filter(Device.user_id == u.id).scalar() or 0
        assessment_count = db.query(func.count(Assessment.id)).filter(Assessment.user_id == u.id).scalar() or 0
        results.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "city": u.city,
            "role": u.role,
            "device_count": device_count,
            "assessment_count": assessment_count,
            "created_at": u.created_at
        })
    return results

@router.get("/assessments")
def get_all_assessments(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    assessments = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
    results = []
    for a in assessments:
        rec = db.query(Recommendation).filter(Recommendation.assessment_id == a.id).first()
        results.append({
            "id": a.id,
            "user_email": a.user.email if a.user else "Unknown",
            "device_name": a.device.name if a.device else "Unknown",
            "category": a.device.category.name if (a.device and a.device.category) else "Unknown",
            "overall_condition": a.overall_condition,
            "functional_status": a.functional_status,
            "recommended_route": rec.recommended_route if rec else "Pending",
            "overall_score": rec.overall_score if rec else None,
            "created_at": a.created_at
        })
    return results

@router.get("/requests")
def get_all_recovery_requests(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    requests = db.query(RecoveryRequest).order_by(RecoveryRequest.created_at.desc()).all()
    results = []
    for r in requests:
        results.append({
            "id": r.id,
            "tracking_code": r.tracking_code,
            "user_email": r.user.email if r.user else "Unknown",
            "user_name": r.user.full_name if r.user else "Unknown",
            "device_name": r.device.name if r.device else "Unknown",
            "selected_route": r.selected_route,
            "provider_name": r.provider.name if r.provider else "Not Selected",
            "current_status": r.current_status,
            "created_at": r.created_at,
            "updated_at": r.updated_at
        })
    return results

@router.post("/providers/{provider_id}/toggle-verify")
def toggle_provider_verification(
    provider_id: str,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    provider.is_verified = not provider.is_verified
    db.commit()
    db.refresh(provider)
    return {
        "message": f"Provider verification status set to {provider.is_verified}",
        "is_verified": provider.is_verified
    }
