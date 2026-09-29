"""
Supabase Admin Auth Utility
===========================
Centralised module for all server-side Supabase Auth operations that require
the Service Role Key (e.g. creating users without email confirmation, setting
passwords server-side, deleting auth accounts).

This module uses Python's standard library `urllib` exclusively so it has
ZERO external dependencies and will NEVER fail with ModuleNotFoundError.

Usage
-----
from core.supabase_admin import supabase_admin
auth_user_id = supabase_admin.create_user(email, password)

Environment Variables Required
-------------------------------
SUPABASE_URL            - e.g. https://xjragvyzlailmtfwjfnm.supabase.co
SUPABASE_SERVICE_ROLE_KEY - Supabase Service Role key (NOT the publishable/anon key)
                           Found in: Supabase Dashboard -> Project Settings -> API -> service_role

Important: The Service Role key bypasses RLS and must NEVER be sent to the frontend.
It should ONLY be set in the backend environment (Render.com environment variables).
"""

import os
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Any, Dict, Tuple

logger = logging.getLogger(__name__)


class SupabaseAdminClient:
    """
    HTTP wrapper around the Supabase Auth Admin API using Python's standard library.

    If SUPABASE_SERVICE_ROLE_KEY is not set, all operations are safe no-ops
    (return None/False) so that local development without the key doesn't crash.
    In production this key can be set for full Supabase Auth sync.
    """

    def __init__(self):
        self.supabase_url = os.getenv(
            "SUPABASE_URL",
            "https://xjragvyzlailmtfwjfnm.supabase.co"
        ).rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.admin_api = f"{self.supabase_url}/auth/v1/admin/users"

        if not self.service_role_key:
            logger.warning(
                "[SupabaseAdmin] SUPABASE_SERVICE_ROLE_KEY is not set. "
                "Users created via the platform/invite flows will have a local "
                "password_hash only. They can log in via the /auth/local-login "
                "fallback, but will NOT have a Supabase Auth account. "
                "Set SUPABASE_SERVICE_ROLE_KEY in production for full auth sync."
            )

    @property
    def is_configured(self) -> bool:
        return bool(self.service_role_key)

    def _request(self, method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        """
        Execute an HTTP request using Python standard library urllib.
        Returns (status_code, parsed_json_or_body).
        """
        if not self.is_configured:
            return 0, None

        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-Backend/1.0"
        }
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_bytes = resp.read()
                try:
                    return resp.status, json.loads(resp_bytes.decode("utf-8"))
                except Exception:
                    return resp.status, resp_bytes.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            err_bytes = e.read()
            try:
                parsed = json.loads(err_bytes.decode("utf-8"))
            except Exception:
                parsed = err_bytes.decode("utf-8", errors="replace")
            return e.code, parsed
        except Exception as e:
            logger.error(f"[SupabaseAdmin] Network error calling {url}: {e}")
            return 0, str(e)

    def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        email_confirm: bool = True,
    ) -> Optional[str]:
        """
        Create a user in Supabase Auth and return their auth_user_id (UUID).
        Returns None if the service role key is not configured or if the call fails.
        """
        if not self.is_configured:
            logger.debug(
                "[SupabaseAdmin] Skipping create_user for %s (no service role key)", email
            )
            return None

        payload: Dict[str, Any] = {
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        }
        if full_name:
            payload["user_metadata"] = {"full_name": full_name}

        status_code, resp_data = self._request("POST", self.admin_api, payload)

        if status_code in (200, 201) and isinstance(resp_data, dict):
            auth_id = resp_data.get("id")
            logger.info(
                "[SupabaseAdmin] Created Supabase Auth user for %s (id=%s)", email, auth_id
            )
            return auth_id

        # 422 = user already exists in Supabase Auth
        if status_code == 422:
            existing_id = self._get_existing_user_id(email)
            if existing_id:
                logger.info(
                    "[SupabaseAdmin] Supabase Auth user already exists for %s (id=%s)",
                    email, existing_id
                )
                return existing_id

        logger.warning(
            "[SupabaseAdmin] Failed to create Supabase Auth user for %s: %s %s",
            email, status_code, resp_data
        )
        return None

    def _get_existing_user_id(self, email: str) -> Optional[str]:
        """
        List admin users filtered by email to find the existing auth_user_id.
        Used when create_user returns 422 (already exists).
        """
        if not self.is_configured:
            return None

        url = f"{self.admin_api}?email={urllib.parse.quote(email)}"
        status_code, resp_data = self._request("GET", url)

        if status_code == 200 and isinstance(resp_data, dict):
            users = resp_data.get("users", [])
            for u in users:
                if u.get("email", "").lower() == email.lower():
                    return u.get("id")
        return None

    def update_user_password(self, auth_user_id: str, new_password: str) -> bool:
        """
        Update the password of an existing Supabase Auth user.
        Returns True on success, False on failure.
        """
        if not self.is_configured:
            return False

        url = f"{self.admin_api}/{auth_user_id}"
        status_code, _ = self._request("PUT", url, {"password": new_password})
        return status_code == 200

    def delete_user(self, auth_user_id: str) -> bool:
        """
        Delete a user from Supabase Auth by their auth_user_id.
        Returns True on success, False on failure.
        """
        if not self.is_configured:
            return False

        url = f"{self.admin_api}/{auth_user_id}"
        status_code, _ = self._request("DELETE", url)
        return status_code in (200, 204)


# Singleton instance — import this everywhere
supabase_admin = SupabaseAdminClient()
