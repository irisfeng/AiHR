from __future__ import annotations

import json
from pathlib import Path


WORKSPACE_NAME = "AIHR Hiring HQ"
WORKSPACE_BLOCK_NAME = "AIHR Hiring HQ Block"
WORKSPACE_BLOCK_LABEL = "AIHR 招聘总览"
MANAGER_WORKSPACE_NAME = "AIHR Manager Review"
MANAGER_WORKSPACE_LABEL = "AIHR 用人经理中心"
INTERVIEWER_WORKSPACE_NAME = "AIHR Interview Desk"
INTERVIEWER_WORKSPACE_LABEL = "AIHR 面试协同中心"

AIHR_WORKSPACE_NAMES = {
    WORKSPACE_NAME,
    MANAGER_WORKSPACE_NAME,
    INTERVIEWER_WORKSPACE_NAME,
}

AIHR_WORKSPACE_LABELS = {
    WORKSPACE_BLOCK_LABEL,
    MANAGER_WORKSPACE_LABEL,
    INTERVIEWER_WORKSPACE_LABEL,
}


def ensure_aihr_workspace() -> None:
    import frappe

    _ensure_custom_html_block()
    for definition in _workspace_definitions():
        _ensure_workspace(definition)
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


def _ensure_workspace(definition: dict) -> None:
    import frappe
    from frappe.model.rename_doc import rename_doc

    existing = _find_existing_workspace(definition)
    doc = frappe.get_doc("Workspace", existing) if existing else frappe.new_doc("Workspace")

    doc.label = definition["label"]
    doc.title = definition["label"]
    doc.module = "Recruitment Intelligence"
    doc.public = 1
    doc.parent_page = ""
    doc.is_hidden = 0
    doc.hide_custom = 1
    doc.icon = definition["icon"]
    doc.indicator_color = definition["indicator_color"]
    doc.content = json.dumps(definition["content"], ensure_ascii=False)
    doc.set("custom_blocks", definition.get("custom_blocks", []))
    doc.set("shortcuts", definition["shortcuts"])
    doc.set("links", definition["links"])
    doc.flags.ignore_links = True
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)

    if doc.name != definition["name"]:
        rename_doc("Workspace", doc.name, definition["name"], force=True, ignore_permissions=True, show_alert=False)
        doc = frappe.get_doc("Workspace", definition["name"])
        doc.label = definition["label"]
        doc.title = definition["label"]
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


def _workspace_definitions() -> list[dict]:
    return [
        {
            "name": WORKSPACE_NAME,
            "label": WORKSPACE_BLOCK_LABEL,
            "icon": "branch",
            "indicator_color": "blue",
            "content": _workspace_content(),
            "custom_blocks": _workspace_custom_blocks(),
            "shortcuts": _workspace_shortcuts(),
            "links": _workspace_links(),
        },
        {
            "name": MANAGER_WORKSPACE_NAME,
            "label": MANAGER_WORKSPACE_LABEL,
            "icon": "check-square",
            "indicator_color": "orange",
            "content": _manager_workspace_content(),
            "shortcuts": _manager_workspace_shortcuts(),
            "links": _manager_workspace_links(),
        },
        {
            "name": INTERVIEWER_WORKSPACE_NAME,
            "label": INTERVIEWER_WORKSPACE_LABEL,
            "icon": "calendar",
            "indicator_color": "green",
            "content": _interviewer_workspace_content(),
            "shortcuts": _interviewer_workspace_shortcuts(),
            "links": _interviewer_workspace_links(),
        },
    ]


