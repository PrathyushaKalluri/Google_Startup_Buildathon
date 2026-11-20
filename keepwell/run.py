#!/usr/bin/env python3
"""KeepWell Development Server Runner.
Initializes the database, loads fixtures if first run, and launches FastAPI.
"""
import uvicorn
import os
import sys

# Ensure keepwell directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import init_db
from app.fixtures.seed_data import seed_database

if __name__ == "__main__":
    print("=" * 60)
    print("KeepWell — AI Repair Desk & Home Memory for Appliances")
    print("Target: Tier 2/3 Indian Cities | Refrigerator & AC Repairs")
    print("Powered by Google DeepMind & Google Cloud (asia-south1)")
    print("=" * 60)
    
    print("[1/2] Initializing database and verifying fixtures...")
    init_db()
    seed_database()
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"[2/2] Launching KeepWell server on http://localhost:{port}")
    print(f" -> Agency Desk:        http://localhost:{port}/agency")
    print(f" -> WhatsApp Simulator: http://localhost:{port}/simulator")
    print(f" -> API Docs (Swagger): http://localhost:{port}/docs")
    print("=" * 60)
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
