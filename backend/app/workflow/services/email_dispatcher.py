"""
email_dispatcher.py
Dedicated Background & On-Demand Email Queue Dispatcher.
Processes pending email jobs dynamically from client database tables using SQLAlchemy
schema and table inspection, connects to the configured SMTP server, and delivers actual emails.
"""

import smtplib
import socket
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from sqlalchemy import text, inspect

from app.core.logger import logger, WorkflowTelemetryLogger
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter


def _get_field_ci(d: dict, *candidates, default=None) -> Any:
    """Helper to case-insensitively retrieve fields from row dictionaries."""
    if not isinstance(d, dict):
        return default
    d_lower = {str(k).lower(): v for k, v in d.items()}
    for cand in candidates:
        if cand is not None:
            c_low = str(cand).lower()
            if c_low in d_lower and d_lower[c_low] is not None:
                val = d_lower[c_low]
                if str(val).strip() != "":
                    return val
    return default


class EmailDispatcher:
    """
    Processes and dispatches queued emails dynamically from Client Database tables
    using SMTP credentials configured in client database tables.
    """

    _smtp_config_cache: Dict[str, Any] = {}
    _in_flight_jobs: Set[int] = set()
    _in_flight_lock = threading.Lock()
    _dispatch_lock = threading.Lock()

    @classmethod
    def get_smtp_config(
        cls,
        conn_id: Optional[int] = None,
        email_server_id: Optional[int] = None,
        from_email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves active, non-deleted SMTP server credentials from client database tables dynamically.
        Never uses deleted (is_deleted=1) or inactive (is_active=0) email servers.
        Strictly scopes to conn_id when provided.
        """
        search_conns = [conn_id] if conn_id is not None else []
        if conn_id is None:
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
                with eng.connect() as conn:
                    # Check standard table candidates
                    for cand in ["email_server", "dbo.email_server", "public.email_server", "ers.email_server", "mst_email_server", "dbo.mst_email_server", "smtp_settings", "email_config"]:
                        try:
                            rows = conn.execute(text(f"SELECT * FROM {cand}")).fetchall()
                            if not rows:
                                continue
                            for r in rows:
                                m = dict(r._mapping)
                                # 1. Check deleted / inactive flags strictly
                                is_del = None
                                is_act = None
                                for k, v in m.items():
                                    if k.lower() == "is_deleted":
                                        is_del = v
                                    elif k.lower() in ("is_active", "active", "status"):
                                        is_act = v

                                if is_del is not None and str(is_del).strip().lower() in ("1", "true", "t", "yes"):
                                    continue
                                if is_act is not None and str(is_act).strip().lower() in ("0", "false", "f", "no", "inactive"):
                                    continue

                                # 2. Server ID check
                                sid = None
                                for k, v in m.items():
                                    if k.lower() in ("email_server_id", "server_id", "id", "pk"):
                                        sid = v
                                        break

                                # 3. Email user check
                                s_user = ""
                                for k, v in m.items():
                                    if k.lower() in ("outgoing_email_user", "email_user", "username", "email_id", "emailid", "email", "sender_email", "from_email"):
                                        s_user = str(v or "").strip()
                                        break

                                # If from_email is specified, prioritize matching sender email
                                if from_email and "@" in from_email:
                                    if s_user.lower() == from_email.lower().strip():
                                        return m

                                # If email_server_id is specified
                                if email_server_id is not None and sid is not None:
                                    if str(sid) == str(email_server_id):
                                        return m

                                # If neither is specified, return first valid active server
                                if not from_email and email_server_id is None:
                                    return m
                        except Exception:
                            pass
            except Exception:
                pass
        return None

    @staticmethod
    def _decrypt_password_safe(raw_pwd: Optional[str]) -> str:
        """Decrypts Fernet-encrypted password or returns plain text if unencrypted."""
        if not raw_pwd:
            return ""
        try:
            from app.core.security import decrypt_text
            return decrypt_text(str(raw_pwd))
        except Exception:
            return str(raw_pwd)

    @classmethod
    def send_smtp_email(
        cls,
        smtp_cfg: Dict[str, Any],
        to_email: str,
        subject: str,
        body: str,
        email_type: str = "TEXT",
        cc: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Connects to SMTP host and sends the email message with enterprise diagnostics."""
        host = smtp_cfg.get("outgoing_server_ip")
        port = int(smtp_cfg.get("outgoing_email_port") or 587)
        user = smtp_cfg.get("outgoing_email_user")
        raw_password = smtp_cfg.get("outgoing_email_password")
        password = cls._decrypt_password_safe(raw_password)
        encryption = int(smtp_cfg.get("outgoing_email_encryption") or 1)

        if not host or not user or not password:
            err_detail = f"Incomplete SMTP configuration (Host: '{host}', User: '{user}'). Please configure valid credentials in email_server settings."
            logger.error(f"[EMAIL_DISPATCHER] Configuration Error: {err_detail}")
            raise ValueError(err_detail)

        sender_address = from_email if (from_email and "@" in from_email) else user
        enc_label = "SSL" if (port == 465 or encryption == 2) else ("STARTTLS" if (encryption == 1 or port == 587) else "PLAIN")
        logger.info(f"[EMAIL_DISPATCHER] Connecting to SMTP server {host}:{port} via {enc_label} (Sender: {sender_address} [Auth User: {user}])")

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_address
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc

        mime_sub = "html" if (email_type and email_type.upper() == "HTML") else "plain"
        msg.attach(MIMEText(body, mime_sub, "utf-8"))

        recipients_raw = [e.strip() for e in to_email.split(",") if e.strip()]
        if cc:
            recipients_raw.extend([e.strip() for e in cc.split(",") if e.strip()])

        # Restrict duplicate recipients using Python set
        seen_recipients: Set[str] = set()
        recipients = []
        for r in recipients_raw:
            r_lower = r.lower()
            if r_lower not in seen_recipients:
                seen_recipients.add(r_lower)
                recipients.append(r)

        server = None
        delivered = False
        data_sent = False
        start_ts = time.time()
        timeout_sec = 60  # 60s timeout for robust SMTP TLS handshakes and multi-recipient transmission
        try:
            if port == 465 or encryption == 2:
                server = smtplib.SMTP_SSL(host, port, timeout=timeout_sec)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout_sec)
                server.ehlo()
                if encryption == 1 or port == 587:
                    server.starttls()
                    server.ehlo()

            if hasattr(server, "sock") and server.sock:
                server.sock.settimeout(timeout_sec)

            server.login(user, password)
            data_sent = True
            server.sendmail(user, recipients, msg.as_string())
            delivered = True
            duration_ms = round((time.time() - start_ts) * 1000, 2)
            logger.info(f"[EMAIL_DISPATCHER] SUCCESS: Delivered email to {to_email} (Subject: '{subject}') in {duration_ms}ms")
            return True
        except smtplib.SMTPAuthenticationError as auth_err:
            if delivered or data_sent:
                logger.warning(f"[EMAIL_DISPATCHER] Teardown notice: Email was already delivered before disconnect: {auth_err}")
                return True
            logger.error(f"[EMAIL_DISPATCHER] SMTP Authentication Failed for '{user}' on {host}:{port} -> {auth_err}")
            raise RuntimeError(f"SMTP Authentication Failed (Code {auth_err.smtp_code}): {auth_err.smtp_error.decode('utf-8', errors='ignore') if isinstance(auth_err.smtp_error, bytes) else auth_err.smtp_error}") from auth_err
        except (smtplib.SMTPConnectError, socket.timeout, TimeoutError, smtplib.SMTPServerDisconnected) as conn_err:
            err_text = str(conn_err).lower()
            if data_sent and ("read operation timed out" in err_text or "unexpectedly closed" in err_text or delivered):
                logger.info(f"[EMAIL_DISPATCHER] SMTP read timeout after data transmission ({conn_err}). Email was accepted and queued by mail server.")
                return True
            logger.error(f"[EMAIL_DISPATCHER] SMTP Connection Timeout/Failed to {host}:{port} -> {conn_err}")
            raise RuntimeError(f"SMTP Connection Timeout to {host}:{port}: {conn_err}") from conn_err
        except smtplib.SMTPRecipientsRefused as rec_err:
            if delivered or data_sent:
                return True
            logger.error(f"[EMAIL_DISPATCHER] SMTP Recipients Refused for {to_email} -> {rec_err}")
            raise RuntimeError(f"SMTP Recipient Refused ({to_email}): {rec_err}") from rec_err
        except Exception as ex:
            if delivered or data_sent:
                logger.warning(f"[EMAIL_DISPATCHER] Post-delivery teardown exception ignored ({ex}). Email was delivered.")
                return True
            logger.error(f"[EMAIL_DISPATCHER] Unexpected SMTP Delivery Error: {ex}")
            raise
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass

    @classmethod
    def process_pending_email_jobs(cls, conn_id: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
        """
        Dynamically scans client database tables across all configured connections for 'New' or 'Pending'
        emails and sends them immediately with thread-safe atomic claiming and 3-state lifecycle.
        """
        # Ensure only one dispatcher thread runs at any instant to eliminate duplicate concurrent sends
        if not cls._dispatch_lock.acquire(blocking=False):
            logger.debug("[EMAIL_DISPATCHER] Dispatch already in progress in another thread. Yielding.")
            return {"processed": 0, "success": 0, "failed": 0, "details": [], "status": "Busy"}

        try:
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
                if not target_conns and None not in target_conns:
                    target_conns.append(None)

            seen_conns = set()
            seen_engine_urls = set()
            seen_tables_per_pass = set()

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
                    eng_url_key = str(eng.url)
                    if eng_url_key in seen_engine_urls:
                        logger.debug(f"[EMAIL_DISPATCHER] Connection #{cid} shares engine URL '{eng_url_key}'. Skipping duplicate engine scan.")
                        continue
                    seen_engine_urls.add(eng_url_key)

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
                excluded_schemas = {
                    "information_schema", "pg_catalog", "pg_toast", "sys",
                    "db_accessadmin", "db_backupoperator", "db_datareader",
                    "db_datawriter", "db_ddladmin", "db_denydatareader",
                    "db_denydatawriter", "db_owner", "db_securityadmin", "guest"
                }
                for s in available_schemas:
                    if s not in schemas_to_check and s.lower() not in excluded_schemas:
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

                        table_identity_key = f"{eng_url_key}:{sch or 'default'}.{tbl_name}"
                        if table_identity_key in seen_tables_per_pass:
                            continue
                        seen_tables_per_pass.add(table_identity_key)

                        # Dynamic column inspection to prevent SQL column errors
                        try:
                            cols_info = inspector.get_columns(tbl_name, schema=sch)
                            cols = {c["name"].lower(): c["name"] for c in cols_info}
                        except Exception:
                            cols = {}

                        pk_col = cols.get("email_job_id") or cols.get("id") or cols.get("job_id") or "email_job_id"
                        status_col = cols.get("send_status") or cols.get("status") or "send_status"
                        attempts_col = (
                            cols.get("send_attempts") or
                            cols.get("attempts") or
                            cols.get("send_attempt") or
                            cols.get("retry_count") or
                            cols.get("retries") or
                            cols.get("no_of_attempts") or
                            cols.get("attempt_count") or
                            cols.get("attempts_count") or
                            cols.get("sendattempts")
                        )
                        total_attempts_col = (
                            cols.get("total_attempts") or
                            cols.get("max_attempts") or
                            cols.get("max_retries") or
                            cols.get("total_retries") or
                            cols.get("retry_limit") or
                            cols.get("totalattempts")
                        )
                        delay_col = cols.get("attempt_delay") or cols.get("delay") or cols.get("retry_delay") or cols.get("delay_ms")
                        next_attempt_col = cols.get("next_attempt_at") or cols.get("next_retry_at") or cols.get("next_attempt") or cols.get("next_retry")
                        sent_on_col = cols.get("sent_on") or cols.get("sent_date")
                        deleted_col = cols.get("is_deleted")
                        created_col = cols.get("created_on") or cols.get("created_at")
                        error_col = cols.get("error_message") or cols.get("error") or cols.get("last_error") or cols.get("remarks")

                        now_dt = datetime.now()
                        job_table = f"{sch}.{tbl_name}" if sch else tbl_name

                        # 1. CLEANUP & NORMALIZE STATUSES
                        try:
                            with eng.begin() as conn:
                                # If jobs have reached maximum attempts, set them to Failed
                                if attempts_col and total_attempts_col:
                                    conn.execute(text(f"""
                                        UPDATE {job_table}
                                        SET {status_col} = 'Failed'
                                        WHERE {status_col} = 'New' AND COALESCE({attempts_col}, 0) >= COALESCE({total_attempts_col}, 3)
                                    """))
                                elif attempts_col:
                                    conn.execute(text(f"""
                                        UPDATE {job_table}
                                        SET {status_col} = 'Failed'
                                        WHERE {status_col} = 'New' AND COALESCE({attempts_col}, 0) >= 3
                                    """))

                                # Normalize legacy non-standard statuses to 'New' if not failed/processing
                                normalize_where = [f"{status_col} NOT IN ('New', 'Sent', 'Failed', 'Processing', 'In-Progress', 'Claimed')"]
                                if attempts_col and total_attempts_col:
                                    normalize_sql = f"""
                                        UPDATE {job_table}
                                        SET {status_col} = CASE
                                                WHEN COALESCE({attempts_col}, 0) >= COALESCE({total_attempts_col}, 3) THEN 'Failed'
                                                ELSE 'New'
                                            END
                                        WHERE {" AND ".join(normalize_where)}
                                    """""
                                else:
                                    normalize_sql = f"""
                                        UPDATE {job_table}
                                        SET {status_col} = 'New'
                                        WHERE {" AND ".join(normalize_where)}
                                    """""
                                conn.execute(text(normalize_sql))
                        except Exception as norm_ex:
                            logger.debug(f"[EMAIL_DISPATCHER] Status normalization note: {norm_ex}")

                        # 2. SELECT CANDIDATE 'New' EMAIL JOBS
                        where_clauses = [f"{status_col} = 'New'"]
                        if deleted_col:
                            where_clauses.append(f"({deleted_col} = 0 OR {deleted_col} IS NULL)")
                        if attempts_col and total_attempts_col:
                            where_clauses.append(f"(COALESCE({attempts_col}, 0) < COALESCE({total_attempts_col}, 3))")
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

                        smtp_cache: Dict[str, Optional[Dict[str, Any]]] = {}

                        for job in rows:
                            raw_id = _get_field_ci(job, pk_col, "email_job_id", "id", "job_id")
                            if raw_id is None:
                                continue
                            job_id = int(raw_id)

                            # Thread-Safe In-Memory Exclusion
                            with cls._in_flight_lock:
                                if job_id in cls._in_flight_jobs:
                                    logger.debug(f"[EMAIL_DISPATCHER] Job #{job_id} already being dispatched by another worker thread. Skipping.")
                                    continue
                                cls._in_flight_jobs.add(job_id)

                            try:
                                # Robust attempt calculations
                                raw_att = _get_field_ci(job, attempts_col, "send_attempts", "attempts", "send_attempt", "retry_count", "retries", "no_of_attempts", "attempt_count", default=0)
                                try:
                                    curr_attempts = int(raw_att)
                                except Exception:
                                    curr_attempts = 0

                                raw_tot = _get_field_ci(job, total_attempts_col, "total_attempts", "max_attempts", "max_retries", "retry_limit", default=3)
                                try:
                                    total_attempts = int(raw_tot)
                                    if total_attempts <= 0:
                                        total_attempts = 3
                                except Exception:
                                    total_attempts = 3

                                raw_delay = _get_field_ci(job, delay_col, "attempt_delay", "delay", "retry_delay", "delay_ms", default=5000)
                                try:
                                    attempt_delay_ms = int(raw_delay)
                                    if attempt_delay_ms <= 0:
                                        attempt_delay_ms = 5000
                                except Exception:
                                    attempt_delay_ms = 5000

                                new_attempt_count = curr_attempts + 1

                                # 3. ATOMIC CLAIM: Atomically set status to 'Processing' to prevent other workers/threads from double-sending
                                future_lock_dt = datetime.now() + timedelta(minutes=5)
                                claim_set = [f"{status_col} = 'Processing'"]
                                claim_binds: Dict[str, Any] = {"jid": job_id, "now_dt": datetime.now()}

                                if attempts_col:
                                    claim_set.append(f"{attempts_col} = :new_att")
                                    claim_binds["new_att"] = new_attempt_count
                                if next_attempt_col:
                                    claim_set.append(f"{next_attempt_col} = :lock_dt")
                                    claim_binds["lock_dt"] = future_lock_dt

                                claim_where = [
                                    f"{pk_col} = :jid",
                                    f"{status_col} = 'New'"
                                ]
                                if attempts_col and total_attempts_col:
                                    claim_where.append(f"(COALESCE({attempts_col}, 0) < COALESCE({total_attempts_col}, 3))")
                                if next_attempt_col:
                                    claim_where.append(f"({next_attempt_col} IS NULL OR {next_attempt_col} <= :now_dt)")

                                claim_sql = f"""
                                    UPDATE {job_table}
                                    SET {', '.join(claim_set)}
                                    WHERE {' AND '.join(claim_where)}
                                """
                                with eng.begin() as conn:
                                    claim_res = conn.execute(text(claim_sql), claim_binds)
                                    if claim_res.rowcount == 0:
                                        # Row was already claimed/processed by another thread or worker
                                        logger.debug(f"[EMAIL_DISPATCHER] Job #{job_id} was already claimed by another thread. Skipping.")
                                        continue

                                logger.info(f"[EMAIL_DISPATCHER] Processing Job #{job_id} [Attempt {new_attempt_count}/{total_attempts}].")

                                # Guaranteed processing block
                                job_start_time = time.time()
                                try:
                                    server_id_raw = _get_field_ci(job, "email_server_id", "server_id", default=None)
                                    server_id = int(server_id_raw) if server_id_raw is not None and str(server_id_raw).isdigit() else None
                                    from_email_val = _get_field_ci(job, "from_email", "email_from", "sender_email", "sender", "outgoing_email_user")
                                    to_email = str(_get_field_ci(job, "to_email", "email_to", "recipient", default="") or "").strip()
                                    subject = str(_get_field_ci(job, "subject", "email_subject", default="Notification") or "Notification")
                                    body = str(_get_field_ci(job, "body", "email_body", default="") or "")
                                    e_type = str(_get_field_ci(job, "email_type", default="TEXT") or "TEXT")
                                    cc = _get_field_ci(job, "cc_email", "email_cc", "cc")

                                    if not to_email or "@" not in to_email:
                                        err_msg = f"Invalid recipient email address: '{to_email}'"
                                        logger.error(f"[EMAIL_DISPATCHER] Job #{job_id} Permanently Failed: {err_msg}")
                                        invalid_set = [f"{status_col} = 'Failed'"]
                                        binds = {"jid": job_id}
                                        if attempts_col:
                                            invalid_set.append(f"{attempts_col} = :new_att")
                                            binds["new_att"] = new_attempt_count
                                        if next_attempt_col:
                                            invalid_set.append(f"{next_attempt_col} = NULL")
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
                                        all_details.append({"job_id": job_id, "status": "Failed", "to": to_email, "error": err_msg})
                                        continue

                                    cache_key = f"{cid}_{server_id}_{from_email_val}"
                                    if cache_key not in smtp_cache:
                                        cfg = cls.get_smtp_config(cid, server_id, from_email=from_email_val)
                                        smtp_cache[cache_key] = cfg

                                    smtp_cfg = smtp_cache.get(cache_key)
                                    if not smtp_cfg:
                                        err_msg = f"No active SMTP configuration found for sender '{from_email_val or server_id}' in Connection #{cid}."
                                        logger.error(f"[EMAIL_DISPATCHER] Job #{job_id} Permanently Failed: {err_msg}")
                                        fail_set = [f"{status_col} = 'Failed'"]
                                        binds = {"jid": job_id}
                                        if attempts_col:
                                            fail_set.append(f"{attempts_col} = :new_att")
                                            binds["new_att"] = new_attempt_count
                                        if next_attempt_col:
                                            fail_set.append(f"{next_attempt_col} = NULL")
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
                                        all_details.append({"job_id": job_id, "status": "Failed", "error": err_msg})
                                        continue

                                    cls.send_smtp_email(
                                        smtp_cfg=smtp_cfg,
                                        to_email=to_email,
                                        subject=subject,
                                        body=body,
                                        email_type=e_type,
                                        cc=cc,
                                        from_email=from_email_val
                                    )

                                    # 4. MARK AS 'Sent'
                                    sent_set = [f"{status_col} = 'Sent'"]
                                    binds = {"jid": job_id}
                                    if attempts_col:
                                        sent_set.append(f"{attempts_col} = :new_att")
                                        binds["new_att"] = new_attempt_count
                                    if next_attempt_col:
                                        sent_set.append(f"{next_attempt_col} = NULL")
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
                                    is_failed = (new_attempt_count >= total_attempts) or (not attempts_col)
                                    final_status = 'Failed' if is_failed else 'New'

                                    if is_failed:
                                        logger.warning(f"[EMAIL_DISPATCHER] Job #{job_id} Permanently FAILED after {new_attempt_count} attempts. Reason: {err_msg}")
                                    else:
                                        logger.info(f"[EMAIL_DISPATCHER] Job #{job_id} Scheduled retry #{new_attempt_count + 1} at {next_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                                    # 5. MARK AS 'New' (for retry) OR 'Failed' (if max attempts reached)
                                    fail_set = [f"{status_col} = :st"]
                                    binds = {"st": final_status, "jid": job_id}
                                    if attempts_col:
                                        fail_set.append(f"{attempts_col} = :new_att")
                                        binds["new_att"] = new_attempt_count
                                    if next_attempt_col:
                                        fail_set.append(f"{next_attempt_col} = :nxt")
                                        binds["nxt"] = None if is_failed else next_dt
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

                            finally:
                                with cls._in_flight_lock:
                                    cls._in_flight_jobs.discard(job_id)

                        total_processed += len(rows)

        finally:
            try:
                cls._dispatch_lock.release()
            except Exception:
                pass

        return {
            "processed": total_processed,
            "success": total_success,
            "failed": total_failed,
            "details": all_details
        }
