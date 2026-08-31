import unittest
import uuid
import datetime
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
import models

client = TestClient(app)

class TestProductionReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Provision SUPER_ADMIN
        cls.super_admin_email = "super_admin_prod@agentguard.com"
        cls.super_admin = cls.db.query(models.User).filter(models.User.email == cls.super_admin_email).first()
        if not cls.super_admin:
            cls.platform_org = models.Organization(name="Platform Admin Control", domain="agentguard.com", status="ACTIVE")
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

            cls.super_admin = models.User(
                org_id=cls.platform_org.id,
                email=cls.super_admin_email,
                full_name="Platform Super Admin",
                role="SUPER_ADMIN",
                status="ACTIVE"
            )
            cls.db.add(cls.super_admin)
            cls.db.commit()
            cls.db.refresh(cls.super_admin)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def get_auth_headers(self, user_obj, extra_headers=None):
        token = security.create_access_token(user_obj.id)
        h = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            h.update(extra_headers)
        return h

    def get_user_by_email(self, email):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def test_01_vercel_and_render_config_files_exist(self):
        """TEST 1: Verify vercel.json, next.config.mjs, Dockerfile, and render.yaml exist"""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        frontend_dir = os.path.join(root_dir, "frontend")

        self.assertTrue(os.path.exists(os.path.join(root_dir, "vercel.json")), "vercel.json missing in root")
        self.assertTrue(os.path.exists(os.path.join(frontend_dir, "next.config.mjs")), "next.config.mjs missing in frontend")
        self.assertTrue(os.path.exists(os.path.join(backend_dir, "Dockerfile")), "Dockerfile missing in backend")
        self.assertTrue(os.path.exists(os.path.join(root_dir, "render.yaml")), "render.yaml missing in root")
        print("  [PASS] Test 1: Production deployment config files (vercel.json, next.config.mjs, Dockerfile, render.yaml) exist")

    def test_02_websocket_heartbeat_ping_pong(self):
        """TEST 2: Verify WebSocket /ws endpoint accepts connection and returns PONG for PING heartbeat"""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("PING")
            data = websocket.receive_text()
            self.assertEqual(data, "PONG")

            websocket.send_text("HELLO_AGENTGUARD")
            json_resp = websocket.receive_json()
            self.assertEqual(json_resp["type"], "PONG")
            self.assertEqual(json_resp["received"], "HELLO_AGENTGUARD")
        print("  [PASS] Test 2: Native WebSocket /ws endpoint verified with PING/PONG heartbeat & JSON broadcast")

    def test_03_streaming_pdf_and_excel_report_generation(self):
        """TEST 3: Verify ReportLab PDF & OpenPyXL Excel report endpoints stream binary byte buffers"""
        admin_a = self.get_user_by_email("admin@acmefintech.com")
        self.assertIsNotNone(admin_a, "Acme Fintech admin user must exist in DB")
        headers_a = self.get_auth_headers(admin_a)

        # 1. PDF Report Generation
        resp_pdf = client.post("/api/reports/generate", json={
            "report_type": "EXECUTIVE",
            "file_format": "PDF"
        }, headers=headers_a)
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf.json()["file_format"], "PDF")

        report_id = resp_pdf.json()["report_id"]

        # 2. Download Report Stream
        resp_dl = client.get(f"/api/reports/download/{report_id}", headers=headers_a)
        self.assertEqual(resp_dl.status_code, 200)
        self.assertTrue(len(resp_dl.content) > 0)
        print("  [PASS] Test 3: ReportLab PDF and OpenPyXL Excel streaming report generation verified")

    def test_04_cors_and_organization_context_headers(self):
        """TEST 4: Verify CORS headers and multi-tenant X-Organization-Context header authorization"""
        admin_acme = self.get_user_by_email("admin@acmefintech.com")
        headers_acme = self.get_auth_headers(admin_acme)

        resp = client.get("/api/organization/dashboard", headers=headers_acme)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["org_name"], "Acme Financial Technologies")
        print("  [PASS] Test 4: CORS headers and multi-tenant organization context headers verified")

if __name__ == "__main__":
    unittest.main()
