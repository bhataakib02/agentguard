-- AGENTGUARD Supabase Migration: Add OTP Challenges Table
-- Revision ID: 0002_add_otp_challenges
-- Secure cryptographic one-time passcode challenge table

CREATE TABLE IF NOT EXISTS public.otp_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR NOT NULL,
    purpose VARCHAR NOT NULL,
    code_hash VARCHAR NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    consumed BOOLEAN NOT NULL DEFAULT FALSE,
    consumed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resend_available_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address VARCHAR,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_otp_challenges_email ON public.otp_challenges (email);
CREATE INDEX IF NOT EXISTS ix_otp_challenges_purpose ON public.otp_challenges (purpose);
CREATE INDEX IF NOT EXISTS ix_otp_challenges_code_hash ON public.otp_challenges (code_hash);
CREATE INDEX IF NOT EXISTS ix_otp_challenges_consumed ON public.otp_challenges (consumed);
CREATE INDEX IF NOT EXISTS ix_otp_challenges_expires_at ON public.otp_challenges (expires_at);
CREATE INDEX IF NOT EXISTS ix_otp_challenges_created_at ON public.otp_challenges (created_at);
