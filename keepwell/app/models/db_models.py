import datetime
import json
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.state_machine import JobState

class Agency(Base):
    __tablename__ = "agencies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    city = Column(String(50), default="Warangal")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    technicians = relationship("Technician", back_populates="agency")
    jobs = relationship("Job", back_populates="agency")

class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    skills = Column(String(200), default="REFRIGERATOR,AC")
    languages = Column(String(100), default="Telugu,Hindi,English")
    rating = Column(Float, default=4.8)
    active = Column(Boolean, default=True)
    
    agency = relationship("Agency", back_populates="technicians")
    assigned_jobs = relationship("Job", back_populates="technician")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), default="Household")
    language = Column(String(20), default="Telugu")
    address = Column(String(255), default="Warangal, Telangana")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    appliances = relationship("Appliance", back_populates="customer")
    jobs = relationship("Job", back_populates="customer")

class Appliance(Base):
    __tablename__ = "appliances"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    appliance_type = Column(String(50), default="REFRIGERATOR") # REFRIGERATOR, AC
    brand = Column(String(50), nullable=False)                 # LG, Samsung, Whirlpool, Voltas
    model_number = Column(String(100), index=True)
    serial_number = Column(String(100), index=True)
    purchase_year = Column(Integer, default=2022)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    customer = relationship("Customer", back_populates="appliances")
    jobs = relationship("Job", back_populates="appliance")
    service_events = relationship("ServiceEvent", back_populates="appliance", order_by="desc(ServiceEvent.event_date)")

class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=False) # COMPRESSOR, CAPACITOR, THERMOSTAT, GAS, RELAY
    price = Column(Float, nullable=False)
    in_stock = Column(Integer, default=10)
    compatible_models = Column(Text, default="[]") # JSON list of strings

    def is_compatible_with(self, model_number: str) -> bool:
        if not model_number:
            return False
        try:
            models = json.loads(self.compatible_models)
            return model_number in models or "*" in models
        except Exception:
            return False

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=True)
    
    state = Column(String(50), default=JobState.INTAKE_PENDING.value)
    raw_transcript = Column(Text, nullable=True)
    language = Column(String(20), default="te")
    symptom_category = Column(String(100), nullable=True)
    
    # Hazard & safety (deterministic)
    hazard_flag = Column(Boolean, default=False)
    hazard_summary = Column(Text, nullable=True)
    
    # Diagnostic outputs
    diagnostic_hypotheses = Column(Text, default="[]") # JSON list
    inspect_first = Column(Boolean, default=False)
    
    # Parts & Dispatch
    selected_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    parts_status = Column(String(50), default="NOT_CHECKED") # VERIFIED, UNKNOWN, INCOMPATIBLE, INSPECT_FIRST
    assigned_technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    scheduled_slot = Column(String(100), nullable=True)
    
    # Customer Magic Link
    magic_token = Column(String(64), unique=True, index=True)
    
    # Metric Tracking
    is_repeat = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    agency = relationship("Agency", back_populates="jobs")
    customer = relationship("Customer", back_populates="jobs")
    appliance = relationship("Appliance", back_populates="jobs")
    technician = relationship("Technician", back_populates="assigned_jobs")
    part = relationship("Part")
    quotes = relationship("Quote", back_populates="job")
    events = relationship("JobEvent", back_populates="job", order_by="JobEvent.timestamp")

class JobEvent(Base):
    __tablename__ = "job_events"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    from_state = Column(String(50))
    to_state = Column(String(50))
    actor = Column(String(50)) # SYSTEM, CUSTOMER, AGENCY, TECHNICIAN
    comment = Column(Text, nullable=True)
    payload = Column(Text, default="{}")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    job = relationship("Job", back_populates="events")

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    visiting_charge = Column(Float, default=250.0)
    labor_charge = Column(Float, default=300.0)
    parts_cost = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0) # 18% on labor + parts
    total_amount = Column(Float, default=550.0)
    
    agency_approved = Column(Boolean, default=False)
    customer_approved = Column(Boolean, default=False)
    payment_status = Column(String(30), default="PENDING") # PENDING, PAID
    upi_txn_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    job = relationship("Job", back_populates="quotes")

class ServiceEvent(Base):
    __tablename__ = "service_events"
    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    event_date = Column(DateTime, default=datetime.datetime.utcnow)
    technician_findings = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)
    customer_confirmed = Column(Boolean, default=True)
    first_visit_resolved = Column(Boolean, default=True)
    
    appliance = relationship("Appliance", back_populates="service_events")
