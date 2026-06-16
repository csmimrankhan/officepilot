from __future__ import annotations

import json
import re
from datetime import datetime, date
from typing import Any

from sqlalchemy.orm import Session

from ..models.accounting_skill import AccountingSkill, AccountingSkillRun
from ..models.accounting_skill_version import AccountingSkillVersion
from ..models.agent_workflow_memory import AgentWorkflowMemory
from ..models.agent_task_plan import AgentTaskPlan
from ..services.audit import log_action as record_audit

DANGEROUS_PATTERNS = [
    r"payment",
    r"bank\s*transfer",
    r"password\s*entry",
    r"otp|2fa|two.?factor",
    r"delete\s*records?",
    r"tax\s*filing",
    r"payroll\s*submission",
    r"irreversible\s*submit",
    r"api[_-]?key",
    r"secret\s*(key|token)",
    r"cvv|ssn|pin\s*number",
    # Phase 34 — email write/modify actions blocked in read-only mode
    r"send\s+email",
    r"forward\s+email",
    r"delete\s+email",
    r"move\s+email",
    r"mark\s+as\s+read",
    r"archive\s+email",
    r"label\s+email",
    r"modify\s+gmail",
    r"compose\s+email",
    r"reply\s+to\s+email",
]

SENSITIVE_PATTERNS = [
    r"password",
    r"api[_-]?key",
    r"secret",
    r"token",
    r"otp",
    r"2fa",
    r"cvv",
    r"ssn",
    r"pin",
]


def _is_dangerous_skill(name: str, steps: list[dict]) -> str | None:
    text = name.lower()
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, text):
            return f"Skill name contains blocked pattern: {pat}"
    for step in steps:
        instruction = (step.get("instruction") or step.get("step_type") or "").lower()
        target = (step.get("target") or "").lower()
        combined = f"{instruction} {target}"
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, combined):
                return f"Step contains blocked pattern: {pat}"
    return None


def _redact_sensitive(steps: list[dict]) -> list[dict]:
    redacted = []
    for step in steps:
        step_copy = dict(step)
        params = step_copy.get("parameters", {})
        if isinstance(params, dict):
            for key in list(params.keys()):
                kl = key.lower()
                for pat in SENSITIVE_PATTERNS:
                    if re.search(pat, kl):
                        params[key] = "[REDACTED]"
                        break
        instruction = step_copy.get("instruction", "")
        if any(re.search(pat, instruction.lower()) for pat in SENSITIVE_PATTERNS):
            step_copy["instruction"] = "[REDACTED]"
        step_copy["parameters"] = params
        redacted.append(step_copy)
    return redacted


def _generate_skill_name(steps: list[dict], plan: AgentTaskPlan | None = None) -> str:
    if plan and plan.command_text:
        text = plan.command_text.strip()
        if len(text) > 60:
            text = text[:57] + "..."
        return f"Skill: {text}"
    step_types = [s.get("step_type", s.get("tool", "")) for s in steps if s.get("step_type") or s.get("tool")]
    if step_types:
        return f"Skill: {' → '.join(step_types[:3])}"
    return "Skill: Untitled"


def _generate_trigger_phrases(steps: list[dict], plan: AgentTaskPlan | None = None) -> list[str]:
    phrases = []
    if plan and plan.command_text:
        phrases.append(plan.command_text.lower().strip())
        words = plan.command_text.lower().split()
        if len(words) > 2:
            phrases.append(" ".join(words[:3]))
            phrases.append(" ".join(words[-3:]))
    step_types = [s.get("step_type", s.get("tool", "")) for s in steps if s.get("step_type") or s.get("tool")]
    if step_types:
        phrases.append(" ".join(step_types[:2]).lower())
    return list(set(p for p in phrases if p))


def _detect_variables(steps: list[dict]) -> list[dict]:
    variables = []
    seen = set()
    var_pattern = re.compile(r"\{(\w+)\}")
    for step in steps:
        for val in [str(step.get(k, "")) for k in ("instruction", "target", "expected_result")]:
            for match in var_pattern.finditer(val):
                name = match.group(1)
                if name not in seen:
                    seen.add(name)
                    variables.append({"name": name, "type": "string", "example": f"value_for_{name}", "description": f"Custom {name}"})
    if not variables:
        today = date.today().isoformat()
        variables = [
            {"name": "date", "type": "string", "example": today, "description": "Reference date"},
        ]
    return variables


def _extract_safety_rules(steps: list[dict]) -> dict:
    has_approval = any(s.get("risk_level") == "medium" or s.get("risk_level") == "high" for s in steps)
    return {
        "approval_required": has_approval,
        "max_risk_level": "high" if any(s.get("risk_level") == "high" for s in steps) else "medium" if has_approval else "low",
        "blocked_actions": [],
        "auto_redact": True,
    }


def _compute_risk_level(name: str, steps: list[dict]) -> str:
    if any(s.get("risk_level") == "high" for s in steps):
        return "high"
    if any(s.get("risk_level") == "medium" for s in steps):
        return "medium"
    if _is_dangerous_skill(name, steps):
        return "high"
    return "low"


