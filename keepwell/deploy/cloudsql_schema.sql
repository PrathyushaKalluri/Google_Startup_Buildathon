-- ==============================================================================
-- KeepWell: Cloud SQL (PostgreSQL + pgvector) DDL Schema
-- Region: asia-south1 (Mumbai)
-- Multi-tenant row-level security enabled per agency
-- ==============================================================================

-- Enable pgvector for manual semantic search & similar repair matching
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Agencies (Tenants)
CREATE TABLE IF NOT EXISTS agencies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    city VARCHAR(50) DEFAULT 'Warangal',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Technicians
CREATE TABLE IF NOT EXISTS technicians (
    id SERIAL PRIMARY KEY,
    agency_id INT REFERENCES agencies(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    skills VARCHAR(200) DEFAULT 'REFRIGERATOR,AC',
    languages VARCHAR(100) DEFAULT 'Telugu,Hindi,English',
    rating FLOAT DEFAULT 4.8,
    active BOOLEAN DEFAULT TRUE
);

-- 3. Customers
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) DEFAULT 'Household',
    language VARCHAR(20) DEFAULT 'Telugu',
    address VARCHAR(255) DEFAULT 'Warangal, Telangana',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Appliances (Digital Passports)
CREATE TABLE IF NOT EXISTS appliances (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE SET NULL,
    appliance_type VARCHAR(50) DEFAULT 'REFRIGERATOR',
    brand VARCHAR(50) NOT NULL,
    model_number VARCHAR(100),
    serial_number VARCHAR(100),
    purchase_year INT DEFAULT 2022,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Parts Inventory (Verified Catalogue)
CREATE TABLE IF NOT EXISTS parts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price FLOAT NOT NULL,
    in_stock INT DEFAULT 10,
    compatible_models TEXT DEFAULT '[]'
);

-- 6. Jobs (Repair Workflows)
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    agency_id INT REFERENCES agencies(id) ON DELETE CASCADE,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    appliance_id INT REFERENCES appliances(id) ON DELETE SET NULL,
    state VARCHAR(50) NOT NULL,
    raw_transcript TEXT,
    language VARCHAR(20) DEFAULT 'te',
    symptom_category VARCHAR(100),
    hazard_flag BOOLEAN DEFAULT FALSE,
    hazard_summary TEXT,
    diagnostic_hypotheses TEXT DEFAULT '[]',
    inspect_first BOOLEAN DEFAULT FALSE,
    selected_part_id INT REFERENCES parts(id),
    parts_status VARCHAR(50) DEFAULT 'NOT_CHECKED',
    assigned_technician_id INT REFERENCES technicians(id),
    scheduled_slot VARCHAR(100),
    magic_token VARCHAR(64) UNIQUE,
    is_repeat BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Job Event Audit Log (Append-only)
CREATE TABLE IF NOT EXISTS job_events (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
    from_state VARCHAR(50),
    to_state VARCHAR(50),
    actor VARCHAR(50),
    comment TEXT,
    payload TEXT DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Quotes & Billing
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
    visiting_charge FLOAT DEFAULT 250.0,
    labor_charge FLOAT DEFAULT 300.0,
    parts_cost FLOAT DEFAULT 0.0,
    gst_amount FLOAT DEFAULT 0.0,
    total_amount FLOAT DEFAULT 550.0,
    agency_approved BOOLEAN DEFAULT FALSE,
    customer_approved BOOLEAN DEFAULT FALSE,
    payment_status VARCHAR(30) DEFAULT 'PENDING',
    upi_txn_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Service Events (Permanent Home Memory)
CREATE TABLE IF NOT EXISTS service_events (
    id SERIAL PRIMARY KEY,
    appliance_id INT REFERENCES appliances(id) ON DELETE CASCADE,
    job_id INT REFERENCES jobs(id) ON DELETE SET NULL,
    event_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    technician_findings TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    customer_confirmed BOOLEAN DEFAULT TRUE,
    first_visit_resolved BOOLEAN DEFAULT TRUE
);
