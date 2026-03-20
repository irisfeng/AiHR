from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_NAME = "AIHR Hiring HQ"
WORKSPACE_BLOCK_NAME = "AIHR Hiring HQ Block"
WORKSPACE_BLOCK_LABEL = "AIHR 招聘作战台"


def ensure_aihr_workspace() -> None:
    import frappe

    _ensure_custom_html_block()
    _ensure_workspace()
    _ensure_default_app()
    frappe.clear_cache()


def _ensure_custom_html_block() -> None:
    import frappe

    existing = frappe.db.exists("Custom HTML Block", WORKSPACE_BLOCK_NAME)
    doc = (
        frappe.get_doc("Custom HTML Block", existing)
        if existing
        else frappe.new_doc("Custom HTML Block")
    )
    doc.name = WORKSPACE_BLOCK_NAME
    doc.private = 0
    doc.html = _load_asset("workspace_assets/aihr_hiring_hq_block.html")
    doc.script = _load_asset("workspace_assets/aihr_hiring_hq_block.js")
    doc.style = _load_asset("workspace_assets/aihr_hiring_hq_block.css")
    doc.save(ignore_permissions=True)


def _ensure_workspace() -> None:
    import frappe
    from frappe.model.rename_doc import rename_doc

    existing = _find_existing_workspace()
    doc = frappe.get_doc("Workspace", existing) if existing else frappe.new_doc("Workspace")

    doc.label = WORKSPACE_BLOCK_LABEL
    doc.title = WORKSPACE_BLOCK_LABEL
    doc.module = "Recruitment Intelligence"
    doc.public = 1
    doc.parent_page = ""
    doc.is_hidden = 0
    doc.hide_custom = 1
    doc.icon = "branch"
    doc.indicator_color = "blue"
    doc.content = json.dumps(_workspace_content(), ensure_ascii=False)
    doc.set("custom_blocks", _workspace_custom_blocks())
    doc.set("shortcuts", _workspace_shortcuts())
    doc.set("links", _workspace_links())
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)

    if doc.name != WORKSPACE_NAME:
        rename_doc("Workspace", doc.name, WORKSPACE_NAME, force=True, ignore_permissions=True, show_alert=False)
        doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
        doc.label = WORKSPACE_BLOCK_LABEL
        doc.title = WORKSPACE_BLOCK_LABEL
        doc.flags.ignore_links = True
        doc.flags.ignore_validate = True
        doc.save(ignore_permissions=True)


def _ensure_default_app() -> None:
    import frappe

    if not frappe.db.get_single_value("System Settings", "default_app"):
        frappe.db.set_single_value("System Settings", "default_app", "aihr")


def _load_asset(relative_path: str) -> str:
    import frappe

    return Path(frappe.get_app_path("aihr", *relative_path.split("/"))).read_text(encoding="utf-8")


def _find_existing_workspace() -> str | None:
    import frappe

    for filters in (
        WORKSPACE_NAME,
        {"label": WORKSPACE_BLOCK_LABEL},
        {"title": WORKSPACE_BLOCK_LABEL},
        {"label": WORKSPACE_NAME},
        {"title": WORKSPACE_NAME},
    ):
        existing = frappe.db.exists("Workspace", filters)
        if existing:
            return str(existing)
    return None


def _workspace_content() -> list[dict]:
    return [
        {
            "type": "custom_block",
            "data": {
                "custom_block_name": WORKSPACE_BLOCK_LABEL,
                "col": 12,
            },
        },
        {"type": "spacer", "data": {"col": 12}},
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>高频操作</b></span><div class="text-muted">围绕招聘主链路推进，而不是在 ERP 模块里寻找入口。</div>',
                "col": 12,
            },
        },
        {"type": "shortcut", "data": {"shortcut_name": "新建岗位需求", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "招聘中岗位", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "候选人池", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "AI 摘要池", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "面试安排", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "Offer 管理", "col": 2}},
        {"type": "spacer", "data": {"col": 12}},
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>功能模块</b></span><div class="text-muted">从需求、筛选、面试到录用，全部围绕 AIHR 招聘作战台组织。</div>',
                "col": 12,
            },
        },
        {"type": "card", "data": {"card_name": "招聘执行", "col": 4}},
        {"type": "card", "data": {"card_name": "面试与录用", "col": 4}},
        {"type": "card", "data": {"card_name": "组织与主数据", "col": 4}},
    ]


