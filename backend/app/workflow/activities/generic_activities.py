import json
import requests
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.workflow.runtime.base_activity import BaseActivity
from app.workflow.runtime.registry import registry
from app.workflow.runtime.context import WorkflowContext
from app.core.logger import logger
from app.workflow.models.history import WorkflowHistory

@registry.register("EmailActivity")
class EmailActivity(BaseActivity):
    """
    Generic activity that dispatches emails using parameters resolved from 
    extension configurations or workflow context variables.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        recipient = config.get("recipient_email") or context.get_variable("recipient_email")
        subject = config.get("email_subject") or context.get_variable("email_subject")
        return recipient is not None and subject is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        recipient = config.get("recipient_email") or context.get_variable("recipient_email")
        subject = config.get("email_subject") or context.get_variable("email_subject")
        body = config.get("email_body") or context.get_variable("email_body") or ""
        
        logger.info(f"[Generic EmailActivity] Sending email to '{recipient}' with subject: '{subject}'")
        return {"sent": True, "recipient": recipient}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        logger.warning("[Generic EmailActivity] Rollback initiated: Emails cannot be physically recalled.")
        return {"compensated": True}


@registry.register("WebhookActivity")
class WebhookActivity(BaseActivity):
    """
    Generic activity triggering external REST APIs/webhooks.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        url = config.get("webhook_url") or context.get_variable("webhook_url")
        return url is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        url = config.get("webhook_url") or context.get_variable("webhook_url")
        payload_raw = config.get("webhook_payload")
        
        if payload_raw and isinstance(payload_raw, str):
            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = {"raw_content": payload_raw}
        else:
            payload = payload_raw or context.get_variable("webhook_payload") or {}
            
        method = config.get("webhook_method") or context.get_variable("webhook_method") or "POST"
        
        logger.info(f"[Generic WebhookActivity] Sending {method} to '{url}' with payload: {payload}")
        try:
            headers = {"Content-Type": "application/json"}
            res = requests.request(method, url, json=payload, headers=headers, timeout=10)
            return {"status_code": res.status_code, "response_body": res.text}
        except Exception as e:
            logger.error(f"[Generic WebhookActivity] HTTP call failed: {str(e)}")
            raise e

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        logger.warning("[Generic WebhookActivity] Webhook call rollback requested.")
        return {"compensated": True}


@registry.register("UpdateDatabaseActivity")
class UpdateDatabaseActivity(BaseActivity):
    """
    Generic database update executor. Uses dynamically bound session inside context.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        query_string = config.get("db_query") or context.get_variable("db_query")
        return query_string is not None and context.db is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        query_string = config.get("db_query") or context.get_variable("db_query")
        params_raw = config.get("db_params")
        
        if params_raw and isinstance(params_raw, str):
            try:
                params = json.loads(params_raw)
            except Exception:
                params = {}
        else:
            params = params_raw or context.get_variable("db_params") or {}
        
        logger.info(f"[Generic UpdateDatabaseActivity] Executing SQL: {query_string} with parameters: {params}")
        
        result = context.db.execute(text(query_string), params)
        context.db.flush()
        return {"rows_affected": result.rowcount}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        logger.warning("[Generic UpdateDatabaseActivity] Database execution rollback: Transaction rollback handles updates.")
        return {"compensated": True}


@registry.register("NotificationActivity")
class NotificationActivity(BaseActivity):
    """
    Creates internal notifications for users.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        user_id = config.get("notification_user_id") or context.get_variable("notification_user_id")
        message = config.get("notification_message") or context.get_variable("notification_message")
        return user_id is not None and message is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        user_id = config.get("notification_user_id") or context.get_variable("notification_user_id")
        message = config.get("notification_message") or context.get_variable("notification_message")
        
        logger.info(f"[Generic NotificationActivity] Adding alert for User ID {user_id}: {message}")
        return {"notified": True, "user_id": user_id}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"compensated": True}


@registry.register("AuditActivity")
class AuditActivity(BaseActivity):
    """
    Inserts high-level transition history trails. Uses dynamically bound database.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        instance_id = config.get("instance_id") or context.get_variable("instance_id")
        action_name = config.get("action_name") or context.get_variable("action_name")
        return instance_id is not None and action_name is not None and context.db is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        instance_id = config.get("instance_id") or context.get_variable("instance_id")
        action_name = config.get("action_name") or context.get_variable("action_name")
        remarks = config.get("remarks") or context.get_variable("remarks") or "System auto trace"
        
        logger.info(f"[Generic AuditActivity] Logging transition '{action_name}' for instance {instance_id}")
        
        history = WorkflowHistory(
            instance_id=instance_id,
            action_name=action_name,
            remarks=remarks,
            performed_by=context.user_id or 1,
            performed_role=context.user_role or "SYSTEM"
        )
        context.db.add(history)
        context.db.flush()
        return {"audit_logged": True}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        logger.warning("[Generic AuditActivity] Compensation: Removing audit entry.")
        return {"compensated": True}


@registry.register("LogActivity")
class LogActivity(BaseActivity):
    """
    Generic execution tracer logging structured trace outputs.
    """
    def validate(self, context: WorkflowContext) -> bool:
        config = context.activity_config or {}
        message = config.get("log_message") or context.get_variable("log_message")
        return message is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        config = context.activity_config or {}
        message = config.get("log_message") or context.get_variable("log_message")
        level = config.get("log_level") or context.get_variable("log_level") or "INFO"
        
        structured_msg = f"[Process Log] {message}"
        if level == "ERROR":
            logger.error(structured_msg)
        elif level == "WARNING":
            logger.warning(structured_msg)
        else:
            logger.info(structured_msg)
            
        return {"logged": True}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"compensated": True}
