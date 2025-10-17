-- FPL Cheat Database Schema - Simplified Version
-- Run this script in your Supabase SQL editor

-- Drop the existing table if it exists
DROP TABLE IF EXISTS all_managers;

-- Create all_managers table with FPL API ID as primary key
CREATE TABLE all_managers (
    manager_id INTEGER PRIMARY KEY,
    manager_name TEXT NOT NULL,
    team_name TEXT NOT NULL
);

-- Create index for better performance on team_name lookups
CREATE INDEX idx_all_managers_team_name ON all_managers(team_name);
CREATE INDEX idx_all_managers_manager_name ON all_managers(manager_name);

-- Create fetch_progress table for tracking data fetch progress
CREATE TABLE fetch_progress (
    id INTEGER PRIMARY KEY DEFAULT 1,
    last_page INTEGER DEFAULT 0,
    last_manager_count INTEGER DEFAULT 0,
    last_batch_start_time TEXT,
    last_batch_end_time TEXT,
    total_managers_fetched INTEGER DEFAULT 0,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert initial progress record
INSERT INTO fetch_progress (id, last_page, last_manager_count, total_managers_fetched)
VALUES (1, 0, 0, 0);

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT ALL ON all_managers TO authenticated;
-- GRANT ALL ON all_managers TO anon;
-- GRANT ALL ON fetch_progress TO authenticated;
-- GRANT ALL ON fetch_progress TO anon;
