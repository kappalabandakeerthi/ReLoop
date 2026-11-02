"""
ReLoop End-to-End API Integration Tests
Tests health, authentication, device management, assessment submission,
decision engine pipeline, provider directory, and recovery tracking.
"""

import pytest
import httpx
from app.main import app

@pytest.mark.anyio
async def test_health_check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

@pytest.mark.anyio
async def test_auth_workflow():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        test_email = "tester_unique_flow@reloop.dev"
        # 1. Register or check existing
        reg_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Test User",
            "city": "Austin"
        })
        assert reg_res.status_code in [201, 400]

        # 2. Login
        login_res = await client.post("/api/auth/login", json={
            "email": test_email,
            "password": "Password123!"
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        token = data["access_token"]

        # 3. Access /me
        me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == test_email

@pytest.mark.anyio
async def test_full_device_recovery_workflow():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login as demo user
        login_res = await client.post("/api/auth/login", json={
            "email": "user@reloop.dev",
            "password": "User@123456"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch categories
        cat_res = await client.get("/api/categories")
        assert cat_res.status_code == 200
        categories = cat_res.json()
        assert len(categories) >= 8
        laptop_cat = next(c for c in categories if c["name"] == "Laptop")

        # 2. Add device (Laptop with battery fault)
        dev_res = await client.post("/api/devices", headers=headers, json={
            "category_id": laptop_cat["id"],
            "name": "ThinkPad T14",
            "brand": "Lenovo",
            "model": "T14 Gen 2",
            "purchase_year": 2021,
            "approximate_age_years": 3.0,
            "working_condition": "minor_issues",
            "fault_description": "Battery degrades rapidly",
            "powers_on": True,
            "physically_damaged": False,
            "contains_personal_data": True
        })
        assert dev_res.status_code == 201
        device_id = dev_res.json()["id"]

        # 3. Submit Assessment
        assess_res = await client.post("/api/assessments", headers=headers, json={
            "device_id": device_id,
            "overall_condition": "good",
            "functional_status": "partially_functional",
            "specific_faults": ["battery_drain", "internal_wear"],
            "estimated_repair_cost": 80.0,
            "estimated_resale_value": 450.0,
            "estimated_replacement_cost": 950.0,
            "expected_remaining_life_years": 3.5,
            "notes": "Cosmetically clean, needs new OEM battery"
        })
        assert assess_res.status_code == 201
        rec = assess_res.json()
        assert rec["recommended_route"] == "Repair"
        assert rec["overall_score"] > 65.0
        assessment_id = rec["assessment_id"]

        # 4. Discover Providers for Repair
        prov_res = await client.get("/api/providers?category=Repair")
        assert prov_res.status_code == 200
        providers = prov_res.json()
        assert len(providers) >= 1
        selected_provider = providers[0]

        # 5. Initiate Recovery Request
        recov_res = await client.post("/api/recovery", headers=headers, json={
            "device_id": device_id,
            "assessment_id": assessment_id,
            "selected_route": "Repair",
            "provider_id": selected_provider["id"],
            "notes": "Booked battery replacement with demo technician"
        })
        assert recov_res.status_code == 201
        recovery_data = recov_res.json()
        assert recovery_data["current_status"] == "Provider Selected"
        assert recovery_data["tracking_code"].startswith("REL-")
        tracking_code = recovery_data["tracking_code"]

        # 6. Track by Tracking Code
        track_res = await client.get(f"/api/recovery/track/{tracking_code}")
        assert track_res.status_code == 200
        assert track_res.json()["tracking_code"] == tracking_code
        assert len(track_res.json()["status_history"]) >= 1
