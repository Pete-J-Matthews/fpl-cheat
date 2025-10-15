-- FPL Cheat Database Schema
-- Run this script in your Supabase SQL editor

-- Create creator_teams table
CREATE TABLE IF NOT EXISTS creator_teams (
    id SERIAL PRIMARY KEY,
    team_name TEXT NOT NULL,
    squad_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_creator_teams_team_name ON creator_teams(team_name);
CREATE INDEX IF NOT EXISTS idx_creator_teams_created_at ON creator_teams(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_creator_teams_updated_at 
    BEFORE UPDATE ON creator_teams 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add some sample data (optional)
-- INSERT INTO creator_teams (team_name, squad_data) VALUES 
-- ('FPL General', '{"picks": [], "entry": 12345}'),
-- ('FPL Focal', '{"picks": [], "entry": 67890}');

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT ALL ON creator_teams TO authenticated;
-- GRANT ALL ON creator_teams TO anon;
