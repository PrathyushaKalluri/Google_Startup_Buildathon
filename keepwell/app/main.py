import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import get_db, init_db
from app.config import settings
from app.api import routes_whatsapp, routes_jobs, routes_quotes, routes_appliances, routes_technicians
from app.models.db_models import Job, Agency, Appliance, Part, Technician
from app.services.home_memory_service import HomeMemoryService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="KeepWell Platform",
    description="The AI Repair Desk and Home Memory for Appliances in Tier 2/3 Indian Cities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and templates
static_path = os.path.join(BASE_DIR, "static")
templates_path = os.path.join(BASE_DIR, "templates")
os.makedirs(static_path, exist_ok=True)
os.makedirs(templates_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Register API Routers
app.include_router(routes_whatsapp.router)
app.include_router(routes_jobs.router)
app.include_router(routes_quotes.router)
app.include_router(routes_appliances.router)
app.include_router(routes_technicians.router)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db)):
    agency = db.query(Agency).first()
    fvr_metrics = HomeMemoryService.calculate_agency_fvr(db, agency.id if agency else 1)
    active_jobs = db.query(Job).order_by(Job.id.desc()).limit(10).all()
    parts_count = db.query(Part).count()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "agency": agency,
        "fvr_metrics": fvr_metrics,
        "active_jobs": active_jobs,
        "parts_count": parts_count
    })

@app.get("/agency", response_class=HTMLResponse)
def agency_desk_page(request: Request, db: Session = Depends(get_db)):
    agency = db.query(Agency).first()
    jobs = db.query(Job).order_by(Job.id.desc()).all()
    fvr_metrics = HomeMemoryService.calculate_agency_fvr(db, agency.id if agency else 1)
    parts = db.query(Part).all()
    technicians = db.query(Technician).all()
    return templates.TemplateResponse("agency_desk.html", {
        "request": request,
        "agency": agency,
        "jobs": jobs,
        "fvr_metrics": fvr_metrics,
        "parts": parts,
        "technicians": technicians
    })

@app.get("/simulator", response_class=HTMLResponse)
def simulator_page(request: Request, db: Session = Depends(get_db)):
    parts = db.query(Part).all()
    appliances = db.query(Appliance).all()
    return templates.TemplateResponse("whatsapp_simulator.html", {
        "request": request,
        "parts": parts,
        "appliances": appliances
    })

@app.get("/m/{token}", response_class=HTMLResponse)
def home_memory_customer_page(token: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.magic_token == token).first()
    if not job:
        return HTMLResponse("<h3>Invalid or expired link.</h3>", status_code=404)
    history = HomeMemoryService.get_appliance_history(db, job.appliance_id) if job.appliance_id else {}
    quote = job.quotes[-1] if job.quotes else None
    return templates.TemplateResponse("home_memory.html", {
        "request": request,
        "job": job,
        "appliance": history,
        "quote": quote
    })

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "keepwell-core",
        "region": settings.gcp_region,
        "models": {
            "fast": settings.gemini_model_fast,
            "reasoning": settings.gemini_model_reasoning
        }
    }