# ── Default Automation Skill Templates ─────────────────────────────────────────
# These are Hermes-style automation skills for common accounting workflows.
# They focus on browser/desktop/file/email automation, NOT document parsing.

AUTOMATION_SKILL_TEMPLATES = [
    {
        "name": "Create Excel Summary",
        "description": "Detects columns in an Excel file, creates a grouped summary sheet with totals, formats the report, and saves a copy.",
        "trigger_phrases": ["create excel summary", "summarize this spreadsheet", "make summary sheet", "prepare excel summary", "excel summary banao"],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "excel_create_summary_from_file", "tool": "excel_create_summary_from_file", "target": "Excel file", "instruction": "Select and analyze the Excel file to summarize", "expected_result": "File validated", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}"}},
            {"step_order": 2, "step_type": "excel_create_summary_from_file", "tool": "excel_create_summary_from_file", "target": "Data", "instruction": "Auto-detect columns and create grouped summary with totals", "expected_result": "Summary sheet with grouped totals", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{file_path}", "source_sheet": "{sheet_name}", "group_by_column": "{group_by_column}", "value_column": "{value_column}"}},
        ],
    },
    {
        "name": "Apply Formula",
        "description": "Adds a SUM, VLOOKUP, or other formula to an Excel sheet with compatibility handling for older Excel versions.",
        "trigger_phrases": ["apply formula", "add formula", "calculate total", "add sum formula", "sum column", "formula laga do"],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "excel_open_workbook", "tool": "excel_open_workbook", "target": "Excel file", "instruction": "Open the Excel file", "expected_result": "Workbook info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}"}},
            {"step_order": 2, "step_type": "excel_detect_columns", "tool": "excel_detect_columns", "target": "Excel sheet", "instruction": "Detect columns to find the amount column", "expected_result": "Column info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}"}},
            {"step_order": 3, "step_type": "excel_apply_total_formula", "tool": "excel_apply_total_formula", "target": "Excel", "instruction": "Apply SUM formula to total the amount column", "expected_result": "Total formula added", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}", "column_letter": "{column_letter}"}},
        ],
    },
    {
        "name": "Create Pivot Table",
        "description": "Creates a pivot-like grouped summary from an Excel sheet. Asks for row field, value field, and aggregation method.",
        "trigger_phrases": ["create pivot table", "summarize by vendor", "pivot expenses by category", "group by month", "pivot banao"],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "excel_open_workbook", "tool": "excel_open_workbook", "target": "Excel file", "instruction": "Open the Excel file", "expected_result": "Workbook info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}"}},
            {"step_order": 2, "step_type": "excel_detect_columns", "tool": "excel_detect_columns", "target": "Excel sheet", "instruction": "Detect columns to find row and value fields", "expected_result": "Column info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}"}},
            {"step_order": 3, "step_type": "excel_create_pivot_table", "tool": "excel_create_pivot_table", "target": "Excel", "instruction": "Create pivot-like summary grouped by {group_by_column} with {value_column}", "expected_result": "Pivot summary created", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{file_path}", "source_sheet": "{sheet_name}", "group_by_column": "{group_by_column}", "value_column": "{value_column}"}},
            {"step_order": 4, "step_type": "excel_add_total_row", "tool": "excel_add_total_row", "target": "Excel", "instruction": "Add total row to the pivot summary", "expected_result": "Total row added", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}_Summary", "column_letter": "{value_column_letter}"}},
        ],
    },
    {
        "name": "Clean Excel/CSV",
        "description": "Cleans a CSV or Excel file by removing empty rows and columns, normalizing dates and currency, and saving a cleaned copy.",
        "trigger_phrases": ["clean this excel file", "clean csv", "fix spreadsheet", "remove empty rows", "spreadsheet clean karo"],
        "approval_required": False,
        "steps": [
            {"step_order": 1, "step_type": "excel_open_workbook", "tool": "excel_open_workbook", "target": "CSV/Excel file", "instruction": "Open the file to inspect", "expected_result": "File structure", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}"}},
            {"step_order": 2, "step_type": "excel_clean_csv", "tool": "excel_clean_csv", "target": "file", "instruction": "Clean the file by removing empty rows and columns", "expected_result": "Cleaned Excel file", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path}"}},
        ],
    },
    {
        "name": "Compare Excel Reports",
        "description": "Compares two Excel workbooks sheet by sheet and reports row-level differences.",
        "trigger_phrases": ["compare two excel files", "compare reports", "find differences", "compare this month and last month", "excel compare karo"],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "excel_open_workbook", "tool": "excel_open_workbook", "target": "Excel file A", "instruction": "Open first Excel file", "expected_result": "Workbook A info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path_a}"}},
            {"step_order": 2, "step_type": "excel_open_workbook", "tool": "excel_open_workbook", "target": "Excel file B", "instruction": "Open second Excel file", "expected_result": "Workbook B info", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{file_path_b}"}},
            {"step_order": 3, "step_type": "excel_compare_workbooks", "tool": "excel_compare_workbooks", "target": "both files", "instruction": "Compare the two workbooks", "expected_result": "Difference report", "requires_approval": False, "risk_level": "low", "parameters": {"path_a": "{file_path_a}", "path_b": "{file_path_b}"}},
        ],
    },
    # ── Export Accounting Report (Browser Automation) ──────────────────────
    # Phase 32: Guided download mode. Safe read/export/download only.
    # No password automation, no blind clicking. User navigates manually
    # in guided mode; agent watches Downloads folder for exported file.
    {
        "name": "Export Accounting Report",
        "description": "Browser export automation — opens an accounting website, you log in manually, navigate to the report, and export. OfficePilot watches the Downloads folder and copies the file to your output folder.",
        "trigger_phrases": [
            "export profit and loss",
            "download report",
            "get monthly report",
            "export accounting report",
            "get pnl report",
            "export monthly pnl",
            "export monthly profit and loss",
            "export pnl statement",
            "download accounting report",
            "get report from accounting software",
            "quickbooks report export",
            "xero report download",
            "accounting export banao",
            "report download karo",
            "profit and loss report download",
            "monthly report export",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "browser_open_url", "tool": "browser_open_url", "target": "Accounting platform", "instruction": "Open the accounting platform in the browser", "expected_result": "Platform loaded", "requires_approval": True, "risk_level": "medium", "parameters": {"url": "{platform_url}", "guided_mode": True}},
            {"step_order": 2, "step_type": "browser_wait_for_user_login", "tool": "browser_wait_for_user_login", "target": "Login page", "instruction": "Wait for you to log in manually (your password is never stored or typed)", "expected_result": "User logged in", "requires_approval": False, "risk_level": "low", "parameters": {"prompt": "Please log into the accounting platform manually in the browser"}},
            {"step_order": 3, "step_type": "browser_read_page", "tool": "browser_read_page", "target": "Dashboard", "instruction": "Confirm you are logged in by reading the page", "expected_result": "Dashboard visible", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 4, "step_type": "browser_export_report", "tool": "browser_export_report", "target": "Export button", "instruction": "Ready for export — please navigate to the report in the browser and click Export/Download. I will watch the Downloads folder and detect the file automatically.", "expected_result": "Report downloaded", "requires_approval": True, "risk_level": "medium", "parameters": {"report_type": "accounting_report", "guided_mode": True}},
            {"step_order": 5, "step_type": "browser_wait_for_download", "tool": "browser_wait_for_download", "target": "Downloads folder", "instruction": "Detect the downloaded report file", "expected_result": "File detected", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 6, "step_type": "file_open_folder", "tool": "file_open_folder", "target": "Output folder", "instruction": "Show the saved report file location", "expected_result": "File path displayed", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{output_folder}"}},
        ],
    },
    # ── Guided Browser Export (Simple Download Watcher) ───────────────────
    {
        "name": "Guided Browser Export",
        "description": "Simple guided browser export — opens a website, you log in and navigate to the report, OfficePilot watches the Downloads folder and saves the exported file.",
        "trigger_phrases": [
            "browser guided export",
            "guided export",
            "watch browser download",
            "export from browser",
            "download from website",
            "browser download karo",
            "website se export karo",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "browser_open_url", "tool": "browser_open_url", "target": "Website", "instruction": "Open the website in the browser", "expected_result": "Website loaded", "requires_approval": True, "risk_level": "medium", "parameters": {"url": "{website_url}", "guided_mode": True}},
            {"step_order": 2, "step_type": "browser_wait_for_user_login", "tool": "browser_wait_for_user_login", "target": "Login page", "instruction": "Wait for you to log in manually", "expected_result": "User logged in", "requires_approval": False, "risk_level": "low", "parameters": {"prompt": "Please log in manually in the browser"}},
            {"step_order": 3, "step_type": "browser_export_report", "tool": "browser_export_report", "target": "Export button", "instruction": "Please navigate to the report/data and click Export/Download. I will watch the Downloads folder for the file.", "expected_result": "File downloaded", "requires_approval": True, "risk_level": "medium", "parameters": {"report_type": "exported_file", "guided_mode": True}},
            {"step_order": 4, "step_type": "browser_wait_for_download", "tool": "browser_wait_for_download", "target": "Downloads folder", "instruction": "Detect the downloaded file", "expected_result": "File detected", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 5, "step_type": "file_open_folder", "tool": "file_open_folder", "target": "Output folder", "instruction": "Show the saved file location", "expected_result": "File path displayed", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{output_folder}"}},
        ],
    },
    # ── Copy Table to Excel ───────────────────────────────────────────────
    {
        "name": "Copy Table to Excel",
        "description": "Copies a visible table from the screen or browser, transfers it into a new Excel workbook, and formats the result.",
        "trigger_phrases": [
            "copy this table to excel",
            "extract visible table",
            "move table to spreadsheet",
            "copy table from screen",
            "copy table from browser",
            "table copy karo",
            "excel mein table dalo",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "screen_find_table", "tool": "screen_find_table", "target": "Screen", "instruction": "Detect table region on the screen", "expected_result": "Table region identified", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 2, "step_type": "desktop_copy", "tool": "desktop_copy", "target": "Detected table", "instruction": "Copy the table content from screen/browser", "expected_result": "Table content in clipboard", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 3, "step_type": "excel_create_workbook", "tool": "excel_create_workbook", "target": "New Excel file", "instruction": "Create a new Excel workbook", "expected_result": "New workbook created", "requires_approval": True, "risk_level": "medium", "parameters": {"filename": "{output_filename}", "headers": []}},
            {"step_order": 4, "step_type": "excel_append_rows", "tool": "excel_append_rows", "target": "Excel sheet", "instruction": "Paste the table data into the workbook", "expected_result": "Data pasted", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{output_filename}", "sheet_name": "Sheet1", "rows": "{table_rows}"}},
            {"step_order": 5, "step_type": "excel_format_header", "tool": "excel_format_header", "target": "Excel sheet", "instruction": "Format the header row", "expected_result": "Formatted header", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{output_filename}", "sheet_name": "Sheet1"}},
            {"step_order": 6, "step_type": "excel_auto_size_columns", "tool": "excel_auto_size_columns", "target": "Excel sheet", "instruction": "Auto-size columns", "expected_result": "Columns resized", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{output_filename}", "sheet_name": "Sheet1"}},
        ],
    },
    # ── Prepare Monthly Report Folder ──────────────────────────────────────
    {
        "name": "Prepare Monthly Folder",
        "description": "Creates a monthly folder structure, moves last month's downloaded reports into the folder, and creates an index Excel file.",
        "trigger_phrases": [
            "prepare monthly folder",
            "organize this month files",
            "create month end folder",
            "month end organize",
            "report organize karo",
            "monthly folder banao",
            "organize monthly downloads",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "file_create_folder", "tool": "file_create_folder", "target": "File system", "instruction": "Create monthly folder structure", "expected_result": "Folder created", "requires_approval": True, "risk_level": "medium", "parameters": {"path": "{monthly_folder_path}"}},
            {"step_order": 2, "step_type": "file_find_latest_download", "tool": "file_find_latest_download", "target": "Downloads", "instruction": "Find downloaded reports from this month", "expected_result": "Files found", "requires_approval": False, "risk_level": "low", "parameters": {"folder": "{download_folder}", "extension": "{file_extension}"}},
            {"step_order": 3, "step_type": "file_copy", "tool": "file_copy", "target": "Downloaded files", "instruction": "Copy report files to the monthly folder", "expected_result": "Files copied", "requires_approval": True, "risk_level": "medium", "parameters": {"source": "{downloaded_files}", "dest": "{monthly_folder_path}"}},
            {"step_order": 4, "step_type": "excel_create_workbook", "tool": "excel_create_workbook", "target": "Index Excel", "instruction": "Create an index Excel file listing the copied reports", "expected_result": "Index created", "requires_approval": True, "risk_level": "medium", "parameters": {"filename": "{index_filename}", "headers": ["File Name", "Source Path", "Date Copied"]}},
            {"step_order": 5, "step_type": "file_open_folder", "tool": "file_open_folder", "target": "Monthly folder", "instruction": "Open the completed monthly folder", "expected_result": "Folder opened", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{monthly_folder_path}"}},
        ],
    },
    # ── Email Attachment Downloader (Phase 34 — Gmail Read-Only) ──────────
    {
        "name": "Email Attachment Downloader",
        "description": "Connects to Gmail, searches for invoice/report emails, shows preview, gets approval, downloads attachments to local folder, and optionally creates Excel summary.",
        "trigger_phrases": [
            "download invoice attachments",
            "find invoice emails",
            "get today attachments",
            "download email attachments",
            "get email invoices",
            "email attachment download karo",
            "find and download attachments",
            "get report attachments from Gmail",
            "download receipt attachments",
            "invoice emails download karo",
            "Gmail sa invoice download karo",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "email_connect_gmail", "tool": "email_connect_gmail", "target": "Gmail", "instruction": "Connect Gmail read-only account", "expected_result": "Gmail connected or already connected", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 2, "step_type": "email_search", "tool": "email_search", "target": "Gmail inbox", "instruction": "Search for invoice/report emails with attachments", "expected_result": "Matching emails found", "requires_approval": False, "risk_level": "low", "parameters": {"query": "has:attachment newer_than:30d (invoice OR receipt OR bill OR report)", "max_results": 10}},
            {"step_order": 3, "step_type": "email_preview_messages", "tool": "email_preview_messages", "target": "Email messages", "instruction": "Preview matched messages with attachment details", "expected_result": "Message previews ready for review", "requires_approval": False, "risk_level": "low", "parameters": {}},
            {"step_order": 4, "step_type": "approval_checkpoint", "tool": "approval_request", "target": "User", "instruction": "Review messages and approve attachment download", "expected_result": "Approval granted", "requires_approval": True, "risk_level": "medium", "parameters": {"prompt": "Review the matched emails and approve downloading their attachments?"}},
            {"step_order": 5, "step_type": "email_download_attachments", "tool": "email_download_attachments", "target": "Email attachments", "instruction": "Download attachments from approved emails", "expected_result": "Files downloaded to local folder", "requires_approval": True, "risk_level": "medium", "parameters": {"query": "has:attachment newer_than:30d (invoice OR receipt OR bill OR report)", "output_folder": "{save_folder}"}},
            {"step_order": 6, "step_type": "file_open_folder", "tool": "file_open_folder", "target": "Download folder", "instruction": "Open the folder with downloaded attachments", "expected_result": "Folder opened", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{save_folder}"}},
        ],
    },
    # ── Prepare Monthly Report ─────────────────────────────────────────────
    {
        "name": "Prepare Monthly Report",
        "description": "Creates a monthly accounting report by opening the accounting platform, exporting P&L and balance sheet, organizing files into a monthly folder, and creating an Excel summary.",
        "trigger_phrases": [
            "prepare monthly report",
            "create month end report",
            "monthly accounting report",
            "month end summary",
            "monthly report tayar karo",
            "month end accounting",
        ],
        "approval_required": True,
        "steps": [
            {"step_order": 1, "step_type": "browser_open_url", "tool": "browser_open_url", "target": "Accounting platform", "instruction": "Open accounting platform", "expected_result": "Platform loaded", "requires_approval": True, "risk_level": "medium", "parameters": {"url": "{platform_url}"}},
            {"step_order": 2, "step_type": "browser_wait_for_user_login", "tool": "browser_wait_for_user_login", "target": "Login", "instruction": "Wait for manual login", "expected_result": "Logged in", "requires_approval": False, "risk_level": "low", "parameters": {"prompt": "Please log in to your accounting platform"}},
            {"step_order": 3, "step_type": "browser_export_report", "tool": "browser_export_report", "target": "P&L report", "instruction": "Export Profit & Loss report for the month", "expected_result": "P&L exported", "requires_approval": True, "risk_level": "medium", "parameters": {"report_type": "profit_and_loss", "period": "{report_period}"}},
            {"step_order": 4, "step_type": "browser_export_report", "tool": "browser_export_report", "target": "Balance Sheet", "instruction": "Export Balance Sheet for the month", "expected_result": "Balance Sheet exported", "requires_approval": True, "risk_level": "medium", "parameters": {"report_type": "balance_sheet", "period": "{report_period}"}},
            {"step_order": 5, "step_type": "file_create_folder", "tool": "file_create_folder", "target": "File system", "instruction": "Create monthly report folder", "expected_result": "Folder created", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{report_folder_path}"}},
            {"step_order": 6, "step_type": "file_open_folder", "tool": "file_open_folder", "target": "Report folder", "instruction": "Open the completed report folder", "expected_result": "Folder opened", "requires_approval": False, "risk_level": "low", "parameters": {"path": "{report_folder_path}"}},
        ],
    },
]


def seed_default_excel_skills(db: Session, user_id: int) -> list[dict]:
    seeded = []
    for tmpl in AUTOMATION_SKILL_TEMPLATES:
        existing = db.query(AccountingSkill).filter(
            AccountingSkill.user_id == user_id,
            AccountingSkill.name == tmpl["name"],
        ).first()
        if existing:
            continue
        skill = AccountingSkill(
            user_id=user_id,
            name=tmpl["name"],
            description=tmpl["description"],
            trigger_phrases_json=json.dumps(tmpl["trigger_phrases"]),
            workflow_steps_json=json.dumps(tmpl["steps"]),
            approval_required=tmpl["approval_required"],
            version=1,
            status="active",
        )
        db.add(skill)
        db.flush()

        version = AccountingSkillVersion(
            skill_id=skill.id,
            user_id=user_id,
            version=1,
            name=tmpl["name"],
            description=tmpl["description"],
            trigger_phrases_json=skill.trigger_phrases_json,
            workflow_steps_json=skill.workflow_steps_json,
            approval_required=tmpl["approval_required"],
        )
        db.add(version)
        seeded.append({"id": skill.id, "name": tmpl["name"]})

    if seeded:
        db.commit()
    return seeded


def create_skill_from_workflow(
    db: Session,
    user_id: int,
    plan_id: int | None = None,
    workflow_memory_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
    trigger_phrases: list[str] | None = None,
) -> dict:
    plan = None
    steps: list[dict] = []
    workflow_memory = None

    if workflow_memory_id:
        workflow_memory = db.query(AgentWorkflowMemory).filter(
            AgentWorkflowMemory.id == workflow_memory_id,
            AgentWorkflowMemory.user_id == user_id,
        ).first()
        if not workflow_memory:
            return {"ok": False, "error": "Workflow not found"}
        if workflow_memory.steps_json:
            try:
                steps = json.loads(workflow_memory.steps_json)
            except (json.JSONDecodeError, TypeError):
                steps = []
        if workflow_memory.source_task_plan_id:
            plan = db.query(AgentTaskPlan).filter(AgentTaskPlan.id == workflow_memory.source_task_plan_id).first()
        elif not plan and workflow_memory.trigger_phrases_json:
            plan = db.query(AgentTaskPlan).filter(
                AgentTaskPlan.user_id == user_id,
                AgentTaskPlan.command_text.isnot(None),
                AgentTaskPlan.status == "completed",
            ).order_by(AgentTaskPlan.created_at.desc()).first()
    elif plan_id:
        plan = db.query(AgentTaskPlan).filter(
            AgentTaskPlan.id == plan_id,
            AgentTaskPlan.user_id == user_id,
        ).first()
        if not plan:
            return {"ok": False, "error": "Plan not found"}
        if plan.plan_json:
            try:
                plan_data = json.loads(plan.plan_json)
                steps = plan_data.get("steps", [])
            except (json.JSONDecodeError, TypeError):
                steps = []

    if not steps:
        return {"ok": False, "error": "No workflow steps to save as skill"}

    if not name:
        name = _generate_skill_name(steps, plan)
    if not description:
        description = plan.command_text if plan and plan.command_text else f"Accounting skill with {len(steps)} steps"
    if not trigger_phrases:
        trigger_phrases = _generate_trigger_phrases(steps, plan)

    danger = _is_dangerous_skill(name, steps)
    if danger:
        return {"ok": False, "error": danger}

    redacted_steps = _redact_sensitive(steps)
    variables = _detect_variables(redacted_steps)
    safety_rules = _extract_safety_rules(redacted_steps)
    risk_level = _compute_risk_level(name, redacted_steps)

    skill = AccountingSkill(
        user_id=user_id,
        name=name,
        description=description,
        source_plan_id=plan_id,
        source_workflow_memory_id=workflow_memory_id,
        trigger_phrases_json=json.dumps(trigger_phrases),
        workflow_steps_json=json.dumps(redacted_steps),
        variables_json=json.dumps(variables),
        safety_rules_json=json.dumps(safety_rules),
        approval_required=safety_rules["approval_required"],
        version=1,
        status="active",
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    _save_version(db, skill)

    record_audit(
        db=db, action="skill.create", entity_type="accounting_skill",
        entity_id=skill.id, actor=str(user_id),
        details=json.dumps({"name": name, "risk_level": risk_level, "steps": len(redacted_steps)}),
    )

    return {
        "ok": True,
        "skill_id": skill.id,
        "name": skill.name,
        "risk_level": risk_level,
        "trigger_phrases": trigger_phrases,
        "steps_count": len(redacted_steps),
        "approval_required": skill.approval_required,
    }


def _save_version(db: Session, skill: AccountingSkill) -> AccountingSkillVersion:
    version = AccountingSkillVersion(
        skill_id=skill.id,
        user_id=skill.user_id,
        version=skill.version,
        name=skill.name,
        description=skill.description,
        trigger_phrases_json=skill.trigger_phrases_json,
        workflow_steps_json=skill.workflow_steps_json,
        variables_json=skill.variables_json,
        safety_rules_json=skill.safety_rules_json,
        approval_required=skill.approval_required,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update_skill(db: Session, user_id: int, skill_id: int, updates: dict) -> dict:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
    ).first()
    if not skill:
        return {"ok": False, "error": "Skill not found"}

    name = updates.get("name", skill.name)
    steps = []
    if "workflow_steps_json" in updates:
        try:
            steps = json.loads(updates["workflow_steps_json"])
        except (json.JSONDecodeError, TypeError):
            steps = []
    else:
        try:
            steps = json.loads(skill.workflow_steps_json) if skill.workflow_steps_json else []
        except (json.JSONDecodeError, TypeError):
            steps = []

    danger = _is_dangerous_skill(name, steps)
    if danger:
        return {"ok": False, "error": danger}

    skill.version += 1
    skill.updated_at = datetime.utcnow()

    for field in ("name", "description", "trigger_phrases_json", "workflow_steps_json",
                  "variables_json", "safety_rules_json", "approval_required", "status"):
        if field in updates:
            setattr(skill, field, updates[field])

    db.commit()
    db.refresh(skill)
    _save_version(db, skill)

    record_audit(
        db=db, action="skill.update", entity_type="accounting_skill",
        entity_id=skill.id, actor=str(user_id),
        details=json.dumps({"name": skill.name, "version": skill.version}),
    )

    return {
        "ok": True,
        "skill_id": skill.id,
        "name": skill.name,
        "version": skill.version,
    }


def restore_skill_version(db: Session, user_id: int, skill_id: int, version: int) -> dict:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
    ).first()
    if not skill:
        return {"ok": False, "error": "Skill not found"}

    old_version = db.query(AccountingSkillVersion).filter(
        AccountingSkillVersion.skill_id == skill_id,
        AccountingSkillVersion.version == version,
    ).first()
    if not old_version:
        return {"ok": False, "error": f"Version {version} not found"}

    skill.version += 1
    skill.name = old_version.name
    skill.description = old_version.description
    skill.trigger_phrases_json = old_version.trigger_phrases_json
    skill.workflow_steps_json = old_version.workflow_steps_json
    skill.variables_json = old_version.variables_json
    skill.safety_rules_json = old_version.safety_rules_json
    skill.approval_required = old_version.approval_required
    skill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(skill)
    _save_version(db, skill)

    record_audit(
        db=db, action="skill.restore", entity_type="accounting_skill",
        entity_id=skill.id, actor=str(user_id),
        details=json.dumps({"restored_from_version": version, "new_version": skill.version}),
    )

    return {"ok": True, "skill_id": skill.id, "version": skill.version, "restored_from_version": version}


def find_skill_by_phrase(db: Session, phrase: str, user_id: int) -> dict | None:
    """Find best matching skill. Returns simplified dict (no steps)."""
    skills = (
        db.query(AccountingSkill)
        .filter(AccountingSkill.user_id == user_id, AccountingSkill.status == "active")
        .all()
    )
    ql = phrase.lower().strip()
    best_match = None
    best_score = 0

    for skill in skills:
        score = 0
        if skill.trigger_phrases_json:
            try:
                phrases = json.loads(skill.trigger_phrases_json)
                if isinstance(phrases, list):
                    for p in phrases:
                        if isinstance(p, str) and p.lower() in ql:
                            score = max(score, 0.9)
                        if isinstance(p, str) and ql in p.lower():
                            score = max(score, 1.0)
            except (json.JSONDecodeError, TypeError):
                pass
        if skill.name and ql in skill.name.lower():
            score = max(score, 0.8)
        if skill.description and ql in skill.description.lower():
            score = max(score, 0.6)

        if score > best_score:
            best_score = score
            best_match = skill

    if not best_match or best_score < 0.5:
        return None

    return {
        "skill_id": best_match.id,
        "name": best_match.name,
        "description": best_match.description,
        "confidence": best_score,
        "trigger_phrases": json.loads(best_match.trigger_phrases_json) if best_match.trigger_phrases_json else [],
        "steps_count": len(json.loads(best_match.workflow_steps_json)) if best_match.workflow_steps_json else 0,
        "approval_required": best_match.approval_required,
        "run_count": best_match.run_count,
    }


def find_skill_for_command(db: Session, command: str, user_id: int) -> dict | None:
    """Find best matching skill with full details including steps.
    Returns None if confidence < 0.6 (no match).
    Confidence >= 0.85: strong match
    Confidence 0.60-0.84: possible match
    """
    skills = (
        db.query(AccountingSkill)
        .filter(AccountingSkill.user_id == user_id, AccountingSkill.status == "active")
        .all()
    )
    ql = command.lower().strip()
    best_match = None
    best_score = 0
    matched_trigger = ""

    for skill in skills:
        score = 0
        matched = ""
        if skill.trigger_phrases_json:
            try:
                phrases = json.loads(skill.trigger_phrases_json)
                if isinstance(phrases, list):
                    for p in phrases:
                        if isinstance(p, str):
                            pl = p.lower()
                            if ql in pl:
                                # command is a substring of trigger phrase
                                s = max(score, 0.7 + (len(ql) / max(len(pl), 1)) * 0.3)
                                if s > score:
                                    score = s
                                    matched = p
                            elif pl in ql:
                                # trigger phrase is a substring of command
                                s = max(score, 0.8 + (len(pl) / max(len(ql), 1)) * 0.2)
                                if s > score:
                                    score = s
                                    matched = p
                            else:
                                # Fuzzy word overlap: count shared words
                                q_words = set(ql.split())
                                p_words = set(pl.split())
                                if q_words and p_words:
                                    overlap = q_words & p_words
                                    if overlap:
                                        overlap_ratio = len(overlap) / max(len(p_words), 1)
                                        s = 0.5 + overlap_ratio * 0.4
                                        if s > score:
                                            score = s
                                            matched = p
            except (json.JSONDecodeError, TypeError):
                pass
        if skill.name and ql in skill.name.lower():
            score = max(score, 0.75)
            if not matched:
                matched = skill.name
        if skill.description and ql in skill.description.lower():
            score = max(score, 0.6)
            if not matched:
                matched = skill.description[:60]

        if score > best_score:
            best_score = score
            best_match = skill
            matched_trigger = matched

    if not best_match or best_score < 0.6:
        return None

    steps = json.loads(best_match.workflow_steps_json) if best_match.workflow_steps_json else []
    safety = json.loads(best_match.safety_rules_json) if best_match.safety_rules_json else {}
    phrases = json.loads(best_match.trigger_phrases_json) if best_match.trigger_phrases_json else []

    return {
        "skill_id": best_match.id,
        "name": best_match.name,
        "description": best_match.description,
        "confidence": min(best_score, 1.0),
        "match_type": "strong" if best_score >= 0.85 else "possible",
        "matched_trigger": matched_trigger,
        "trigger_phrases": phrases,
        "steps": steps,
        "safety_rules": safety,
        "approval_required": best_match.approval_required,
        "run_count": best_match.run_count,
        "version": best_match.version,
    }


def dry_run_skill(db: Session, user_id: int, skill_id: int) -> dict:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
        AccountingSkill.status == "active",
    ).first()
    if not skill:
        return {"ok": False, "error": "Skill not found"}

    steps = json.loads(skill.workflow_steps_json) if skill.workflow_steps_json else []
    result = {
        "skill_id": skill.id,
        "name": skill.name,
        "dry_run": True,
        "steps_preview": steps,
        "safety_rules": json.loads(skill.safety_rules_json) if skill.safety_rules_json else {},
        "approval_required": skill.approval_required,
    }

    run = AccountingSkillRun(
        skill_id=skill_id,
        user_id=user_id,
        command_text=f"dry-run: {skill.name}",
        status="dry_run",
        dry_run_result_json=json.dumps(result),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {"ok": True, "run_id": run.id, "result": result}


def execute_skill(db: Session, user_id: int, skill_id: int, variables: dict | None = None) -> dict:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
        AccountingSkill.status == "active",
    ).first()
    if not skill:
        return {"ok": False, "error": "Skill not found"}

    if skill.approval_required:
        return {"ok": False, "error": "Approval required before live execution. Run dry-run first and approve."}

    steps = json.loads(skill.workflow_steps_json) if skill.workflow_steps_json else []

    if variables:
        resolved = []
        for step in steps:
            step_copy = dict(step)
            for key in ("instruction", "target", "expected_result"):
                if key in step_copy and isinstance(step_copy[key], str):
                    for var_name, var_value in variables.items():
                        step_copy[key] = step_copy[key].replace(f"{{{var_name}}}", str(var_value))
            resolved.append(step_copy)
        steps = resolved

    resolved_variables = variables or {}

    run = AccountingSkillRun(
        skill_id=skill_id,
        user_id=user_id,
        command_text=f"live: {skill.name}",
        resolved_variables_json=json.dumps(resolved_variables) if resolved_variables else None,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    result = {
        "run_id": run.id,
        "skill_id": skill.id,
        "name": skill.name,
        "steps_executed": len(steps),
        "status": "running",
    }

    skill.run_count = (skill.run_count or 0) + 1
    skill.last_used_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "run_id": run.id, "result": result}


def complete_skill_run(db: Session, run_id: int, user_id: int, result_json: str | None = None) -> dict:
    run = db.query(AccountingSkillRun).filter(
        AccountingSkillRun.id == run_id,
        AccountingSkillRun.user_id == user_id,
    ).first()
    if not run:
        return {"ok": False, "error": "Run not found"}
    run.status = "completed"
    run.live_result_json = result_json
    run.completed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "run_id": run.id}


