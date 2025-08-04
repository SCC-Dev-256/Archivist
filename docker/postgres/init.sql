-- Archivist Database Initialization Script
-- Creates the initial database schema and tables

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create tables
CREATE TABLE IF NOT EXISTS transcription_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS vod_entries (
    id SERIAL PRIMARY KEY,
    cablecast_id INTEGER UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_path TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS file_metadata (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_size BIGINT,
    duration FLOAT,
    format VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_transcription_jobs_status ON transcription_jobs(status);
CREATE INDEX IF NOT EXISTS idx_transcription_jobs_created_at ON transcription_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_vod_entries_status ON vod_entries(status);
CREATE INDEX IF NOT EXISTS idx_file_metadata_file_path ON file_metadata(file_path);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_transcription_jobs_updated_at 
    BEFORE UPDATE ON transcription_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vod_entries_updated_at 
    BEFORE UPDATE ON vod_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_metadata_updated_at 
    BEFORE UPDATE ON file_metadata 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 