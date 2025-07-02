-- Migration: Add cablecast_shows table for Cablecast integration
-- This table stores the mapping between Archivist transcriptions and Cablecast shows

CREATE TABLE IF NOT EXISTS cablecast_shows (
    id SERIAL PRIMARY KEY,
    cablecast_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration INTEGER, -- Duration in seconds
    transcription_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(transcription_id), -- Each transcription can only be linked to one show
    UNIQUE(cablecast_id, transcription_id), -- Prevent duplicate links
    
    -- Foreign key to transcription_results
    CONSTRAINT fk_cablecast_shows_transcription 
        FOREIGN KEY (transcription_id) 
        REFERENCES transcription_results(id) 
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_cablecast_shows_cablecast_id ON cablecast_shows(cablecast_id);
CREATE INDEX IF NOT EXISTS idx_cablecast_shows_transcription_id ON cablecast_shows(transcription_id);
CREATE INDEX IF NOT EXISTS idx_cablecast_shows_created_at ON cablecast_shows(created_at);

-- Add comments for documentation
COMMENT ON TABLE cablecast_shows IS 'Maps Archivist transcriptions to existing Cablecast shows';
COMMENT ON COLUMN cablecast_shows.cablecast_id IS 'ID of the show in Cablecast system';
COMMENT ON COLUMN cablecast_shows.transcription_id IS 'ID of the transcription in Archivist';
COMMENT ON COLUMN cablecast_shows.title IS 'Title of the Cablecast show';
COMMENT ON COLUMN cablecast_shows.description IS 'Description of the Cablecast show';
COMMENT ON COLUMN cablecast_shows.duration IS 'Duration of the show in seconds'; 