def _find_existing_workspace(definition: dict) -> str | None:
    import frappe

    for filters in (
        definition["name"],
        {"label": definition["label"]},
        {"title": definition["label"]},
        {"label": definition["name"]},
        {"title": definition["name"]},
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
                "text": '<span class="h4"><b>招聘 MVP 高频操作</b></span><div class="text-muted">只保留岗位、简历导入、AI 初筛、面试和 Offer 这些核心动作。</div>',
                "col": 12,
            },
        },
        {"type": "shortcut", "data": {"shortcut_name": "新建岗位需求", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "招聘中岗位", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "导入简历包", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "候选人池", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "AI 初筛", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "面试安排", "col": 2}},
        {"type": "shortcut", "data": {"shortcut_name": "Offer 管理", "col": 2}},
        {"type": "spacer", "data": {"col": 12}},
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>核心模块</b></span><div class="text-muted">围绕一条招聘主线推进，不把 MVP 做成完整 HRMS。</div>',
                "col": 12,
            },
        },
        {"type": "card", "data": {"card_name": "岗位与渠道", "col": 4}},
        {"type": "card", "data": {"card_name": "导入与初筛", "col": 4}},
        {"type": "card", "data": {"card_name": "面试与 Offer", "col": 4}},
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
            "label": "导入简历包",
            "type": "DocType",
            "link_to": "Job Opening",
            "doc_view": "List",
            "format": "{} 个导入入口",
            "stats_filter": json.dumps({"status": ["=", "Open"]}, ensure_ascii=False),
            "color": "#0f766e",
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
            "label": "AI 初筛",
            "type": "DocType",
            "link_to": "AI Screening",
            "doc_view": "List",
            "format": "{} 条初筛",
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
            "label": "岗位与渠道",
            "description": "收口岗位需求、补充 JD，并把需求转成实际招聘中的岗位。",
        },
        {"type": "Link", "label": "岗位需求单", "link_type": "DocType", "link_to": "Job Requisition"},
        {"type": "Link", "label": "招聘中岗位", "link_type": "DocType", "link_to": "Job Opening"},
        {
            "type": "Card Break",
            "label": "导入与初筛",
            "description": "把供应商 ZIP 简历包导入系统，自动解析、建档并产出 AI 初筛摘要。",
        },
        {"type": "Link", "label": "招聘中岗位", "link_type": "DocType", "link_to": "Job Opening"},
        {"type": "Link", "label": "候选人档案", "link_type": "DocType", "link_to": "Job Applicant"},
        {"type": "Link", "label": "AI 初筛结果", "link_type": "DocType", "link_to": "AI Screening"},
        {
            "type": "Card Break",
            "label": "面试与 Offer",
            "description": "聚焦面试安排、反馈回收和 Offer 推进，先不扩到入职与薪酬。",
        },
        {"type": "Link", "label": "面试安排", "link_type": "DocType", "link_to": "Interview"},
        {"type": "Link", "label": "面试反馈", "link_type": "DocType", "link_to": "Interview Feedback"},
        {"type": "Link", "label": "Offer 管理", "link_type": "DocType", "link_to": "Job Offer"},
    ]


def _manager_workspace_content() -> list[dict]:
    return [
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>用人经理概览</b></span><div class="text-muted">先发起岗位需求，再看 AI 初筛、面试安排和 Offer 决策，不再先翻 PDF 简历。</div>',
                "col": 12,
            },
        },
        {"type": "shortcut", "data": {"shortcut_name": "岗位需求单", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "待经理复核", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "候选人池", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "面试安排", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "Offer 管理", "col": 3}},
        {"type": "spacer", "data": {"col": 12}},
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>经理关注模块</b></span><div class="text-muted">从岗位需求开始，再围绕“是否推进”做判断，避免经理陷入日常录入。</div>',
                "col": 12,
            },
        },
        {"type": "card", "data": {"card_name": "候选人复核", "col": 6}},
        {"type": "card", "data": {"card_name": "面试与录用", "col": 6}},
    ]


