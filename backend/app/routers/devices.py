from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.device import Device, DeviceCategory
from ..schemas.device import (
    DeviceCreateRequest,
    DeviceUpdateRequest,
    DeviceResponse,
    CategoryResponse
)
from ..utils.dependencies import get_current_user

router = APIRouter(tags=["Devices"])

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(DeviceCategory).order_by(DeviceCategory.id).all()
    return categories

@router.get("/devices", response_model=List[DeviceResponse])
def get_my_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    devices = db.query(Device).filter(Device.user_id == current_user.id).order_by(Device.created_at.desc()).all()
    results = []
    for d in devices:
        res = DeviceResponse.model_validate(d)
        if d.category:
            res.category_name = d.category.name
        results.append(res)
    return results

@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    device_data: DeviceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(DeviceCategory).filter(DeviceCategory.id == device_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified device category does not exist."
        )

    # Compute approximate age if purchase year is given
    approx_age = device_data.approximate_age_years
    current_year = datetime.utcnow().year
    if approx_age is None and device_data.purchase_year:
        approx_age = max(0.0, float(current_year - device_data.purchase_year))

    new_device = Device(
        user_id=current_user.id,
        category_id=device_data.category_id,
        name=device_data.name,
        brand=device_data.brand,
        model=device_data.model,
        purchase_year=device_data.purchase_year,
        approximate_age_years=approx_age,
        working_condition=device_data.working_condition,
        fault_description=device_data.fault_description,
        powers_on=device_data.powers_on,
        physically_damaged=device_data.physically_damaged,
        contains_personal_data=device_data.contains_personal_data
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    res = DeviceResponse.model_validate(new_device)
    res.category_name = category.name
    return res

@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device_details(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    if device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    res = DeviceResponse.model_validate(device)
    if device.category:
        res.category_name = device.category.name
    return res

@router.put("/devices/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: str,
    update_data: DeviceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    if device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if update_data.category_id is not None:
        cat = db.query(DeviceCategory).filter(DeviceCategory.id == update_data.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
        device.category_id = update_data.category_id

    if update_data.name is not None:
        device.name = update_data.name
    if update_data.brand is not None:
        device.brand = update_data.brand
    if update_data.model is not None:
        device.model = update_data.model
    if update_data.purchase_year is not None:
        device.purchase_year = update_data.purchase_year
    if update_data.approximate_age_years is not None:
        device.approximate_age_years = update_data.approximate_age_years
    if update_data.working_condition is not None:
        device.working_condition = update_data.working_condition
    if update_data.fault_description is not None:
        device.fault_description = update_data.fault_description
    if update_data.powers_on is not None:
        device.powers_on = update_data.powers_on
    if update_data.physically_damaged is not None:
        device.physically_damaged = update_data.physically_damaged
    if update_data.contains_personal_data is not None:
        device.contains_personal_data = update_data.contains_personal_data

    db.commit()
    db.refresh(device)

    res = DeviceResponse.model_validate(device)
    if device.category:
        res.category_name = device.category.name
    return res

@router.delete("/devices/{device_id}", status_code=status.HTTP_200_OK)
def delete_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    if device.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully."}