def list_skills(db: Session, user_id: int, status: str | None = None) -> list[dict]:
    q = db.query(AccountingSkill).filter(AccountingSkill.user_id == user_id)
    if status:
        q = q.filter(AccountingSkill.status == status)
    skills = q.order_by(AccountingSkill.updated_at.desc()).all()

    result = []
    for s in skills:
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "trigger_phrases": json.loads(s.trigger_phrases_json) if s.trigger_phrases_json else [],
            "steps_count": len(json.loads(s.workflow_steps_json)) if s.workflow_steps_json else 0,
            "approval_required": s.approval_required,
            "version": s.version,
            "status": s.status,
            "run_count": s.run_count,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        })
    return result


def get_skill(db: Session, user_id: int, skill_id: int) -> dict | None:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
    ).first()
    if not skill:
        return None

    steps = json.loads(skill.workflow_steps_json) if skill.workflow_steps_json else []
    variables = json.loads(skill.variables_json) if skill.variables_json else []
    safety = json.loads(skill.safety_rules_json) if skill.safety_rules_json else {}
    phrases = json.loads(skill.trigger_phrases_json) if skill.trigger_phrases_json else []

    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "trigger_phrases": phrases,
        "workflow_steps": steps,
        "variables": variables,
        "safety_rules": safety,
        "approval_required": skill.approval_required,
        "version": skill.version,
        "status": skill.status,
        "run_count": skill.run_count,
        "last_used_at": skill.last_used_at.isoformat() if skill.last_used_at else None,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


