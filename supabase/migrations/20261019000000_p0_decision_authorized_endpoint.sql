-- AGENTGUARD Supabase Migration: P0-1 Decision Authorized Endpoint Snapshot Binding
-- Binds runtime execution gate tokens to the exact tool endpoint snapshot at decision time

ALTER TABLE decisions ADD COLUMN IF NOT EXISTS authorized_endpoint VARCHAR;
