-- FPL Cheat Database Schema - Simplified Version
-- Run this script in your Supabase SQL editor

-- Drop the existing table if it exists
DROP TABLE IF EXISTS creator_teams;

-- Create creator_teams table with simple structure
CREATE TABLE creator_teams (
    user_id SERIAL PRIMARY KEY,
    user_name TEXT NOT NULL,
    team_name TEXT NOT NULL
);

-- Create index for better performance on team_name lookups
CREATE INDEX idx_creator_teams_team_name ON creator_teams(team_name);
CREATE INDEX idx_creator_teams_user_name ON creator_teams(user_name);

-- Add some sample data (optional)
-- INSERT INTO creator_teams (user_name, team_name) VALUES 
-- ('FPL General', 'General FPL'),
-- ('FPL Focal', 'Focal FPL');

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT ALL ON creator_teams TO authenticated;
-- GRANT ALL ON creator_teams TO anon;
