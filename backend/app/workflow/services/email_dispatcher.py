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
        """Connects to SMTP host and sends the email message with enterprise diagnostics."""
        import socket
        import time

        host = smtp_cfg.get("outgoing_server_ip")
        port = int(smtp_cfg.get("outgoing_email_port") or 587)
        user = smtp_cfg.get("outgoing_email_user")
        password = smtp_cfg.get("outgoing_email_password")
        encryption = int(smtp_cfg.get("outgoing_email_encryption") or 1)

        if not host or not user or not password:
            err_detail = f"Incomplete SMTP configuration (Host: '{host}', User: '{user}'). Please configure valid credentials in email_server settings."
            logger.error(f"[EMAIL_DISPATCHER] Configuration Error: {err_detail}")
            raise ValueError(err_detail)

        enc_label = "SSL" if (port == 465 or encryption == 2) else ("STARTTLS" if (encryption == 1 or port == 587) else "PLAIN")
        logger.info(f"[EMAIL_DISPATCHER] Connecting to SMTP server {host}:{port} via {enc_label} (Sender: {user})")

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
        start_ts = time.time()
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
            duration_ms = round((time.time() - start_ts) * 1000, 2)
            logger.info(f"[EMAIL_DISPATCHER] SUCCESS: Delivered email to {to_email} (Subject: '{subject}') in {duration_ms}ms")
            return True
        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error(f"[EMAIL_DISPATCHER] SMTP Authentication Failed for '{user}' on {host}:{port} -> {auth_err}")
            raise RuntimeError(f"SMTP Authentication Failed (Code {auth_err.smtp_code}): {auth_err.smtp_error.decode('utf-8', errors='ignore') if isinstance(auth_err.smtp_error, bytes) else auth_err.smtp_error}") from auth_err
        except (smtplib.SMTPConnectError, socket.timeout, TimeoutError) as conn_err:
            logger.error(f"[EMAIL_DISPATCHER] SMTP Connection Timeout/Failed to {host}:{port} -> {conn_err}")
            raise RuntimeError(f"SMTP Connection Timeout to {host}:{port}: {conn_err}") from conn_err
        except smtplib.SMTPRecipientsRefused as rec_err:
            logger.error(f"[EMAIL_DISPATCHER] SMTP Recipients Refused for {to_email} -> {rec_err}")
            raise RuntimeError(f"SMTP Recipient Refused ({to_email}): {rec_err}") from rec_err
        except Exception as ex:
            logger.error(f"[EMAIL_DISPATCHER] Unexpected SMTP Delivery Error: {ex}", exc_info=True)
            raise
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
        emails and sends them immediately. Automatically recovers stale 'Processing' jobs.
        """
        import time
        from datetime import timedelta
        from app.core.logger import WorkflowTelemetryLogger

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
            except Exception as eng_ex:
                logger.debug(f"[EMAIL_DISPATCHER] Connection #{cid} engine unresolvable: {eng_ex}")
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

                    # Dynamic column inspection to prevent SQL column errors
                    try:
                        cols_info = inspector.get_columns(tbl_name, schema=sch)
                        cols = {c["name"].lower(): c["name"] for c in cols_info}
                    except Exception:
                        cols = {}

                    pk_col = cols.get("email_job_id") or cols.get("id") or cols.get("job_id") or "email_job_id"
                    status_col = cols.get("send_status") or cols.get("status") or "send_status"
                    attempts_col = cols.get("send_attempts") or cols.get("attempts")
                    total_attempts_col = cols.get("total_attempts") or cols.get("max_attempts")
                    delay_col = cols.get("attempt_delay") or cols.get("delay")
                    next_attempt_col = cols.get("next_attempt_at") or cols.get("next_retry_at")
                    sent_on_col = cols.get("sent_on") or cols.get("sent_date")
                    deleted_col = cols.get("is_deleted")
                    created_col = cols.get("created_on") or cols.get("created_at")
                    error_col = cols.get("error_message") or cols.get("error") or cols.get("last_error") or cols.get("remarks")

                    now_dt = datetime.now()
                    job_table = f"{sch}.{tbl_name}" if sch else tbl_name

                    # 1. AUTO-RECOVER STALE 'Processing' JOBS (older than 45 seconds)
                    try:
                        stale_cutoff = now_dt - timedelta(seconds=45)
                        recover_where = [f"{status_col} = 'Processing'"]
                        if created_col:
                            recover_where.append(f"{created_col} <= :stale_cutoff")
                        if attempts_col and total_attempts_col:
                            recover_sql = f"""
                                UPDATE {job_table}
                                SET {status_col} = CASE
                                        WHEN COALESCE({attempts_col}, 0) >= COALESCE({total_attempts_col}, 3) THEN 'Failed'
                                        ELSE 'Pending'
                                    END
                                WHERE {" AND ".join(recover_where)}
                            """
                        else:
                            recover_sql = f"""
                                UPDATE {job_table}
                                SET {status_col} = 'Pending'
                                WHERE {" AND ".join(recover_where)}
                            """
                        with eng.begin() as conn:
                            rec_res = conn.execute(text(recover_sql), {"stale_cutoff": stale_cutoff})
                            if rec_res.rowcount and rec_res.rowcount > 0:
                                logger.warning(f"[EMAIL_DISPATCHER] Auto-recovered {rec_res.rowcount} orphaned 'Processing' email jobs in '{job_table}' back to Pending/Failed.")
                    except Exception as rec_ex:
                        logger.debug(f"[EMAIL_DISPATCHER] Stale recovery note: {rec_ex}")

                    # 2. SELECT CANDIDATE EMAIL JOBS
                    where_clauses = [f"{status_col} IN ('New', 'Pending', 'NEW', 'PENDING')"]
                    if deleted_col:
                        where_clauses.append(f"({deleted_col} = 0 OR {deleted_col} IS NULL)")
                    if attempts_col and total_attempts_col:
                        where_clauses.append(f"(COALESCE({attempts_col}, 0) < COALESCE({total_attempts_col}, 3) OR {total_attempts_col} = 0)")
                    elif attempts_col:
                        where_clauses.append(f"(COALESCE({attempts_col}, 0) < 3)")
                    if next_attempt_col:
                        where_clauses.append(f"({next_attempt_col} IS NULL OR {next_attempt_col} <= :now_dt)")

                    select_sql = f"""
                        SELECT * FROM {job_table}
                        WHERE {" AND ".join(where_clauses)}
                        ORDER BY {pk_col} ASC
                    """
                    rows = []
                    try:
                        with eng.connect() as conn:
                            binds = {"now_dt": now_dt} if next_attempt_col else {}
                            rows = [dict(r._mapping) for r in conn.execute(text(select_sql), binds).fetchmany(limit)]
                    except Exception as select_ex:
                        logger.error(f"[EMAIL_DISPATCHER] Query failed on {job_table}: {select_ex}")
                        continue

                    if not rows:
                        continue

                    logger.info(f"[EMAIL_DISPATCHER] Found {len(rows)} pending email job(s) in '{job_table}' to process.")
                    smtp_cache: Dict[int, Dict[str, Any]] = {}

                    for job in rows:
                        job_id = job.get(pk_col) or job.get("email_job_id") or job.get("id")
                        raw_tot = job.get(total_attempts_col) if total_attempts_col else 3
                        try:
                            total_attempts = int(raw_tot) if raw_tot is not None and str(raw_tot).strip() != "" else 3
                        except Exception:
                            total_attempts = 3

                        raw_att = job.get(attempts_col) if attempts_col else 0
                        try:
                            curr_attempts = int(raw_att) if raw_att is not None and str(raw_att).strip() != "" else 0
                        except Exception:
                            curr_attempts = 0

                        raw_delay = job.get(delay_col) if delay_col else 5000
                        try:
                            attempt_delay_ms = int(raw_delay) if raw_delay is not None and str(raw_delay).strip() != "" else 5000
                        except Exception:
                            attempt_delay_ms = 5000

                        # 3. ATOMIC CLAIM: Mark job as 'Processing' and increment attempts atomically
                        claim_set = [f"{status_col} = 'Processing'"]
                        if attempts_col:
                            claim_set.append(f"{attempts_col} = COALESCE({attempts_col}, 0) + 1")

                        claim_where = [
                            f"{pk_col} = :jid",
                            f"{status_col} IN ('New', 'Pending', 'NEW', 'PENDING')"
                        ]
                        if attempts_col and total_attempts_col:
                            claim_where.append(f"(COALESCE({attempts_col}, 0) < COALESCE({total_attempts_col}, 3) OR {total_attempts_col} = 0)")

                        claim_sql = f"""
                            UPDATE {job_table}
                            SET {', '.join(claim_set)}
                            WHERE {' AND '.join(claim_where)}
                        """
                        with eng.begin() as conn:
                            claim_res = conn.execute(text(claim_sql), {"jid": job_id})
                            if claim_res.rowcount == 0:
                                # Another worker claimed or reached max attempts
                                continue

                        new_attempt_count = curr_attempts + 1
                        logger.info(f"[EMAIL_DISPATCHER] Claimed Job #{job_id} [Attempt {new_attempt_count}/{total_attempts}] for processing.")

                        # Guaranteed processing block
                        job_start_time = time.time()
                        try:
                            server_id = job.get("email_server_id") or 1
                            to_email = str(job.get("to_email") or job.get("email_to") or job.get("recipient") or "").strip()
                            subject = str(job.get("subject") or job.get("email_subject") or "Notification")
                            body = str(job.get("body") or job.get("email_body") or "")
                            e_type = str(job.get("email_type") or "TEXT")
                            cc = job.get("cc_email") or job.get("email_cc") or job.get("cc")

                            if not to_email or "@" not in to_email:
                                err_msg = f"Invalid recipient email address: '{to_email}'"
                                logger.warning(f"[EMAIL_DISPATCHER] Job #{job_id} Rejected: {err_msg}")
                                invalid_set = [f"{status_col} = 'Invalid_Email'"]
                                binds = {"jid": job_id}
                                if error_col:
                                    invalid_set.append(f"{error_col} = :err")
                                    binds["err"] = err_msg
                                with eng.begin() as conn:
                                    conn.execute(text(f"""
                                        UPDATE {job_table}
                                        SET {', '.join(invalid_set)}
                                        WHERE {pk_col} = :jid
                                    """), binds)
                                total_failed += 1
                                all_details.append({"job_id": job_id, "status": "Invalid_Email", "to": to_email, "error": err_msg})
                                continue

                            if server_id not in smtp_cache:
                                cfg = cls.get_smtp_config(cid, server_id)
                                if not cfg:
                                    cfg = cls.get_smtp_config(None, server_id)
                                if cfg:
                                    smtp_cache[server_id] = cfg

                            smtp_cfg = smtp_cache.get(server_id)
                            if not smtp_cfg:
                                err_msg = f"No active SMTP configuration found for email_server_id #{server_id}."
                                logger.error(f"[EMAIL_DISPATCHER] Job #{job_id} Failed: {err_msg}")
                                fail_set = [f"{status_col} = 'Failed'"]
                                binds = {"jid": job_id}
                                if error_col:
                                    fail_set.append(f"{error_col} = :err")
                                    binds["err"] = err_msg
                                with eng.begin() as conn:
                                    conn.execute(text(f"""
                                        UPDATE {job_table}
                                        SET {', '.join(fail_set)}
                                        WHERE {pk_col} = :jid
                                    """), binds)
                                total_failed += 1
                                all_details.append({"job_id": job_id, "status": "No_SMTP_Config", "error": err_msg})
                                continue

                            cls.send_smtp_email(
                                smtp_cfg=smtp_cfg,
                                to_email=to_email,
                                subject=subject,
                                body=body,
                                email_type=e_type,
                                cc=cc
                            )

                            # 4. MARK AS SENT
                            sent_set = [f"{status_col} = 'Sent'"]
                            binds = {"jid": job_id}
                            if sent_on_col:
                                sent_set.append(f"{sent_on_col} = :sent_dt")
                                binds["sent_dt"] = datetime.now()
                            if error_col:
                                sent_set.append(f"{error_col} = NULL")

                            with eng.begin() as conn:
                                conn.execute(text(f"""
                                    UPDATE {job_table}
                                    SET {', '.join(sent_set)}
                                    WHERE {pk_col} = :jid
                                """), binds)

                            exec_ms = round((time.time() - job_start_time) * 1000, 2)
                            logger.info(f"[EMAIL_DISPATCHER] Job #{job_id} Successfully Delivered to {to_email} ({exec_ms}ms)")
                            
                            try:
                                WorkflowTelemetryLogger.log_audit_event(
                                    action_name="SEND_EMAIL_DISPATCHED",
                                    message=f"Email Job #{job_id} delivered to {to_email} (Subject: '{subject}')",
                                    details={"job_id": job_id, "to": to_email, "subject": subject, "duration_ms": exec_ms}
                                )
                            except Exception:
                                pass

                            total_success += 1
                            all_details.append({"job_id": job_id, "status": "Sent", "to": to_email, "subject": subject})

                        except Exception as send_err:
                            err_msg = str(send_err)[:255]
                            logger.error(f"[EMAIL_DISPATCHER] Job #{job_id} Delivery Error on Attempt {new_attempt_count}/{total_attempts}: {send_err}")
                            
                            next_dt = datetime.now() + timedelta(milliseconds=attempt_delay_ms)
                            is_failed = (total_attempts > 0 and new_attempt_count >= total_attempts)
                            final_status = 'Failed' if is_failed else 'Pending'

                            if is_failed:
                                logger.warning(f"[EMAIL_DISPATCHER] Job #{job_id} Permanently FAILED after {new_attempt_count} attempts. Reason: {err_msg}")
                            else:
                                logger.info(f"[EMAIL_DISPATCHER] Job #{job_id} Scheduled retry #{new_attempt_count + 1} at {next_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                            # 5. MARK AS PENDING / FAILED SAFELY
                            fail_set = [f"{status_col} = :st"]
                            binds = {"st": final_status, "jid": job_id}
                            if next_attempt_col:
                                fail_set.append(f"{next_attempt_col} = :nxt")
                                binds["nxt"] = next_dt
                            if error_col:
                                fail_set.append(f"{error_col} = :err")
                                binds["err"] = err_msg

                            try:
                                with eng.begin() as conn:
                                    conn.execute(text(f"""
                                        UPDATE {job_table}
                                        SET {', '.join(fail_set)}
                                        WHERE {pk_col} = :jid
                                    """), binds)
                            except Exception as update_err:
                                logger.error(f"[EMAIL_DISPATCHER] Fallback update error for job #{job_id}: {update_err}")

                            try:
                                WorkflowTelemetryLogger.log_error(
                                    message=f"Email Job #{job_id} Delivery Failed [Attempt {new_attempt_count}/{total_attempts}]",
                                    error=err_msg,
                                    details={"job_id": job_id, "to": to_email, "status": final_status, "attempts": new_attempt_count}
                                )
                            except Exception:
                                pass

                            total_failed += 1
                            all_details.append({"job_id": job_id, "status": final_status, "to": to_email, "error": err_msg})

                    total_processed += len(rows)

        return {
            "processed": total_processed,
            "success": total_success,
            "failed": total_failed,
            "details": all_details
        }
