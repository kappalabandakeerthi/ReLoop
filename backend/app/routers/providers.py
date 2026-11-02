import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.provider import ServiceProvider
from ..schemas.provider import (
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ProviderResponse
)
from ..utils.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/providers", tags=["Service Providers"])

def _format_provider(p: ServiceProvider) -> ProviderResponse:
    res = ProviderResponse.from_orm(p)
    res.services_offered = p.get_services()
    return res

@router.get("", response_model=List[ProviderResponse])
def get_providers(
    category: Optional[str] = Query(None, description="Filter by category: Repair, Resell, Donate, Refurbish, Recycle"),
    city: Optional[str] = Query(None, description="Filter by city"),
    verified_only: Optional[bool] = Query(False, description="Filter only verified providers"),
    search: Optional[str] = Query(None, description="Search by name, address, or service keywords"),
    db: Session = Depends(get_db)
):
    query = db.query(ServiceProvider)

    if category:
        query = query.filter(ServiceProvider.category == category)
    if city:
        query = query.filter(ServiceProvider.city.ilike(f"%{city}%"))
    if verified_only:
        query = query.filter(ServiceProvider.is_verified == True)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (ServiceProvider.name.ilike(search_pattern)) |
            (ServiceProvider.address.ilike(search_pattern)) |
            (ServiceProvider.services_offered.ilike(search_pattern))
        )

    providers = query.order_by(ServiceProvider.rating.desc(), ServiceProvider.name).all()
    return [_format_provider(p) for p in providers]

@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider_details(provider_id: str, db: Session = Depends(get_db)):
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service provider not found.")
    return _format_provider(provider)

@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(
    provider_data: ProviderCreateRequest,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    new_provider = ServiceProvider(
        name=provider_data.name,
        category=provider_data.category,
        address=provider_data.address,
        city=provider_data.city,
        contact_email=provider_data.contact_email,
        contact_phone=provider_data.contact_phone,
        website=provider_data.website,
        services_offered=json.dumps(provider_data.services_offered),
        operating_hours=provider_data.operating_hours,
        is_verified=provider_data.is_verified,
        is_sample=provider_data.is_sample,
        latitude=provider_data.latitude,
        longitude=provider_data.longitude,
        rating=provider_data.rating or 4.5
    )
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    return _format_provider(new_provider)

@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str,
    update_data: ProviderUpdateRequest,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service provider not found.")

    if update_data.name is not None:
        provider.name = update_data.name
    if update_data.category is not None:
        provider.category = update_data.category
    if update_data.address is not None:
        provider.address = update_data.address
    if update_data.city is not None:
        provider.city = update_data.city
    if update_data.contact_email is not None:
        provider.contact_email = update_data.contact_email
    if update_data.contact_phone is not None:
        provider.contact_phone = update_data.contact_phone
    if update_data.website is not None:
        provider.website = update_data.website
    if update_data.services_offered is not None:
        provider.services_offered = json.dumps(update_data.services_offered)
    if update_data.operating_hours is not None:
        provider.operating_hours = update_data.operating_hours
    if update_data.is_verified is not None:
        provider.is_verified = update_data.is_verified
    if update_data.is_sample is not None:
        provider.is_sample = update_data.is_sample
    if update_data.latitude is not None:
        provider.latitude = update_data.latitude
    if update_data.longitude is not None:
        provider.longitude = update_data.longitude
    if update_data.rating is not None:
        provider.rating = update_data.rating

    db.commit()
    db.refresh(provider)
    return _format_provider(provider)

@router.delete("/{provider_id}", status_code=status.HTTP_200_OK)
def delete_provider(
    provider_id: str,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service provider not found.")
    db.delete(provider)
    db.commit()
    return {"message": "Service provider deleted successfully."}
