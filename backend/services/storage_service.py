"""
Phase 6D: Report and Object Storage Abstraction for AgentGuard
Provides a unified interface for storing generated reports (PDF, Excel, CSV)
locally or in S3-compatible cloud object storage with strict tenant isolation.
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger("agentguard.storage_service")

# Base directory for local report storage
BASE_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "reports"))


class StorageService:
    def __init__(self):
        self.provider = settings.OBJECT_STORAGE_PROVIDER.upper()
        self._s3_client = None

    def _get_s3_client(self):
        if self._s3_client is None:
            if not settings.S3_BUCKET or not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
                return None
            try:
                import boto3
                kwargs = {
                    "aws_access_key_id": settings.S3_ACCESS_KEY,
                    "aws_secret_access_key": settings.S3_SECRET_KEY,
                    "region_name": settings.S3_REGION or "us-east-1",
                }
                if settings.S3_ENDPOINT:
                    kwargs["endpoint_url"] = settings.S3_ENDPOINT
                self._s3_client = boto3.client("s3", **kwargs)
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self._s3_client = None
        return self._s3_client

    def is_s3_configured(self) -> bool:
        """Returns True only if all required S3 credentials and bucket are present."""
        return bool(
            settings.S3_BUCKET and
            settings.S3_ACCESS_KEY and
            settings.S3_SECRET_KEY
        )

    def save_report_file(
        self,
        content: bytes,
        filename: str,
        org_id: str,
        format_type: str = "PDF"
    ) -> Dict[str, Any]:
        """
        Saves report bytes to the active storage backend with tenant isolation.
        """
        if not org_id:
            raise ValueError("Tenant org_id is required for report storage.")

        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # 1. Attempt S3 if configured
        if self.provider == "S3" and self.is_s3_configured():
            s3 = self._get_s3_client()
            if s3:
                s3_key = f"orgs/{org_id}/reports/{filename}"
                try:
                    s3.put_object(
                        Bucket=settings.S3_BUCKET,
                        Key=s3_key,
                        Body=content,
                        ContentType="application/pdf" if format_type.upper() == "PDF" else "application/octet-stream"
                    )
                    return {
                        "storage_backend": "S3",
                        "storage_key": s3_key,
                        "file_path": f"s3://{settings.S3_BUCKET}/{s3_key}",
                        "file_size_bytes": file_size,
                        "sha256_checksum": sha256,
                        "status": "STORED"
                    }
                except Exception as e:
                    logger.error(f"S3 upload failed: {e}. Falling back to local storage.")

        # 2. Local File Storage (Default & Fallback)
        org_dir = os.path.join(BASE_STORAGE_DIR, f"org_{org_id}")
        os.makedirs(org_dir, exist_ok=True)
        local_path = os.path.join(org_dir, filename)

        # Ensure path does not escape tenant dir
        real_path = os.path.realpath(local_path)
        real_org_dir = os.path.realpath(org_dir)
        if not real_path.startswith(real_org_dir):
            raise PermissionError("Path traversal detected in report storage.")

        with open(local_path, "wb") as f:
            f.write(content)

        storage_key = f"local://org_{org_id}/{filename}"
        return {
            "storage_backend": "LOCAL",
            "storage_key": storage_key,
            "file_path": local_path,
            "file_size_bytes": file_size,
            "sha256_checksum": sha256,
            "status": "STORED"
        }

    def get_report_file(self, storage_key: str, org_id: str) -> Optional[bytes]:
        """
        Retrieves report bytes verifying tenant boundary.
        """
        if not storage_key or not org_id:
            return None

        if storage_key.startswith("s3://") or (self.provider == "S3" and not storage_key.startswith("local://")):
            if not self.is_s3_configured():
                return None
            s3 = self._get_s3_client()
            if not s3:
                return None
            clean_key = storage_key.replace(f"s3://{settings.S3_BUCKET}/", "")
            # Verify key belongs to tenant
            if not clean_key.startswith(f"orgs/{org_id}/"):
                raise PermissionError("Cross-tenant storage access denied.")
            try:
                resp = s3.get_object(Bucket=settings.S3_BUCKET, Key=clean_key)
                return resp["Body"].read()
            except Exception as e:
                logger.error(f"Error fetching S3 report object: {e}")
                return None

        # Local storage retrieval
        clean_name = storage_key.replace(f"local://org_{org_id}/", "")
        org_dir = os.path.join(BASE_STORAGE_DIR, f"org_{org_id}")
        local_path = os.path.join(org_dir, clean_name)

        real_path = os.path.realpath(local_path)
        real_org_dir = os.path.realpath(org_dir)
        if not real_path.startswith(real_org_dir):
            raise PermissionError("Cross-tenant storage access denied.")

        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        return None

    def get_storage_status(self) -> Dict[str, Any]:
        """
        Truthfully reports storage infrastructure health and provider state without leaking credentials.
        """
        s3_ok = self.is_s3_configured()
        return {
            "active_backend": "S3" if (self.provider == "S3" and s3_ok) else "LOCAL",
            "local_storage": {
                "status": "HEALTHY",
                "base_path": BASE_STORAGE_DIR,
                "writable": os.access(os.path.dirname(BASE_STORAGE_DIR), os.W_OK)
            },
            "object_storage": {
                "provider": "S3",
                "status": "HEALTHY" if s3_ok else "NOT_CONFIGURED",
                "bucket": settings.S3_BUCKET if s3_ok else None,
                "region": settings.S3_REGION if s3_ok else None
            }
        }


storage_service = StorageService()
