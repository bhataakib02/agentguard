"""
Phase 6D: Scheduled Report Execution Worker Tasks
Locates due scheduled reports, prevents duplicate concurrent execution,
generates report files, persists storage records with tenant isolation,
and optionally dispatches email delivery.
"""

import os
import datetime
import logging
from typing import Dict, Any, List
from celery_app import celery_app
from database import SessionLocal
import models
from services.storage_service import storage_service
from services.email_service import email_service

logger = logging.getLogger("agentguard.tasks.reports")


def _calculate_next_run(frequency: str, from_time: datetime.datetime) -> datetime.datetime:
    freq = (frequency or "WEEKLY").upper()
    if freq == "DAILY":
        return from_time + datetime.timedelta(days=1)
    elif freq == "MONTHLY":
        return from_time + datetime.timedelta(days=30)
    else:  # WEEKLY default
        return from_time + datetime.timedelta(days=7)


def _generate_report_content(db, org_id: str, report_type: str, file_format: str) -> tuple:
    """
    Generates report bytes and filename using database data.
    """
    fmt_clean = file_format.upper()
    timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"AGENTGUARD_{report_type.upper()}_{timestamp_str}.{fmt_clean.lower() if fmt_clean != 'EXCEL' else 'xlsx'}"

    # Query organization details
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    org_name = org.name if org else "AgentGuard Organization"

    # Query real decision / telemetry counts for content
    decisions_count = db.query(models.Decision).join(models.Agent).filter(models.Agent.org_id == org_id).count()
    agents_count = db.query(models.Agent).filter(models.Agent.org_id == org_id).count()
    policies_count = db.query(models.Policy).filter(models.Policy.org_id == org_id).count()


    if fmt_clean == "PDF":
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1F1F1F"),
            fontName="Times-Bold"
        )
        elements.append(Paragraph(f"AGENTGUARD — {report_type.upper()} REPORT", title_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Organization: {org_name} | Generated: {datetime.datetime.utcnow().isoformat()}Z", styles["Normal"]))
        elements.append(Spacer(1, 15))

        table_data = [
            ["Metric", "Value"],
            ["Total Registered Agents", str(agents_count)],
            ["Active Governance Policies", str(policies_count)],
            ["Total Evaluated Decisions", str(decisions_count)],
            ["Report Frequency Trigger", "SCHEDULED_AUTOMATED_WORKER"],
        ]
        t = Table(table_data, colWidths=[200, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F1F1F')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ]))
        elements.append(t)
        doc.build(elements)
        content_bytes = buffer.getvalue()
        buffer.close()
        return filename, content_bytes

    elif fmt_clean == "EXCEL":
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report Summary"
        ws.append(["AGENTGUARD AUTOMATED SCHEDULED REPORT"])
        ws.append(["Organization", org_name])
        ws.append(["Generated At", datetime.datetime.utcnow().isoformat()])
        ws.append([])
        ws.append(["Metric", "Value"])
        ws.append(["Total Agents", agents_count])
        ws.append(["Active Policies", policies_count])
        ws.append(["Total Decisions", decisions_count])
        buffer = io.BytesIO()
        wb.save(buffer)
        content_bytes = buffer.getvalue()
        buffer.close()
        return filename, content_bytes

    else:  # CSV / Plain
        csv_text = f"Metric,Value\nOrganization,{org_name}\nTotal Agents,{agents_count}\nActive Policies,{policies_count}\nTotal Decisions,{decisions_count}\nGenerated At,{datetime.datetime.utcnow().isoformat()}\n"
        return filename, csv_text.encode("utf-8")


@celery_app.task(name="tasks.report_tasks.execute_scheduled_reports_task")
def execute_scheduled_reports_task() -> Dict[str, Any]:
    """
    Finds due scheduled reports, prevents duplicate concurrent execution,
    generates report files, stores them, and updates schedule next run time.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        # Find active reports where next_run_at <= now or last_run_at is None
        due_reports = db.query(models.ScheduledReport).filter(
            models.ScheduledReport.status == "ACTIVE"
        ).all()

        executed_count = 0
        skipped_count = 0

        for sched in due_reports:
            # Check due condition
            is_due = (sched.last_run_at is None) or (sched.next_run_at and sched.next_run_at <= now)
            if not is_due:
                skipped_count += 1
                continue

            # Concurrency prevention: mark PROCESSING briefly
            sched.status = "PROCESSING"
            db.commit()

            try:
                # 1. Generate Report
                filename, content_bytes = _generate_report_content(
                    db=db,
                    org_id=str(sched.org_id),
                    report_type=sched.report_type,
                    file_format=sched.file_format or "PDF"
                )

                # 2. Store via StorageService
                storage_res = storage_service.save_report_file(
                    content=content_bytes,
                    filename=filename,
                    org_id=str(sched.org_id),
                    format_type=sched.file_format or "PDF"
                )

                # 3. Create ReportHistory
                rep_hist = models.ReportHistory(
                    org_id=sched.org_id,
                    user_id=sched.user_id,
                    report_type=sched.report_type,
                    title=sched.title or f"Scheduled {sched.report_type} Report",
                    file_format=(sched.file_format or "PDF").upper(),
                    file_path=storage_res["file_path"],
                    file_size_bytes=storage_res["file_size_bytes"],
                    filters_json={"scheduled_report_id": str(sched.id), "trigger": "CELERY_BEAT"}
                )
                db.add(rep_hist)

                # 4. Update Schedule
                sched.last_run_at = now
                sched.next_run_at = _calculate_next_run(sched.frequency, now)
                sched.status = "ACTIVE"
                db.commit()

                # 5. Audit Log
                audit = models.AuditLog(
                    event_type="SCHEDULED_REPORT_EXECUTED",
                    actor_type="SYSTEM",
                    actor_id="REPORT_SCHEDULER_WORKER",
                    action=f"Executed scheduled report: {sched.report_type} for org {sched.org_id}",
                    resource=f"scheduled_report:{sched.id}",
                    result="SUCCESS",
                    metadata_json={
                        "schedule_id": str(sched.id),
                        "org_id": str(sched.org_id),
                        "report_history_id": str(rep_hist.id),
                        "file_size": storage_res["file_size_bytes"],
                        "storage_backend": storage_res["storage_backend"]
                    }
                )
                db.add(audit)
                db.commit()

                # 6. Email Delivery if recipients configured
                if sched.recipient_emails and email_service.is_configured():
                    for email in sched.recipient_emails.split(","):
                        clean_email = email.strip()
                        if clean_email:
                            email_service.send_email(
                                to_email=clean_email,
                                subject=f"AGENTGUARD Report: {sched.title}",
                                body_text=f"Your scheduled {sched.report_type} report has been generated.",
                                attachments=[{"filename": filename, "content": content_bytes}]
                            )

                executed_count += 1
                logger.info(f"[execute_scheduled_reports_task] Successfully executed schedule {sched.id}")

            except Exception as e:
                logger.error(f"[execute_scheduled_reports_task] Failed executing schedule {sched.id}: {e}")
                sched.status = "ACTIVE"  # Reset status
                db.commit()

        return {
            "status": "SUCCESS",
            "executed_count": executed_count,
            "skipped_count": skipped_count
        }

    finally:
        db.close()
