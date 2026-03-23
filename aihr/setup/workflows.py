from __future__ import annotations

from aihr.setup.access import AIHR_HIRING_MANAGER_ROLE, HR_MANAGER_ROLE

JOB_REQUISITION_WORKFLOW_NAME = "AIHR Job Requisition Approval"
JOB_REQUISITION_WORKFLOW_FIELD = "workflow_state"

JOB_REQUISITION_WORKFLOW_STATES = [
    {
        "state": "草稿",
        "style": "Info",
        "doc_status": "0",
        "allow_edit": AIHR_HIRING_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Pending",
    },
    {
        "state": "待HR处理",
        "style": "Warning",
        "doc_status": "0",
        "allow_edit": HR_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Pending",
    },
    {
        "state": "已批准",
        "style": "Success",
        "doc_status": "0",
        "allow_edit": HR_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Open & Approved",
    },
    {
        "state": "已驳回",
        "style": "Danger",
        "doc_status": "0",
        "allow_edit": AIHR_HIRING_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Rejected",
    },
    {
        "state": "已暂停",
        "style": "Inverse",
        "doc_status": "0",
        "allow_edit": HR_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "On Hold",
    },
    {
        "state": "已完成",
        "style": "Success",
        "doc_status": "0",
        "allow_edit": HR_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Filled",
        "is_optional_state": 1,
    },
    {
        "state": "已取消",
        "style": "Danger",
        "doc_status": "0",
        "allow_edit": HR_MANAGER_ROLE,
        "update_field": "status",
        "update_value": "Cancelled",
        "is_optional_state": 1,
    },
]

JOB_REQUISITION_WORKFLOW_TRANSITIONS = [
    {
        "state": "草稿",
        "action": "提交需求",
        "next_state": "待HR处理",
        "allowed": AIHR_HIRING_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "草稿",
        "action": "取消需求",
        "next_state": "已取消",
        "allowed": AIHR_HIRING_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "待HR处理",
        "action": "批准开启",
        "next_state": "已批准",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "待HR处理",
        "action": "退回修改",
        "next_state": "已驳回",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "待HR处理",
        "action": "取消需求",
        "next_state": "已取消",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已驳回",
        "action": "重新提交",
        "next_state": "待HR处理",
        "allowed": AIHR_HIRING_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已驳回",
        "action": "取消需求",
        "next_state": "已取消",
        "allowed": AIHR_HIRING_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已批准",
        "action": "暂停招聘",
        "next_state": "已暂停",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已批准",
        "action": "取消需求",
        "next_state": "已取消",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已暂停",
        "action": "恢复招聘",
        "next_state": "已批准",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
    {
        "state": "已暂停",
        "action": "取消需求",
        "next_state": "已取消",
        "allowed": HR_MANAGER_ROLE,
        "allow_self_approval": 1,
    },
]

JOB_REQUISITION_STATUS_TO_WORKFLOW_STATE = {
    "Pending": "待HR处理",
    "Open & Approved": "已批准",
    "Rejected": "已驳回",
    "Filled": "已完成",
    "On Hold": "已暂停",
    "Cancelled": "已取消",
}

JOB_REQUISITION_RUNTIME_STATUS_SYNC = {
    "Filled": "已完成",
    "Cancelled": "已取消",
}


def ensure_aihr_workflows() -> None:
    import frappe

    _ensure_workflow_action_masters()
    _ensure_workflow_states()
    _ensure_job_requisition_workflow()
    _sync_existing_requisition_workflow_states()
    frappe.clear_cache()


def ensure_job_requisition_workflow_status(doc) -> None:
    import frappe

    workflow_name = frappe.db.get_value(
        "Workflow",
        {"document_type": "Job Requisition", "is_active": 1},
        "name",
    )
    if workflow_name != JOB_REQUISITION_WORKFLOW_NAME:
        return

    expected_state = JOB_REQUISITION_RUNTIME_STATUS_SYNC.get(getattr(doc, "status", None))
    if not expected_state or getattr(doc, JOB_REQUISITION_WORKFLOW_FIELD, None) == expected_state:
        return

    frappe.db.set_value(
        "Job Requisition",
        doc.name,
        JOB_REQUISITION_WORKFLOW_FIELD,
        expected_state,
        update_modified=False,
    )
    doc.set(JOB_REQUISITION_WORKFLOW_FIELD, expected_state)


def _ensure_workflow_action_masters() -> None:
    import frappe

    actions = {
        transition["action"]
        for transition in JOB_REQUISITION_WORKFLOW_TRANSITIONS
    }
    for action_name in sorted(actions):
        existing = frappe.db.exists("Workflow Action Master", action_name)
        doc = (
            frappe.get_doc("Workflow Action Master", existing)
            if existing
            else frappe.new_doc("Workflow Action Master")
        )
        doc.workflow_action_name = action_name
        doc.save(ignore_permissions=True)


def _ensure_workflow_states() -> None:
    import frappe

    for state in JOB_REQUISITION_WORKFLOW_STATES:
        existing = frappe.db.exists("Workflow State", state["state"])
        doc = frappe.get_doc("Workflow State", existing) if existing else frappe.new_doc("Workflow State")
        doc.workflow_state_name = state["state"]
        doc.style = state["style"]
        doc.save(ignore_permissions=True)


def _ensure_job_requisition_workflow() -> None:
    import frappe

    existing = frappe.db.exists("Workflow", JOB_REQUISITION_WORKFLOW_NAME)
    doc = frappe.get_doc("Workflow", existing) if existing else frappe.new_doc("Workflow")
    doc.workflow_name = JOB_REQUISITION_WORKFLOW_NAME
    doc.document_type = "Job Requisition"
    doc.workflow_state_field = JOB_REQUISITION_WORKFLOW_FIELD
    doc.is_active = 1
    doc.send_email_alert = 0
    doc.set(
        "states",
        [
            {
                "state": row["state"],
                "doc_status": row["doc_status"],
                "allow_edit": row["allow_edit"],
                "update_field": row["update_field"],
                "update_value": row["update_value"],
                "is_optional_state": row.get("is_optional_state", 0),
            }
            for row in JOB_REQUISITION_WORKFLOW_STATES
        ],
    )
    doc.set(
        "transitions",
        [
            {
                "state": row["state"],
                "action": row["action"],
                "next_state": row["next_state"],
                "allowed": row["allowed"],
                "allow_self_approval": row.get("allow_self_approval", 1),
            }
            for row in JOB_REQUISITION_WORKFLOW_TRANSITIONS
        ],
    )
    doc.save(ignore_permissions=True)


def _sync_existing_requisition_workflow_states() -> None:
    import frappe

    if not frappe.get_meta("Job Requisition").get_field(JOB_REQUISITION_WORKFLOW_FIELD):
        return

    for status, workflow_state in JOB_REQUISITION_STATUS_TO_WORKFLOW_STATE.items():
        frappe.db.sql(
            f"""
            UPDATE `tabJob Requisition`
            SET `{JOB_REQUISITION_WORKFLOW_FIELD}` = %s
            WHERE status = %s
            """,
            (workflow_state, status),
        )

    frappe.db.sql(
        f"""
        UPDATE `tabJob Requisition`
        SET `{JOB_REQUISITION_WORKFLOW_FIELD}` = %s
        WHERE IFNULL(`{JOB_REQUISITION_WORKFLOW_FIELD}`, '') = ''
        """,
        ("草稿",),
    )
