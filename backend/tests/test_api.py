"""
ReLoop End-to-End API Integration Tests
Tests health, authentication, device management, assessment submission,
decision engine pipeline, provider directory, and recovery tracking.
"""

import pytest
import httpx
import uuid
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
        test_email = f"tester-{uuid.uuid4().hex}@reloop.test"
        reg_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Test User",
            "city": "Austin",
            "role": "admin"
        })
        assert reg_res.status_code == 422

        reg_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": "Password123!",
            "full_name": "Test User",
            "city": "Austin"
        })
        assert reg_res.status_code == 201
        assert reg_res.json()["role"] == "user"

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
        admin_res = await client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
        assert admin_res.status_code == 403

@pytest.mark.anyio
async def test_oauth_form_authenticates_bootstrapped_admin():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        token_res = await client.post("/api/auth/token", data={
            "username": "admin@test.reloop",
            "password": "test-only-admin-password"
        })
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]
        stats_res = await client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
        assert stats_res.status_code == 200

@pytest.mark.anyio
async def test_full_device_recovery_workflow():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        test_email = f"journey-{uuid.uuid4().hex}@reloop.test"
        register_res = await client.post("/api/auth/register", json={
            "email": test_email,
            "password": "JourneyPassword123!",
            "full_name": "Journey User",
            "city": "Austin"
        })
        assert register_res.status_code == 201
        token = register_res.json()["access_token"]
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
            "specific_faults": ["battery_drain"],
            "notes": "Cosmetically clean, needs new OEM battery"
        })
        assert assess_res.status_code == 201
        rec = assess_res.json()
        assert rec["recommended_route"] == "Repair"
        repair_score = next(score for score in rec["scores"] if score["route"] == "Repair")
        weights = rec["weights_used"]
        weighted_total = sum(
            weights[key] * repair_score[field]
            for key, field in (
                ("financial", "financial_score"),
                ("useful_life", "useful_life_score"),
                ("convenience", "convenience_score"),
                ("reuse", "reuse_score"),
            )
        )
        assert rec["overall_score"] == pytest.approx(weighted_total, abs=0.01)
        estimates = rec["financial_summary"]
        assert estimates["estimated_repair_cost"] > 0
        assert estimates["estimated_resale_value"] > 0
        assert estimates["estimated_replacement_cost"] > 0
        assert estimates["expected_remaining_life_years"] > 0
        assert estimates["estimate_method"] == "category_age_condition_v1"
        assert set(estimates["estimate_sources"].values()) == {"ReLoop estimate"}
        assert estimates["matched_faults"] == ["battery"]
        assert estimates["estimate_ranges"]["estimated_repair_cost"]["high"] > estimates["estimate_ranges"]["estimated_repair_cost"]["low"]
        for field in [
            "estimated_repair_cost",
            "estimated_replacement_cost",
            "estimated_resale_value",
            "expected_remaining_life_years",
        ]:
            assert estimates["estimate_ranges"][field]["low"] <= estimates[field]
            assert estimates[field] <= estimates["estimate_ranges"][field]["high"]
        assessment_id = rec["assessment_id"]
        saved_assessments_res = await client.get("/api/assessments/my", headers=headers)
        assert saved_assessments_res.status_code == 200
        saved_assessment = next(item for item in saved_assessments_res.json() if item["id"] == assessment_id)
        assert saved_assessment["estimated_repair_cost"] == estimates["estimated_repair_cost"]
        assert saved_assessment["estimated_replacement_cost"] == estimates["estimated_replacement_cost"]
        saved_recommendation_res = await client.get(f"/api/recommendations/device/{device_id}", headers=headers)
        assert saved_recommendation_res.status_code == 200
        saved_estimates = saved_recommendation_res.json()["financial_summary"]
        assert saved_estimates["estimate_method"] == "category_age_condition_v1"
        assert saved_estimates["estimate_confidence"] == estimates["estimate_confidence"]
        assert saved_estimates["estimate_ranges"] == estimates["estimate_ranges"]

        # 4. Discover Providers for Repair
        prov_res = await client.get("/api/providers?category=Repair")
        assert prov_res.status_code == 200
        providers = prov_res.json()
        assert len(providers) >= 1
        selected_provider = providers[0]

        mismatched_provider_res = await client.post("/api/recovery", headers=headers, json={
            "device_id": device_id,
            "assessment_id": assessment_id,
            "selected_route": "Resell",
            "provider_id": selected_provider["id"]
        })
        assert mismatched_provider_res.status_code == 400

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

        # 6. Tracking details require authentication and ownership
        anonymous_track_res = await client.get(f"/api/recovery/track/{tracking_code}")
        assert anonymous_track_res.status_code == 401

        track_res = await client.get(f"/api/recovery/track/{tracking_code}", headers=headers)
        assert track_res.status_code == 200
        assert track_res.json()["tracking_code"] == tracking_code
        assert len(track_res.json()["status_history"]) >= 1
