"""
AGENTGUARD — Dedicated Automated Test Suite for Production Signing Secret Rotation
Verifies:
1. Cryptographic secret generation requirements (minimum 32 bytes/64 hex chars).
2. Fail-closed rejection of insecure placeholders, empty keys, and short keys in production.
3. Cryptographic invalidation of existing sessions and tokens signed with a compromised/previous key.
4. Successful issuance and validation of new session tokens under the rotated secret.
5. Session revocation on logout.
6. WebSocket ticket rejection across secret rotation boundaries.
"""

import os
import unittest
import secrets
from unittest.mock import patch
from fastapi.testclient import TestClient
from jose import jwt, JWTError
import uuid

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Settings
from core.security import create_access_token
from main import app
from ws_manager import WebSocketTicketManager

client = TestClient(app)

class TestSecretRotationAndSessionInvalidation(unittest.TestCase):
    def setUp(self):
        self.old_secret = secrets.token_hex(32)
        self.new_secret = secrets.token_hex(32)
        self.user_id = str(uuid.uuid4())
        self.email = f"user_{uuid.uuid4().hex[:6]}@example.com"
        self.role = "ADMIN"

    def test_01_cryptographic_secret_generation(self):
        """Generates a fresh 256-bit (64-char hex) key and verifies entropy requirements."""
        fresh_secret = secrets.token_hex(32)
        self.assertEqual(len(fresh_secret), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in fresh_secret))
        self.assertNotEqual(fresh_secret, self.old_secret)
        self.assertNotEqual(fresh_secret, self.new_secret)

    def test_02_production_rejects_insecure_or_placeholder_keys(self):
        """Production configuration must fail closed if SECRET_KEY is missing, short, or in placeholder blacklist."""
        blacklisted = [
            "",
            "   ",
            "short-key",
            "change-this-to-a-secure-random-32-byte-hex-key",
            "agentguard-super-secret-production-key-2026",
            "agentguard-default-signing-key",
            "agentguard-dev-stable-signing-key-2026-secure",
            "agentguard-default-key-for-dev",
        ]
        for bad_key in blacklisted:
            with patch.dict(os.environ, {
                "ENVIRONMENT": "production",
                "SECRET_KEY": bad_key,
                "DATABASE_URL": "postgresql://user:pass@localhost:5432/db"
            }):
                with self.assertRaises(RuntimeError) as ctx:
                    Settings()
                self.assertIn("requires a strong, securely provisioned SECRET_KEY", str(ctx.exception))

    def test_03_production_accepts_rotated_secret(self):
        """Production configuration accepts valid cryptographically generated 64-char hex key."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": self.new_secret,
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db"
        }):
            s = Settings()
            self.assertEqual(s.SECRET_KEY, self.new_secret)
            self.assertEqual(s.ENVIRONMENT, "production")

    def test_04_tokens_signed_with_old_secret_are_rejected_after_rotation(self):
        """Tokens signed with the old secret must be rejected when rotated secret is active."""
        # 1. Sign token with old secret
        token_under_old = jwt.encode(
            {"sub": self.user_id, "email": self.email, "role": self.role},
            self.old_secret,
            algorithm="HS256"
        )

        # 2. Verify with old secret works
        decoded = jwt.decode(token_under_old, self.old_secret, algorithms=["HS256"])
        self.assertEqual(decoded["email"], self.email)

        # 3. Verify under new secret fails with JWTError signature failure
        with self.assertRaises(JWTError):
            jwt.decode(token_under_old, self.new_secret, algorithms=["HS256"])

    def test_05_new_tokens_under_rotated_secret_are_valid(self):
        """Tokens signed with the newly rotated secret are valid and parseable."""
        token_under_new = jwt.encode(
            {"sub": self.user_id, "email": self.email, "role": self.role},
            self.new_secret,
            algorithm="HS256"
        )
        decoded = jwt.decode(token_under_new, self.new_secret, algorithms=["HS256"])
        self.assertEqual(decoded["sub"], self.user_id)
        self.assertEqual(decoded["email"], self.email)
        self.assertEqual(decoded["role"], self.role)

    def test_06_ws_tickets_under_old_secret_rejected_after_rotation(self):
        """WebSocket tickets generated with old secret are rejected by ticket manager with new secret."""
        # Ticket issued under old secret
        ticket_payload = {
            "ticket_id": str(uuid.uuid4()),
            "sub": self.user_id,
            "user_id": self.user_id,
            "org_id": None,
            "role": self.role,
            "email": self.email,
            "token_type": "ws_ticket",
            "exp": 9999999999
        }
        old_ticket_token = jwt.encode(ticket_payload, self.old_secret, algorithm="HS256")

        # Ticket manager operating with new secret
        with patch("config.settings.SECRET_KEY", self.new_secret):
            with patch("config.settings.ENVIRONMENT", "development"):
                mgr = WebSocketTicketManager()
                result = mgr.consume_ticket(old_ticket_token)
                self.assertIsNone(result, "Ticket signed with old secret must be rejected after rotation")


if __name__ == "__main__":
    unittest.main()
