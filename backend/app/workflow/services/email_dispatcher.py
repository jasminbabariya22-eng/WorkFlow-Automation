"""
email_dispatcher.py
Dedicated Background & On-Demand Email Queue Dispatcher.
Processes pending email jobs dynamically from client database tables using SQLAlchemy
schema and table inspection, connects to the configured SMTP server, and delivers actual emails.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import text, inspect

from app.core.logger import logger
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter


class EmailDispatcher:
    """
    Processes and dispatches queued emails dynamically from Client Database tables
    using SMTP credentials configured in client database tables.
    """

    @classmethod
    def get_smtp_config(cls, conn_id: Optional[int] = None, email_server_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Retrieves active SMTP server credentials from client database tables dynamically."""
        search_conns = [conn_id] if conn_id is not None else []
        try:
            from app.workflow.database import WorkflowSessionLocal
            from app.workflow.persistence.models import DatabaseConnection
            with WorkflowSessionLocal() as wf_db:
                db_conns = wf_db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).all()
                for c in db_conns:
                    if c.connection_id not in search_conns:
                        search_conns.append(c.connection_id)
        except Exception:
            pass
        if None not in search_conns:
            search_conns.append(None)

        seen_conns = set()
        for cid in search_conns:
            if cid in seen_conns:
                continue
            seen_conns.add(cid)
            try:
                eng = DynamicEnginePool.get_engine(cid)
                inspector = inspect(eng)
                target_schema = ClientDatabaseAdapter._resolve_target_schema(None, cid)

                available_schemas = []
                try:
                    available_schemas = inspector.get_schema_names()
                except Exception:
                    pass

                schemas_to_check = []
                if target_schema:
                    schemas_to_check.append(target_schema)
                for s in available_schemas:
                    if s not in schemas_to_check and s.lower() not in ("information_schema", "pg_catalog", "pg_toast"):
                        schemas_to_check.append(s)
                if not schemas_to_check:
                    schemas_to_check = [None]

                for sch in schemas_to_check:
                    try:
                        table_names = set(inspector.get_table_names(schema=sch))
                    except Exception:
                        table_names = set()

                    for s_tbl in ["email_server", "mst_email_server", "smtp_settings", "email_config", "email_servers"]:
                        if s_tbl in table_names:
                            tbl = f"{sch}.{s_tbl}" if sch else s_tbl
                            sql = f"SELECT * FROM {tbl}"
                            binds = {}
                            if email_server_id:
                                sql += " WHERE email_server_id = :sid AND is_deleted = 0 LIMIT 1"
                                binds["sid"] = email_server_id
                            else:
                                sql += " WHERE is_deleted = 0 ORDER BY email_server_id ASC LIMIT 1"

                            try:
                                with eng.connect() as conn:
                                    row = conn.execute(text(sql), binds).first()
                                    if row:
                                        return dict(row._mapping)
                            except Exception:
                                pass
            except Exception:
                pass
        return None

    @classmethod
    def send_smtp_email(
        cls,
        smtp_cfg: Dict[str, Any],
        to_email: str,
        subject: str,
        body: str,
        email_type: str = "TEXT",
        cc: Optional[str] = None
    ) -> bool:
        """Connects to SMTP host and sends the email message."""
        host = smtp_cfg.get("outgoing_server_ip")
        port = int(smtp_cfg.get("outgoing_email_port") or 587)
        user = smtp_cfg.get("outgoing_email_user")
        password = smtp_cfg.get("outgoing_email_password")
        encryption = int(smtp_cfg.get("outgoing_email_encryption") or 1)

        if not host or not user or not password:
            raise ValueError(f"Incomplete SMTP configuration for server '{host}' / user '{user}'.")

        msg = MIMEMultipart("alternative")
        msg["From"] = user
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        mime_sub = "html" if (email_type and email_type.upper() == "HTML") else "plain"
        msg.attach(MIMEText(body, mime_sub, "utf-8"))

        recipients = [e.strip() for e in to_email.split(",") if e.strip()]
        if cc:
            recipients.extend([e.strip() for e in cc.split(",") if e.strip()])

        server = None
        try:
            if port == 465 or encryption == 2:
                server = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                server.ehlo()
                if encryption == 1 or port == 587:
                    server.starttls()
                    server.ehlo()

            server.login(user, password)
            server.sendmail(user, recipients, msg.as_string())
            logger.info(f"EmailDispatcher: Successfully sent email to {to_email} with subject '{subject}'")
            return True
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    @classmethod
    def process_pending_email_jobs(cls, conn_id: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
        """
        Dynamically scans client database tables across all configured connections for 'New' or 'Pending'
        emails and sends them immediately.
        """
        target_conns = [conn_id] if conn_id is not None else []
        if not target_conns:
            try:
                from app.workflow.database import WorkflowSessionLocal
                from app.workflow.persistence.models import DatabaseConnection
                with WorkflowSessionLocal() as wf_db:
                    db_conns = wf_db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).all()
                    for c in db_conns:
                        if c.connection_id not in target_conns:
                            target_conns.append(c.connection_id)
            except Exception:
                pass
            if None not in target_conns:
                target_conns.append(None)

        seen_conns = set()

        total_processed = 0
        total_success = 0
        total_failed = 0
        all_details = []

        for cid in target_conns:
            if cid in seen_conns:
                continue
            seen_conns.add(cid)

            try:
                eng = DynamicEnginePool.get_engine(cid)
                inspector = inspect(eng)
                target_schema = ClientDatabaseAdapter._resolve_target_schema(None, cid)
            except Exception:
                continue

            available_schemas = []
            try:
                available_schemas = inspector.get_schema_names()
            except Exception:
                pass

            schemas_to_check = []
            if target_schema:
                schemas_to_check.append(target_schema)
            for s in available_schemas:
                if s not in schemas_to_check and s.lower() not in ("information_schema", "pg_catalog", "pg_toast"):
                    schemas_to_check.append(s)
            if not schemas_to_check:
                schemas_to_check = [None]

            for sch in schemas_to_check:
                try:
                    table_names = set(inspector.get_table_names(schema=sch))
                except Exception:
                    table_names = set()

                for tbl_name in ["mst_email_job", "email_jobs", "email_queue", "mst_email_jobs", "outgoing_emails"]:
                    if tbl_name not in table_names:
                        continue

                    job_table = f"{sch}.{tbl_name}" if sch else tbl_name
                    select_sql = f"""
                        SELECT * FROM {job_table}
                        WHERE send_status IN ('New', 'Pending', 'NEW', 'PENDING')
                          AND is_deleted = 0
                        ORDER BY email_job_id ASC
                        LIMIT :lim
                    """
                    rows = []
                    try:
                        with eng.connect() as conn:
                            rows = [dict(r._mapping) for r in conn.execute(text(select_sql), {"lim": limit})]
                    except Exception:
                        continue

                    if not rows:
                        continue

                    smtp_cache: Dict[int, Dict[str, Any]] = {}

                    for job in rows:
                        job_id = job["email_job_id"]
                        server_id = job.get("email_server_id") or 1
                        to_email = job.get("email_to") or ""
                        subject = job.get("email_subject") or "Notification"
                        body = job.get("email_body") or ""
                        e_type = job.get("email_type") or "TEXT"
                        cc = job.get("email_cc")

                        if not to_email or "@" not in to_email:
                            with eng.begin() as conn:
                                conn.execute(text(f"""
                                    UPDATE {job_table}
                                    SET send_status = 'Invalid_Email', send_attempts = send_attempts + 1
                                    WHERE email_job_id = :jid
                                """), {"jid": job_id})
                            total_failed += 1
                            all_details.append({"job_id": job_id, "status": "Invalid_Email", "to": to_email})
                            continue

                        if server_id not in smtp_cache:
                            cfg = cls.get_smtp_config(cid, server_id)
                            if not cfg:
                                cfg = cls.get_smtp_config(None, server_id)
                            if cfg:
                                smtp_cache[server_id] = cfg

                        smtp_cfg = smtp_cache.get(server_id)
                        if not smtp_cfg:
                            total_failed += 1
                            all_details.append({"job_id": job_id, "status": "No_SMTP_Config", "error": "No active email_server configured."})
                            continue

                        try:
                            cls.send_smtp_email(
                                smtp_cfg=smtp_cfg,
                                to_email=to_email,
                                subject=subject,
                                body=body,
                                email_type=e_type,
                                cc=cc
                            )
                            with eng.begin() as conn:
                                conn.execute(text(f"""
                                    UPDATE {job_table}
                                    SET send_status = 'Sent', send_attempts = send_attempts + 1
                                    WHERE email_job_id = :jid
                                """), {"jid": job_id})
                            total_success += 1
                            all_details.append({"job_id": job_id, "status": "Sent", "to": to_email, "subject": subject})
                        except Exception as send_err:
                            err_msg = str(send_err)[:255]
                            logger.error(f"EmailDispatcher: Error sending email job #{job_id} to {to_email}: {send_err}")
                            with eng.begin() as conn:
                                conn.execute(text(f"""
                                    UPDATE {job_table}
                                    SET send_status = 'Failed', send_attempts = send_attempts + 1
                                    WHERE email_job_id = :jid
                                """), {"jid": job_id})
                            total_failed += 1
                            all_details.append({"job_id": job_id, "status": "Failed", "to": to_email, "error": err_msg})

                    total_processed += len(rows)

        return {
            "processed": total_processed,
            "success": total_success,
            "failed": total_failed,
            "details": all_details
        }
