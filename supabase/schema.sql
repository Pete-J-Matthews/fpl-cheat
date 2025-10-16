-- FPL Cheat Database Schema - Simplified Version
-- Run this script in your Supabase SQL editor

-- Drop the existing table if it exists
DROP TABLE IF EXISTS all_managers;

-- Create all_managers table with simple structure
CREATE TABLE all_managers (
    manager_id SERIAL PRIMARY KEY,
    manager_name TEXT NOT NULL,
    team_name TEXT NOT NULL
);

-- Create index for better performance on team_name lookups
CREATE INDEX idx_all_managers_team_name ON all_managers(team_name);
CREATE INDEX idx_all_managers_manager_name ON all_managers(manager_name);


-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT ALL ON all_managers TO authenticated;
-- GRANT ALL ON all_managers TO anon;
