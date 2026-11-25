# AGENTGUARD — Supabase Storage Architecture & Requirements

**Document Version**: 1.0.0  
**Audit Scope**: Supabase Storage Buckets & Application File Storage Usage  
**Audit Status**: Verified Clean (Zero Unused Buckets to Provision)  

---

## 1. Storage Subsystem Audit Findings

A comprehensive search of the AGENTGUARD codebase and live Supabase catalog was conducted:

1. **Live Supabase Storage Catalog**:
   - Query: `SELECT id, name, public, created_at, updated_at FROM storage.buckets;`
   - Result: **0 rows returned** (`[]`). No storage buckets currently exist in the production Supabase project.
2. **Application Storage Architecture**:
   - AGENTGUARD routes all file generation (compliance reports in PDF, CSV, and Excel formats) through `services.storage_service.StorageService` (`backend/services/storage_service.py`).
   - The storage provider is abstracted via the setting `OBJECT_STORAGE_PROVIDER`:
     - Default: `LOCAL` (`backend/storage/reports/org_<org_id>/...`).
     - Enterprise Option: `S3` (AWS S3-compatible cloud object storage using `boto3`).
3. **Supabase Storage Integration**:
   - The application does **not** integrate with or depend on the Supabase Storage API (`@supabase/storage-js` or HTTP `/storage/v1/object`).
   - All report downloads and exports are authenticated at the FastAPI router level (`backend/routers/reports.py`) and streamed directly via `FileResponse`.

---

## 2. Bucket Provisioning Decision

**Strict Safety Rule**: *"Do not provision unused buckets."*

- **Decision**: **ZERO Supabase Storage buckets should be created.**
- **Rationale**: Creating unused buckets in Supabase introduces an unnecessary attack surface, unmonitored storage permissions, and potential PostgREST storage endpoint exposure without application benefit.
- If cloud object storage is required for multi-instance deployments, AGENTGUARD utilizes AWS S3 or private S3-compatible buckets with dedicated IAM role policies and server-side encryption.
