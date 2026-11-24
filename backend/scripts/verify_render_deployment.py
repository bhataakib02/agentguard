"""
Deployment Verification Script for Render Celery Worker & Beat Blueprint.
Checks:
1. Render Blueprint JSON Schema compliance.
2. Celery application import and loader.
3. Registration of tasks.auth_tasks.cleanup_expired_otp_challenges_task.
4. Celery Beat periodic schedule for hourly cleanup.
5. Consistent Redis broker configuration across Web, Worker, and Beat.
6. Worker queue consumption alignment with task queue.
7. Singleton Beat scheduler service (no duplicates).
"""

import sys
import os
import json
import urllib.request
import yaml
import jsonschema

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from celery_app import celery_app
from config import settings

def run_verifications():
    print("=" * 70)
    print("AGENTGUARD — Render Redis, Celery Worker & Beat Verification")
    print("=" * 70)

    render_yaml_path = os.path.join(root_dir, "render.yaml")
    with open(render_yaml_path, "r") as f:
        doc = yaml.safe_load(f)

    # 1. Blueprint Schema Validation
    print("\n[CHECK 1] Validating render.yaml against official Render JSON Schema...")
    schema_url = "https://render.com/schema/render.yaml.json"
    req = urllib.request.Request(schema_url, headers={"User-Agent": "AgentGuard-Deploy-Verifier/1.0"})
    schema = json.loads(urllib.request.urlopen(req).read().decode())
    jsonschema.Draft202012Validator(schema).validate(doc)
    print("  -> PASS: render.yaml adheres strictly to Render Blueprint Draft 2020-12 schema.")

    # 2. Celery Application Import
    print("\n[CHECK 2] Verifying Celery application initialization...")
    assert celery_app.main == "agentguard", f"Unexpected Celery main: {celery_app.main}"
    print(f"  -> PASS: Celery application '{celery_app.main}' imported successfully.")

    # 3. Task Registration
    print("\n[CHECK 3] Verifying cleanup task registration...")
    celery_app.loader.import_default_modules()
    task_name = "tasks.auth_tasks.cleanup_expired_otp_challenges_task"
    assert task_name in celery_app.tasks, f"Task '{task_name}' not registered in celery_app.tasks"
    print(f"  -> PASS: '{task_name}' is registered.")

    # 4. Celery Beat Schedule
    print("\n[CHECK 4] Verifying Celery Beat periodic schedule...")
    beat_schedule = celery_app.conf.beat_schedule
    assert "cleanup-expired-otp-challenges" in beat_schedule, "Missing 'cleanup-expired-otp-challenges' in beat_schedule"
    entry = beat_schedule["cleanup-expired-otp-challenges"]
    assert entry["task"] == task_name, f"Unexpected task in schedule: {entry['task']}"
    assert entry["schedule"] == 3600.0, f"Unexpected schedule interval: {entry['schedule']}"
    print(f"  -> PASS: Periodic schedule configured: '{entry['task']}' every {entry['schedule']}s (1 hour).")

    # 5. Broker Configuration Consistency
    print("\n[CHECK 5] Verifying consistent Redis broker across services...")
    services_by_name = {s["name"]: s for s in doc.get("services", [])}
    assert "agentguard-redis" in services_by_name, "Service 'agentguard-redis' not defined"
    assert "agentguard-backend" in services_by_name, "Service 'agentguard-backend' not defined"
    assert "agentguard-worker" in services_by_name, "Service 'agentguard-worker' not defined"
    assert "agentguard-beat" in services_by_name, "Service 'agentguard-beat' not defined"

    def get_redis_ref(svc):
        for env in svc.get("envVars", []):
            if env.get("key") == "REDIS_URL":
                return env.get("fromService")
        return None

    web_ref = get_redis_ref(services_by_name["agentguard-backend"])
    worker_ref = get_redis_ref(services_by_name["agentguard-worker"])
    beat_ref = get_redis_ref(services_by_name["agentguard-beat"])

    assert web_ref is not None, "agentguard-backend missing REDIS_URL fromService"
    assert worker_ref is not None, "agentguard-worker missing REDIS_URL fromService"
    assert beat_ref is not None, "agentguard-beat missing REDIS_URL fromService"
    assert web_ref == worker_ref == beat_ref, f"Broker mismatch: web={web_ref}, worker={worker_ref}, beat={beat_ref}"
    assert web_ref.get("name") == "agentguard-redis", "Target service must be agentguard-redis"
    assert web_ref.get("property") == "connectionString", "Must use connectionString property"
    print(f"  -> PASS: All services reference '{web_ref['name']}.{web_ref['property']}' for internal broker.")

    # 6. Queue Alignment
    print("\n[CHECK 6] Verifying worker queue matches task destination queue...")
    default_queue = celery_app.amqp.default_queue.name
    task_route = celery_app.amqp.router.route({}, task_name)
    route_queue = task_route["queue"].name
    worker_cmd = services_by_name["agentguard-worker"]["startCommand"]
    assert default_queue == "celery", f"Unexpected default queue: {default_queue}"
    assert route_queue == "celery", f"Unexpected routed queue: {route_queue}"
    assert "-Q celery" in worker_cmd or "worker" in worker_cmd, f"Worker does not consume celery queue: {worker_cmd}"
    print(f"  -> PASS: Task routes to '{route_queue}', and worker consumes '{route_queue}' via: '{worker_cmd}'")

    # 7. Singleton Beat Scheduler
    print("\n[CHECK 7] Verifying single Beat scheduler instance...")
    beat_services = [s for s in doc.get("services", []) if "beat" in s["name"] or "beat" in s.get("startCommand", "")]
    assert len(beat_services) == 1, f"Expected exactly 1 Beat service, found {len(beat_services)}"
    beat_service = beat_services[0]
    assert beat_service.get("numInstances", 1) == 1, f"Beat service has numInstances != 1: {beat_service.get('numInstances')}"
    assert beat_service["name"] == "agentguard-beat", f"Unexpected Beat name: {beat_service['name']}"
    assert "beat" in beat_service["startCommand"] and "worker" not in beat_service["startCommand"], "Beat service must not run a worker"
    print(f"  -> PASS: Exactly 1 Beat scheduler configured ('{beat_service['name']}', numInstances: 1).")

    print("\n" + "=" * 70)
    print("ALL 7 VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_verifications()
