import json
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.db_models import Agency, Technician, Customer, Appliance, Part, ServiceEvent, Job

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def seed_database():
    db = SessionLocal()
    try:
        # 1. Seed Agency if empty
        agency = db.query(Agency).first()
        if not agency:
            agency = Agency(
                name="Sri Laxmi Cool Services",
                phone="+919848099887",
                city="Warangal",
                active=True
            )
            db.add(agency)
            db.commit()
            db.refresh(agency)
            print(f"[Seed] Created Agency: {agency.name} (ID: {agency.id})")

        # 2. Seed Technicians
        if db.query(Technician).count() == 0:
            techs = [
                Technician(agency_id=agency.id, name="K. Ravi Kumar", phone="+919848111222", skills="REFRIGERATOR,AC", languages="Telugu,Hindi", rating=4.9),
                Technician(agency_id=agency.id, name="Md. Shakeel", phone="+919848222333", skills="REFRIGERATOR", languages="Telugu,Hindi,English", rating=4.7),
                Technician(agency_id=agency.id, name="P. Srinivas", phone="+919848333444", skills="AC", languages="Telugu", rating=4.8)
            ]
            db.add_all(techs)
            db.commit()
            print("[Seed] Created 3 Technicians")

        # 3. Seed Parts
        if db.query(Part).count() == 0:
            with open(os.path.join(FIXTURES_DIR, "parts_catalogue.json"), "r") as f:
                parts_data = json.load(f)
            for p in parts_data:
                part = Part(
                    code=p["code"],
                    name=p["name"],
                    category=p["category"],
                    price=p["price"],
                    in_stock=p["in_stock"],
                    compatible_models=json.dumps(p["compatible_models"])
                )
                db.add(part)
            db.commit()
            print(f"[Seed] Created {len(parts_data)} Spare Parts")

        # 4. Seed Customers & Appliances
        if db.query(Customer).count() == 0:
            with open(os.path.join(FIXTURES_DIR, "appliances_seed.json"), "r") as f:
                appliances_data = json.load(f)
            for item in appliances_data:
                cust = Customer(
                    phone=item["customer_phone"],
                    name=item["customer_name"],
                    language=item["customer_language"],
                    address=item["customer_address"]
                )
                db.add(cust)
                db.flush()
                
                appliance = Appliance(
                    customer_id=cust.id,
                    appliance_type=item["appliance_type"],
                    brand=item["brand"],
                    model_number=item["model_number"],
                    serial_number=item["serial_number"],
                    purchase_year=item["purchase_year"],
                    is_verified=item["is_verified"]
                )
                db.add(appliance)
                db.flush()

                # Add a verified prior service event for Ramesh Varma's LG fridge (2 months ago)
                if item["model_number"] == "GL-B201ABPY":
                    event = ServiceEvent(
                        appliance_id=appliance.id,
                        job_id=1,
                        technician_findings="Defrost timer contact stuck open. Cabinet temperature at 14 deg C.",
                        action_taken="Replaced defrost bi-metal sensor and cleaned condenser coil.",
                        customer_confirmed=True,
                        first_visit_resolved=True
                    )
                    db.add(event)

            db.commit()
            print(f"[Seed] Created {len(appliances_data)} Customers with Seed Appliances")

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed_database()
