"""
ReLoop Database Seed Script
Populates standard device categories, clearly labeled sample service providers,
and default test accounts (Administrator & Demo User).
"""

import json
from sqlalchemy.orm import Session
from ..database import engine, SessionLocal, Base
from ..models.user import User
from ..models.device import DeviceCategory, Device
from ..models.provider import ServiceProvider
from ..utils.security import get_password_hash

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # 1. Seed Device Categories
        categories_data = [
            {"name": "Laptop", "description": "Portable notebooks, ultrabooks, MacBooks, Chromebooks, and gaming laptops.", "icon": "laptop"},
            {"name": "Smartphone", "description": "iOS, Android, and mobile cellular handheld devices.", "icon": "smartphone"},
            {"name": "Tablet", "description": "iPads, Android tablets, e-readers, and graphics tablets.", "icon": "tablet"},
            {"name": "Monitor", "description": "External displays, LCD/OLED panels, and desktop computer screens.", "icon": "monitor"},
            {"name": "Desktop", "description": "Tower PCs, iMacs, Mac Minis, work stations, and all-in-one desktop units.", "icon": "cpu"},
            {"name": "Printer", "description": "Laser, inkjet, and multifunction office printers and scanners.", "icon": "printer"},
            {"name": "Charger", "description": "AC power adapters, charging bricks, USB-C docks, and power cables.", "icon": "zap"},
            {"name": "Other", "description": "Smart audio, wearables, gaming consoles, network routers, and misc electronics.", "icon": "box"},
        ]

        for cat_info in categories_data:
            existing = db.query(DeviceCategory).filter(DeviceCategory.name == cat_info["name"]).first()
            if not existing:
                cat = DeviceCategory(
                    name=cat_info["name"],
                    description=cat_info["description"],
                    icon=cat_info["icon"]
                )
                db.add(cat)
        db.commit()

        # 2. Seed Default Admin and User
        admin_email = "admin@reloop.dev"
        user_email = "user@reloop.dev"

        if not db.query(User).filter(User.email == admin_email).first():
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash("Admin@123456"),
                full_name="ReLoop Administrator",
                phone="+1 (555) 019-2831",
                address="701 Brazos St Suite 400",
                city="Austin",
                postal_code="78701",
                role="admin"
            )
            db.add(admin_user)

        if not db.query(User).filter(User.email == user_email).first():
            demo_user = User(
                email=user_email,
                hashed_password=get_password_hash("User@123456"),
                full_name="Alex Morgan",
                phone="+1 (555) 014-9922",
                address="1204 S Congress Ave",
                city="Austin",
                postal_code="78704",
                role="user"
            )
            db.add(demo_user)
        db.commit()

        # 3. Seed Clearly Labeled Sample Service Providers
        # IMPORTANT: Clearly labeled as sample/demo data to comply with accuracy guidelines.
        providers_data = [
            {
                "name": "Precision Tech Repair [Demo Service]",
                "category": "Repair",
                "address": "412 Congress Ave, Austin, TX",
                "city": "Austin",
                "contact_email": "austin-tech@demorepair.example.com",
                "contact_phone": "+1 (512) 555-0101",
                "website": "https://example.com/demo-repair-austin",
                "services_offered": ["Laptop Battery Replacement", "Screen Replacement", "Liquid Damage Cleaning", "Soldering & Port Repair"],
                "operating_hours": "Mon-Fri: 9:00 AM - 6:00 PM, Sat: 10:00 AM - 4:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.2662,
                "longitude": -97.7431,
                "rating": 4.8
            },
            {
                "name": "QuickFix Mobile & Laptop Hub [Demo Service]",
                "category": "Repair",
                "address": "1801 E 51st St, Austin, TX",
                "city": "Austin",
                "contact_email": "support@quickfixdemo.example.com",
                "contact_phone": "+1 (512) 555-0102",
                "website": "https://example.com/demo-quickfix",
                "services_offered": ["Smartphone Screen Diagnostics", "Battery Testing", "Diagnostic Assessment", "Tablet Digitizer Repair"],
                "operating_hours": "Mon-Sat: 10:00 AM - 7:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.3060,
                "longitude": -97.7120,
                "rating": 4.6
            },
            {
                "name": "NextLife Device Exchange [Demo Partner]",
                "category": "Resell",
                "address": "901 W 5th St, Austin, TX",
                "city": "Austin",
                "contact_email": "trade-in@nextlifedemo.example.com",
                "contact_phone": "+1 (512) 555-0103",
                "website": "https://example.com/demo-nextlife",
                "services_offered": ["Instant Direct Trade-In", "Direct Consumer Buyback", "Certified Pre-Owned Consignment"],
                "operating_hours": "Mon-Fri: 9:30 AM - 5:30 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.2701,
                "longitude": -97.7538,
                "rating": 4.7
            },
            {
                "name": "Digital Opportunity Youth Foundation [Demo Charity]",
                "category": "Donate",
                "address": "2201 S 1st St, Austin, TX",
                "city": "Austin",
                "contact_email": "donations@digitalopportunity.example.org",
                "contact_phone": "+1 (512) 555-0104",
                "website": "https://example.org/demo-digital-opportunity",
                "services_offered": ["Student Computer Program", "Charitable Tax Receipts", "Community Lab Equipment Intake"],
                "operating_hours": "Tue-Sat: 10:00 AM - 4:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.2465,
                "longitude": -97.7610,
                "rating": 4.9
            },
            {
                "name": "Apex Certified Refurbishing Lab [Demo Facility]",
                "category": "Refurbish",
                "address": "8101 Cameron Rd, Austin, TX",
                "city": "Austin",
                "contact_email": "intake@apexrefurbdemo.example.com",
                "contact_phone": "+1 (512) 555-0105",
                "website": "https://example.com/demo-apex-refurb",
                "services_offered": ["Factory Overhaul & Cleaning", "Component Recertification", "Thermal Paste & Fan Overhaul", "Enterprise Device Wiping"],
                "operating_hours": "Mon-Fri: 8:00 AM - 5:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.3420,
                "longitude": -97.6970,
                "rating": 4.7
            },
            {
                "name": "Metro E-Waste Recovery Depot [Demo Facility]",
                "category": "Recycle",
                "address": "3810 Todd Ln, Austin, TX",
                "city": "Austin",
                "contact_email": "depot@metroewastedemo.example.com",
                "contact_phone": "+1 (512) 555-0106",
                "website": "https://example.com/demo-metro-ewaste",
                "services_offered": ["Hazardous Battery Safe Disposal", "Certified Destruction", "Circuit Board Material Recovery", "Residential Drop-Off"],
                "operating_hours": "Mon-Sat: 8:00 AM - 4:30 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 30.2180,
                "longitude": -97.7340,
                "rating": 4.9
            },
            # Additional regional providers for diversity
            {
                "name": "Seattle Tech Restoration [Demo Service]",
                "category": "Repair",
                "address": "1402 3rd Ave, Seattle, WA",
                "city": "Seattle",
                "contact_email": "seattle@techrestoredemo.example.com",
                "contact_phone": "+1 (206) 555-0144",
                "website": "https://example.com/demo-seattle-repair",
                "services_offered": ["MacBook Logic Board Diagnostics", "Display Panel Replacement", "SSD Data Recovery"],
                "operating_hours": "Mon-Fri: 9:00 AM - 6:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 47.6080,
                "longitude": -122.3360,
                "rating": 4.8
            },
            {
                "name": "Pacific Recyclers E-Waste Center [Demo Facility]",
                "category": "Recycle",
                "address": "5200 1st Ave S, Seattle, WA",
                "city": "Seattle",
                "contact_email": "contact@pacificrecyclersdemo.example.com",
                "contact_phone": "+1 (206) 555-0199",
                "website": "https://example.com/demo-pacific-recycle",
                "services_offered": ["R2 Compliant Processing", "Heavy CRT/Monitor Recycling", "Lithium Battery Neutralization"],
                "operating_hours": "Mon-Fri: 8:00 AM - 4:00 PM",
                "is_verified": False,
                "is_sample": True,
                "latitude": 47.5550,
                "longitude": -122.3340,
                "rating": 4.7
            }
        ]

        for p_info in providers_data:
            existing = db.query(ServiceProvider).filter(ServiceProvider.name == p_info["name"]).first()
            if not existing:
                provider = ServiceProvider(
                    name=p_info["name"],
                    category=p_info["category"],
                    address=p_info["address"],
                    city=p_info["city"],
                    contact_email=p_info["contact_email"],
                    contact_phone=p_info["contact_phone"],
                    website=p_info["website"],
                    services_offered=json.dumps(p_info["services_offered"]),
                    operating_hours=p_info["operating_hours"],
                    is_verified=p_info["is_verified"],
                    is_sample=p_info["is_sample"],
                    latitude=p_info["latitude"],
                    longitude=p_info["longitude"],
                    rating=p_info["rating"]
                )
                db.add(provider)
        db.commit()

        print("[ReLoop Seed] Database initialized and seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"[ReLoop Seed] Error during seed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