def _workspace_custom_blocks() -> list[dict]:
    return [
        {
            "custom_block_name": WORKSPACE_BLOCK_NAME,
            "label": WORKSPACE_BLOCK_LABEL,
        }
    ]


def _workspace_shortcuts() -> list[dict]:
    return [
        {
            "label": "新建岗位需求",
            "type": "DocType",
            "link_to": "Job Requisition",
            "doc_view": "New",
            "color": "#0f766e",
        },
        {
            "label": "招聘中岗位",
            "type": "DocType",
            "link_to": "Job Opening",
            "doc_view": "List",
            "format": "{} 招聘中",
            "stats_filter": json.dumps({"status": ["=", "Open"]}, ensure_ascii=False),
            "color": "#ea580c",
        },
        {
            "label": "候选人池",
            "type": "DocType",
            "link_to": "Job Applicant",
            "doc_view": "List",
            "format": "{} 候选人",
            "stats_filter": json.dumps({"status": ["!=", "Rejected"]}, ensure_ascii=False),
            "color": "#2563eb",
        },
        {
            "label": "AI 摘要池",
            "type": "DocType",
            "link_to": "AI Screening",
            "doc_view": "List",
            "format": "{} 条摘要",
            "stats_filter": json.dumps({"docstatus": ["!=", "2"]}, ensure_ascii=False),
            "color": "#7c3aed",
        },
        {
            "label": "面试安排",
            "type": "DocType",
            "link_to": "Interview",
            "doc_view": "List",
            "format": "{} 条记录",
            "stats_filter": json.dumps({"docstatus": ["!=", "2"]}, ensure_ascii=False),
            "color": "#ca8a04",
        },
        {
            "label": "Offer 管理",
            "type": "DocType",
            "link_to": "Job Offer",
            "doc_view": "List",
            "format": "{} 条 Offer",
            "stats_filter": json.dumps({"docstatus": ["!=", "2"]}, ensure_ascii=False),
            "color": "#be123c",
        },
    ]


def _workspace_links() -> list[dict]:
    return [
        {
            "type": "Card Break",
            "label": "招聘执行",
            "description": "从岗位需求、岗位开启到候选人 AI 初筛的主链路。",
        },
        {"type": "Link", "label": "岗位需求单", "link_type": "DocType", "link_to": "Job Requisition"},
        {"type": "Link", "label": "招聘中岗位", "link_type": "DocType", "link_to": "Job Opening"},
        {"type": "Link", "label": "候选人档案", "link_type": "DocType", "link_to": "Job Applicant"},
        {"type": "Link", "label": "AI 初筛结果", "link_type": "DocType", "link_to": "AI Screening"},
        {
            "type": "Card Break",
            "label": "面试与录用",
            "description": "面试安排、反馈回收和 Offer 推进。",
        },
        {"type": "Link", "label": "面试安排", "link_type": "DocType", "link_to": "Interview"},
        {"type": "Link", "label": "面试反馈", "link_type": "DocType", "link_to": "Interview Feedback"},
        {"type": "Link", "label": "Offer 管理", "link_type": "DocType", "link_to": "Job Offer"},
        {"type": "Link", "label": "录用信", "link_type": "DocType", "link_to": "Appointment Letter"},
        {
            "type": "Card Break",
            "label": "组织与主数据",
            "description": "用于维护招聘协同所需的组织、入职和基础主数据。",
        },
        {"type": "Link", "label": "入职交接", "link_type": "DocType", "link_to": "Employee Onboarding"},
        {"type": "Link", "label": "员工档案", "link_type": "DocType", "link_to": "Employee"},
        {"type": "Link", "label": "部门", "link_type": "DocType", "link_to": "Department"},
        {"type": "Link", "label": "用户", "link_type": "DocType", "link_to": "User"},
    ]