def get_skill_versions(db: Session, user_id: int, skill_id: int) -> list[dict]:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
    ).first()
    if not skill:
        return []

    versions = (
        db.query(AccountingSkillVersion)
        .filter(AccountingSkillVersion.skill_id == skill_id)
        .order_by(AccountingSkillVersion.version.desc())
        .all()
    )

    result = []
    for v in versions:
        result.append({
            "version": v.version,
            "name": v.name,
            "description": v.description,
            "trigger_phrases": json.loads(v.trigger_phrases_json) if v.trigger_phrases_json else [],
            "steps_count": len(json.loads(v.workflow_steps_json)) if v.workflow_steps_json else 0,
            "approval_required": v.approval_required,
            "created_at": v.created_at.isoformat(),
        })
    return result


def list_skill_runs(db: Session, user_id: int, skill_id: int | None = None, limit: int = 50) -> list[dict]:
    q = db.query(AccountingSkillRun).filter(AccountingSkillRun.user_id == user_id)
    if skill_id:
        q = q.filter(AccountingSkillRun.skill_id == skill_id)
    runs = q.order_by(AccountingSkillRun.created_at.desc()).limit(limit).all()

    result = []
    for r in runs:
        result.append({
            "id": r.id,
            "skill_id": r.skill_id,
            "command_text": r.command_text,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return result


def archive_skill(db: Session, user_id: int, skill_id: int) -> dict:
    skill = db.query(AccountingSkill).filter(
        AccountingSkill.id == skill_id,
        AccountingSkill.user_id == user_id,
    ).first()
    if not skill:
        return {"ok": False, "error": "Skill not found"}
    skill.status = "archived"
    skill.updated_at = datetime.utcnow()
    db.commit()

    record_audit(
        db=db, action="skill.archive", entity_type="accounting_skill",
        entity_id=skill.id, actor=str(user_id),
    )

    return {"ok": True, "skill_id": skill.id}