def _manager_workspace_shortcuts() -> list[dict]:
    return [
        {
            "label": "岗位需求单",
            "type": "DocType",
            "link_to": "Job Requisition",
            "doc_view": "List",
            "format": "{} 条需求",
            "stats_filter": json.dumps({"docstatus": ["!=", "2"]}, ensure_ascii=False),
            "color": "#0f766e",
        },
        {
            "label": "待经理复核",
            "type": "DocType",
            "link_to": "AI Screening",
            "doc_view": "List",
            "format": "{} 条待复核",
            "stats_filter": json.dumps({"status": ["=", "Ready for Review"]}, ensure_ascii=False),
            "color": "#ea580c",
        },
        {
            "label": "候选人池",
            "type": "DocType",
            "link_to": "Job Applicant",
            "doc_view": "List",
            "format": "{} 位候选人",
            "stats_filter": json.dumps({"status": ["!=", "Rejected"]}, ensure_ascii=False),
            "color": "#7c3aed",
        },
        {
            "label": "面试安排",
            "type": "DocType",
            "link_to": "Interview",
            "doc_view": "List",
            "format": "{} 场面试",
            "stats_filter": json.dumps({"status": ["!=", "Rejected"]}, ensure_ascii=False),
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


def _manager_workspace_links() -> list[dict]:
    return [
        {
            "type": "Card Break",
            "label": "岗位需求",
            "description": "先发起并查看岗位需求单，再进入候选人复核和面试推进。",
        },
        {"type": "Link", "label": "岗位需求单", "link_type": "DocType", "link_to": "Job Requisition"},
        {"type": "Link", "label": "招聘中岗位", "link_type": "DocType", "link_to": "Job Opening"},
        {
            "type": "Card Break",
            "label": "候选人复核",
            "description": "先看 AI 摘要，再做经理判断和推进决策。",
        },
        {"type": "Link", "label": "待经理复核", "link_type": "DocType", "link_to": "AI Screening"},
        {"type": "Link", "label": "候选人池", "link_type": "DocType", "link_to": "Job Applicant"},
        {
            "type": "Card Break",
            "label": "面试与录用",
            "description": "聚焦面试反馈、Offer 决策与录用结果留痕。",
        },
        {"type": "Link", "label": "面试安排", "link_type": "DocType", "link_to": "Interview"},
        {"type": "Link", "label": "面试反馈", "link_type": "DocType", "link_to": "Interview Feedback"},
        {"type": "Link", "label": "Offer 管理", "link_type": "DocType", "link_to": "Job Offer"},
    ]


def _interviewer_workspace_content() -> list[dict]:
    return [
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>面试协同概览</b></span><div class="text-muted">面试官只需要看候选人摘要、资料包和反馈录入，不用在系统里迷路。</div>',
                "col": 12,
            },
        },
        {"type": "shortcut", "data": {"shortcut_name": "待执行面试", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "录入反馈", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "候选人摘要", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "面试反馈归档", "col": 3}},
        {"type": "spacer", "data": {"col": 12}},
        {
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>面试执行模块</b></span><div class="text-muted">先看资料包，再填结构化反馈，让结论更快回流主流程。</div>',
                "col": 12,
            },
        },
        {"type": "card", "data": {"card_name": "面试执行", "col": 6}},
        {"type": "card", "data": {"card_name": "候选人简报", "col": 6}},
    ]


def _interviewer_workspace_shortcuts() -> list[dict]:
    return [
        {
            "label": "待执行面试",
            "type": "DocType",
            "link_to": "Interview",
            "doc_view": "List",
            "format": "{} 场待执行",
            "stats_filter": json.dumps({"status": ["in", ["Pending", "Under Review"]]}, ensure_ascii=False),
            "color": "#0f766e",
        },
        {
            "label": "录入反馈",
            "type": "DocType",
            "link_to": "Interview Feedback",
            "doc_view": "List",
            "format": "{} 条反馈",
            "stats_filter": json.dumps({"docstatus": ["!=", "2"]}, ensure_ascii=False),
            "color": "#2563eb",
        },
        {
            "label": "候选人摘要",
            "type": "DocType",
            "link_to": "Job Applicant",
            "doc_view": "List",
            "format": "{} 位候选人",
            "stats_filter": json.dumps({"aihr_ai_status": ["!=", "Rejected"]}, ensure_ascii=False),
            "color": "#7c3aed",
        },
        {
            "label": "面试反馈归档",
            "type": "DocType",
            "link_to": "Interview Feedback",
            "doc_view": "List",
            "format": "{} 条记录",
            "stats_filter": json.dumps({"docstatus": ["=", "1"]}, ensure_ascii=False),
            "color": "#ea580c",
        },
    ]


def _interviewer_workspace_links() -> list[dict]:
    return [
        {
            "type": "Card Break",
            "label": "面试执行",
            "description": "查看资料包、推进面试和回收结构化反馈。",
        },
        {"type": "Link", "label": "面试安排", "link_type": "DocType", "link_to": "Interview"},
        {"type": "Link", "label": "录入反馈", "link_type": "DocType", "link_to": "Interview Feedback"},
        {
            "type": "Card Break",
            "label": "候选人简报",
            "description": "在面试前快速掌握候选人背景、风险点和追问建议。",
        },
        {"type": "Link", "label": "候选人摘要", "link_type": "DocType", "link_to": "Job Applicant"},
        {"type": "Link", "label": "AI 初筛结果", "link_type": "DocType", "link_to": "AI Screening"},
    ]
