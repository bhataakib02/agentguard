"""
Supabase Admin Auth Utility
===========================
Centralised module for all server-side Supabase Auth operations that require
the Service Role Key (e.g. creating users without email confirmation, setting
passwords server-side, deleting auth accounts).

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
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class SupabaseAdminClient:
    """
    Thin HTTP wrapper around the Supabase Auth Admin API.

    If SUPABASE_SERVICE_ROLE_KEY is not set, all operations are no-ops
    (return None) so that local development without the key doesn't crash.
    In production this key MUST be set for full auth sync to work.
    """

    def __init__(self):
        self.supabase_url = os.getenv(
            "SUPABASE_URL",
            "https://xjragvyzlailmtfwjfnm.supabase.co"
        ).rstrip("/")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
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
    def _headers(self) -> dict:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.service_role_key)

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

        Parameters
        ----------
        email         : User's email address
        password      : Plain-text password (Supabase hashes it internally)
        full_name     : Optional display name stored in user_metadata
        email_confirm : If True, marks email as pre-confirmed (no email sent)

        Returns
        -------
        str | None : Supabase auth_user_id on success, None on failure
        """
        if not self.is_configured:
            logger.debug(
                "[SupabaseAdmin] Skipping create_user for %s (no service role key)", email
            )
            return None

        payload = {
            "email": email,
            "password": password,
            "email_confirm": email_confirm,
        }
        if full_name:
            payload["user_metadata"] = {"full_name": full_name}

        try:
            resp = requests.post(
                self.admin_api,
                json=payload,
                headers=self._headers,
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                auth_id = data.get("id")
                logger.info(
                    "[SupabaseAdmin] Created Supabase Auth user for %s (id=%s)", email, auth_id
                )
                return auth_id

            # 422 = user already exists in Supabase Auth
            if resp.status_code == 422:
                existing_id = self._get_existing_user_id(email)
                if existing_id:
                    logger.info(
                        "[SupabaseAdmin] Supabase Auth user already exists for %s (id=%s)",
                        email, existing_id
                    )
                    return existing_id

            logger.warning(
                "[SupabaseAdmin] Failed to create Supabase Auth user for %s: %s %s",
                email, resp.status_code, resp.text
            )
            return None

        except requests.RequestException as exc:
            logger.error(
                "[SupabaseAdmin] Network error creating Supabase Auth user for %s: %s",
                email, exc
            )
            return None

    def _get_existing_user_id(self, email: str) -> Optional[str]:
        """
        List admin users filtered by email to find the existing auth_user_id.
        Used when create_user returns 422 (already exists).
        """
        if not self.is_configured:
            return None
        try:
            resp = requests.get(
                f"{self.admin_api}?email={email}",
                headers=self._headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                users = data.get("users", [])
                for u in users:
                    if u.get("email", "").lower() == email.lower():
                        return u.get("id")
        except requests.RequestException:
            pass
        return None

    def update_user_password(self, auth_user_id: str, new_password: str) -> bool:
        """
        Update the password of an existing Supabase Auth user.
        Returns True on success, False on failure.
        """
        if not self.is_configured:
            return False
        try:
            resp = requests.put(
                f"{self.admin_api}/{auth_user_id}",
                json={"password": new_password},
                headers=self._headers,
                timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def delete_user(self, auth_user_id: str) -> bool:
        """
        Delete a user from Supabase Auth by their auth_user_id.
        Returns True on success, False on failure.
        """
        if not self.is_configured:
            return False
        try:
            resp = requests.delete(
                f"{self.admin_api}/{auth_user_id}",
                headers=self._headers,
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except requests.RequestException:
            return False


# Singleton instance — import this everywhere
supabase_admin = SupabaseAdminClient()
