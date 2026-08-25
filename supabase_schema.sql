-- Supabase Schema for Tracker App
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Links table
CREATE TABLE IF NOT EXISTS links (
    id BIGSERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    loc INTEGER NOT NULL DEFAULT 1,
    cam INTEGER NOT NULL DEFAULT 0,
    mic INTEGER NOT NULL DEFAULT 0,
    interval_s INTEGER NOT NULL DEFAULT 5,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    link_id BIGINT NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    alt DOUBLE PRECISION,
    battery_level DOUBLE PRECISION,
    battery_charging BOOLEAN,
    ua TEXT,
    ip TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Media table
CREATE TABLE IF NOT EXISTS media (
    id BIGSERIAL PRIMARY KEY,
    link_id BIGINT NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('photo', 'audio')),
    filename TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_links_token ON links(token);
CREATE INDEX IF NOT EXISTS idx_links_active ON links(active);
CREATE INDEX IF NOT EXISTS idx_reports_link_id ON reports(link_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_link_id ON media(link_id);
CREATE INDEX IF NOT EXISTS idx_media_created_at ON media(created_at DESC);

-- Row Level Security (RLS) - Optional but recommended
-- Enable RLS on all tables
ALTER TABLE links ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE media ENABLE ROW LEVEL SECURITY;

-- Policies: Allow all operations for service role (backend)
-- These are permissive - tighten as needed for production
CREATE POLICY "Allow all for service role" ON links FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Allow all for service role" ON reports FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Allow all for service role" ON media FOR ALL USING (auth.role() = 'service_role');

-- Storage bucket for media (create via Supabase Dashboard or run this)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('tracker-media', 'tracker-media', false);

-- Storage policies for tracker-media bucket
-- Allow service role full access
-- CREATE POLICY "Service role full access" ON storage.objects FOR ALL USING (bucket_id = 'tracker-media' AND auth.role() = 'service_role');