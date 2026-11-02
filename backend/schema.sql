-- =========================================================
-- ReLoop Database Schema (PostgreSQL DDL)
-- Smart Electronic Device Recovery Platform
-- Note: Does NOT include any environmental metrics
-- =========================================================

-- Enable uuid generation if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: device_categories
CREATE TABLE IF NOT EXISTS device_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: devices
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INT NOT NULL REFERENCES device_categories(id),
    name VARCHAR(150) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    purchase_year INT,
    approximate_age_years NUMERIC(4,1),
    working_condition VARCHAR(30) NOT NULL CHECK (working_condition IN ('working', 'minor_issues', 'major_issues', 'not_working', 'unknown')),
    fault_description TEXT,
    powers_on BOOLEAN,
    physically_damaged BOOLEAN,
    contains_personal_data BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: assessments
CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    overall_condition VARCHAR(30) NOT NULL CHECK (overall_condition IN ('excellent', 'good', 'fair', 'poor', 'unknown')),
    functional_status VARCHAR(30) NOT NULL CHECK (functional_status IN ('fully_functional', 'partially_functional', 'non_functional', 'unknown')),
    specific_faults JSONB DEFAULT '[]'::jsonb,
    estimated_repair_cost NUMERIC(10,2),
    estimated_resale_value NUMERIC(10,2),
    estimated_replacement_cost NUMERIC(10,2),
    expected_remaining_life_years NUMERIC(4,1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    recommended_route VARCHAR(30) NOT NULL CHECK (recommended_route IN ('Repair', 'Reuse', 'Resell', 'Donate', 'Refurbish', 'Recycle')),
    overall_score NUMERIC(5,2) NOT NULL,
    explanation TEXT NOT NULL,
    summary TEXT NOT NULL,
    weights_used JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: recommendation_scores
CREATE TABLE IF NOT EXISTS recommendation_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    route VARCHAR(30) NOT NULL CHECK (route IN ('Repair', 'Reuse', 'Resell', 'Donate', 'Refurbish', 'Recycle')),
    is_eligible BOOLEAN NOT NULL,
    final_score NUMERIC(5,2) NOT NULL,
    financial_score NUMERIC(5,2) NOT NULL,
    useful_life_score NUMERIC(5,2) NOT NULL,
    convenience_score NUMERIC(5,2) NOT NULL,
    reuse_score NUMERIC(5,2) NOT NULL,
    ineligible_reason TEXT,
    score_breakdown JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: service_providers
CREATE TABLE IF NOT EXISTS service_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    category VARCHAR(30) NOT NULL CHECK (category IN ('Repair', 'Resell', 'Donate', 'Refurbish', 'Recycle')),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150),
    contact_phone VARCHAR(50),
    website VARCHAR(255),
    services_offered JSONB DEFAULT '[]'::jsonb,
    operating_hours VARCHAR(150),
    is_verified BOOLEAN DEFAULT FALSE,
    is_sample BOOLEAN DEFAULT TRUE,
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    rating NUMERIC(3,2) DEFAULT 4.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: recovery_requests
CREATE TABLE IF NOT EXISTS recovery_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    selected_route VARCHAR(30) NOT NULL CHECK (selected_route IN ('Repair', 'Reuse', 'Resell', 'Donate', 'Refurbish', 'Recycle')),
    provider_id UUID REFERENCES service_providers(id) ON DELETE SET NULL,
    current_status VARCHAR(50) NOT NULL CHECK (current_status IN (
        'Request Created',
        'Provider Selected',
        'Device Submitted / Collected',
        'Device Under Assessment',
        'Recovery in Progress',
        'Completed'
    )),
    tracking_code VARCHAR(30) UNIQUE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: recovery_status_history
CREATE TABLE IF NOT EXISTS recovery_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_request_id UUID NOT NULL REFERENCES recovery_requests(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    notes TEXT,
    updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_category_id ON devices(category_id);
CREATE INDEX IF NOT EXISTS idx_assessments_device_id ON assessments(device_id);
CREATE INDEX IF NOT EXISTS idx_assessments_user_id ON assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_assessment_id ON recommendations(assessment_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_device_id ON recommendations(device_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_scores_rec_id ON recommendation_scores(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_service_providers_category ON service_providers(category);
CREATE INDEX IF NOT EXISTS idx_service_providers_city ON service_providers(city);
CREATE INDEX IF NOT EXISTS idx_recovery_requests_user_id ON recovery_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_recovery_requests_tracking_code ON recovery_requests(tracking_code);
CREATE INDEX IF NOT EXISTS idx_recovery_requests_status ON recovery_requests(current_status);
CREATE INDEX IF NOT EXISTS idx_recovery_status_history_req_id ON recovery_status_history(recovery_request_id);
