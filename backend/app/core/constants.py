# -*- coding: utf-8 -*-
from enum import IntEnum

class ApprovalStatus(IntEnum):
    REJECTED = -1
    PENDING  =  0
    APPROVED =  1

class WorkflowAction:
    SUBMIT  = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT  = "REJECT"

class RoleCode:
    RISK_OWNER      = "RISK_OWNER"
    FUNCTIONAL_HEAD = "FUNCTION_HEAD"
    RISK_MANAGER    = "RISK_MANAGER"
    RISK_HEAD       = "RISK_HEAD"

class RoleName:
    RISK_OWNER      = "RISK OWNER"
    FUNCTIONAL_HEAD = "FUNCTIONAL HEAD"
    RISK_MANAGER    = "RISK MANAGER"
    RISK_HEAD       = "RISK HEAD"
    ADMIN           = "ADMIN"

APPROVAL_LEVEL_TO_ROLE = {
    1: RoleCode.FUNCTIONAL_HEAD,
    2: RoleCode.RISK_MANAGER,
    3: RoleCode.RISK_HEAD,
}

ROLE_TO_APPROVAL_LEVEL = {v: k for k, v in APPROVAL_LEVEL_TO_ROLE.items()}

REQUEST_STATUS_TO_APPROVAL = {
    7: ApprovalStatus.APPROVED,
    8: ApprovalStatus.REJECTED,
}

REQUEST_STATUS_NAMES = {
    7: "Approved",
    8: "Rejected",
}

def approval_status_name(value) -> str:
    mapping = {
        ApprovalStatus.APPROVED: "Approved",
        ApprovalStatus.REJECTED: "Rejected",
        None: " ",
    }
    try:
        return mapping.get(ApprovalStatus(value), " ")
    except (ValueError, TypeError):
        return mapping.get(None, " ")

def is_approved(value) -> bool:
    try:
        return ApprovalStatus(value) == ApprovalStatus.APPROVED
    except (ValueError, TypeError):
        return False

def is_rejected(value) -> bool:
    try:
        return ApprovalStatus(value) == ApprovalStatus.REJECTED
    except (ValueError, TypeError):
        return False

def all_approved(*values) -> bool:
    return all(is_approved(v) for v in values)
