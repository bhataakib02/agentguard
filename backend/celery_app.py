"""
Phase 6D: Celery Application and Worker Architecture for AgentGuard
Configures Celery distributed tasks, broker connections, periodic Beat schedules,
and health inspection.
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab
from config import settings

logger = logging.getLogger("agentguard.celery")

# Broker fallback logic:
# If CELERY_TASK_ALWAYS_EAGER is enabled or REDIS_URL is not provided, use memory broker for offline tests.
broker_url = settings.CELERY_BROKER_URL
if settings.CELERY_TASK_ALWAYS_EAGER and not settings.REDIS_URL:
    broker_url = "memory://"

result_backend = settings.CELERY_RESULT_BACKEND
if settings.CELERY_TASK_ALWAYS_EAGER and not settings.REDIS_URL:
    result_backend = "cache+memory://"

celery_app = Celery(
    "agentguard",
    broker=broker_url,
    backend=result_backend,
    include=[
        "tasks.webhook_tasks",
        "tasks.report_tasks",
        "tasks.notification_tasks",
        "tasks.escalation_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,

    # Periodic Beat Schedule
    beat_schedule={
        "execute-scheduled-reports": {
            "task": "tasks.report_tasks.execute_scheduled_reports_task",
            "schedule": 900.0,  # Every 15 minutes
        },
        "escalate-overdue-approvals": {
            "task": "tasks.escalation_tasks.escalate_approvals_task",
            "schedule": 1800.0,  # Every 30 minutes
        },
        "retry-pending-webhooks": {
            "task": "tasks.webhook_tasks.retry_pending_webhooks_task",
            "schedule": 300.0,  # Every 5 minutes
        },
    }
)


def inspect_broker_health() -> dict:
    """
    Checks whether the Celery broker (Redis) is reachable.
    Does not expose sensitive credentials in URLs.
    """
    if not settings.REDIS_URL and not settings.CELERY_BROKER_URL.startswith("redis"):
        return {
            "status": "NOT_CONFIGURED",
            "provider": "REDIS",
            "connected": False,
            "latency_ms": None
        }

    target_url = settings.REDIS_URL or settings.CELERY_BROKER_URL
    import time
    try:
        import redis
        t0 = time.time()
        # Parse connection safely with short timeout
        r = redis.from_url(target_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        ping_res = r.ping()
        latency = round((time.time() - t0) * 1000, 2)
        return {
            "status": "HEALTHY" if ping_res else "DEGRADED",
            "provider": "REDIS",
            "connected": bool(ping_res),
            "latency_ms": latency
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "provider": "REDIS",
            "connected": False,
            "latency_ms": None,
            "error_type": type(e).__name__
        }


def inspect_worker_health() -> dict:
    """
    Inspects active Celery workers via broadcast ping.
    """
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return {
            "status": "HEALTHY",
            "mode": "EAGER_INLINE",
            "active_workers": 1,
            "registered_tasks": list(celery_app.tasks.keys())
        }

    broker_status = inspect_broker_health()
    if not broker_status.get("connected"):
        return {
            "status": "UNAVAILABLE",
            "mode": "DISTRIBUTED",
            "active_workers": 0,
            "error": "Broker unreachable"
        }

    try:
        insp = celery_app.control.inspect(timeout=1.0)
        ping_res = insp.ping() or {}
        active_count = len(ping_res)
        return {
            "status": "HEALTHY" if active_count > 0 else "DEGRADED",
            "mode": "DISTRIBUTED",
            "active_workers": active_count,
            "worker_nodes": list(ping_res.keys())
        }
    except Exception as e:
        return {
            "status": "UNAVAILABLE",
            "mode": "DISTRIBUTED",
            "active_workers": 0,
            "error": str(e)
        }
