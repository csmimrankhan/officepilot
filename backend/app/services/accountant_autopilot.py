from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .accountant_agent import build_task_plan, classify_task_risk
from .accounting_skills import find_skill_for_command
from .agent_context import build_agent_context
from .agent_memory import (
    find_recent_workflow,
    find_yesterday_workflows,
    get_plan,
    get_workflow_memory,
    list_workflow_memory,
)
from .multilingual_command import detect_language, translate_to_internal_english
from .safety import activate_kill_switch

logger = logging.getLogger("officepilot.accountant_autopilot")

WORKFLOW_TRIGGER_PATTERNS = re.compile(
    r"(use\s+.*workflow|run\s+.*workflow|repeat\s+.*workflow|"
    r"same\s+as\s+(yesterday|before|last)|"
    r"workflow\s+.*repeat\s+karo|"
    r"kal\s+wala\s+workflow|"
    r"pichla\s+workflow)",
    re.IGNORECASE,
)

YESTERDAY_PATTERNS = re.compile(r"\b(kal|yesterday)\b", re.IGNORECASE)
TODAY_PATTERNS = re.compile(r"\b(aaj|aj|today)\b", re.IGNORECASE)
WORKFLOW_SAVE_PATTERNS = re.compile(
    r"(save\s+(this|current|as)\s+(workflow|task)|"
    r"is\s+(workflow|task)\s+(ko\s+)?save\s+kar)",
    re.IGNORECASE,
)


def _check_skill_match(db: Session, command_text: str, user) -> dict | None:
    match = find_skill_for_command(db, command_text, user.id)
    if not match:
        return None

    lang = detect_language(command_text)
    is_strong = match["match_type"] == "strong"
    voice_reply_text = (
        f"I found a saved skill '{match['name']}' (confidence {match['confidence']:.0%}). Do you want to dry-run it?"
        if is_strong else
        f"I found a possible match '{match['name']}' (confidence {match['confidence']:.0%}). Do you want to try it?"
    )

    result = {
        "type": "skill_match",
        "matched_skill": match,
        "voice_reply": voice_reply_text,
        "suggested_actions": ["dry_run_skill", "create_new_plan", "edit_skill", "cancel"] if is_strong
                             else ["dry_run_skill", "create_new_plan", "cancel"],
        "language": lang,
        "clarification_needed": False,
        "clarification_question": None,
        "blocked_reason": None,
    }

    # Build a plan-like structure so the frontend can transition to execution
    steps = match.get("steps", [])
    result["steps"] = steps
    result["step_count"] = len(steps)
    result["risk_level"] = match.get("safety_rules", {}).get("max_risk_level", "low")
    result["requires_approval"] = match.get("approval_required", True)
    result["can_save_workflow"] = False

    return result


# Folder invoice workflow command patterns
FOLDER_INVOICE_PATTERNS = re.compile(
    r"(scan.*folder.*invoice|"
    r"find.*invoice.*file|extract.*invoice.*folder|"
    r"invoice.*folder.*excel|"
    r"sava.*invoice|"
    r"daily.*invoice(?!.*email)|"
    r"invoice.*process\s*karo|"
    r"invoice.*sa.*excel.*banao|"
    r"invoice.*total.*batao|"
    r"aj.*ki.*invoice(?!.*email))",
    re.IGNORECASE,
)

# P&L comparison command patterns
PNL_COMPARISON_PATTERNS = re.compile(
    r"(open\s+quickbooks.*(?:pnl|P&L|profit.*loss|profit.*loss)|"
    r"(?:pnl|P&L|profit.*loss|profit.*loss).*compar|"
    r"compare.*(?:pnl|P&L|profit.*loss|monthly.*profit)|"
    r"monthly.*(?:pnl|P&L|profit|compar)|"
    r"(?:last\s+month|previous\s+month).*(?:pnl|P&L|profit)|"
    r"(?:pnl|P&L).*(?:differ|difference|change)|"
    r"quickbooks.*monthly|"
    r"quickbooks.*report)",
    re.IGNORECASE,
)


# Multi-word filler phrases to remove before tokenization (longer first)
FILLER_PHRASES = [
    r"summary create karte the",
    r"summary create karo",
    r"summary banao",
    r"ke naam ki",
    r"ki naam ki",
    r"naam ki",
    r"ki file ko",
    r"ki file",
    r"wali file",
    r"wala file",
    r"wale file",
    r"file hai",
    r"uske bare mein",
    r"uske baray mein",
    r"uski summary",
    r"uski samri",
    r"uske naam ki",
    r"uska naam",
    r"mujhe batao",
    r"muje batao",
    r"mujhe bataye",
    r"read karo",
    r"open karo",
    r"padh karo",
    r"ka naam",
]

STOP_WORDS_QUERY = {
    "download", "downloads", "folder", "mein", "me", "se", "sy",
    "ke", "ki", "ka", "kay", "ko",
    "naam", "file", "excel", "xlsx", "xls", "csv",
    "sheet", "spreadsheet", "workbook",
    "read", "open", "karo", "karna", "kar",
    "kholo", "padho",
    "aur", "or",
    "uski", "uske", "uska", "iske", "iska", "is", "in",
    "mujhe", "muje", "mujhy",
    "batao", "bata", "bataye",
    "samri", "summary", "samary", "summry", "summarize",
    "create", "create", "banao", "nikalo", "nikaalo",
    "bare", "baare",
    "about", "hisaab", "total",
    "pdf", "name", "named", "with",
    "the", "a", "an", "and", "for", "in", "of", "to", "is", "it",
    "data", "new", "old",
    "search", "find",
    "entry", "amount",
    "debit", "credit", "kitni", "kitna",
    "hai", "hy", "hee", "hain",
    "wali", "wala", "wale",
}


def _extract_file_query(normalized: str) -> str:
    """Extract meaningful filename search keywords from a Roman Urdu/English command."""
    query = normalized.lower()
    # Remove multi-word filler phrases first
    for phrase in FILLER_PHRASES:
        query = re.sub(phrase, " ", query)
    # Tokenize and remove individual stop words
    tokens = query.split()
    filtered = [t for t in tokens if t not in STOP_WORDS_QUERY and len(t) > 1]
    # Filter out pure numbers and single chars
    filtered = [t for t in filtered if not t.isdigit()]
    return " ".join(filtered).strip() or ""


def _build_excel_downloads_summary_plan(query: str, normalized: str) -> dict:
    summary_text = f"I will search your Downloads folder for an Excel or CSV file matching '{query}' and create a summary."
    if not query:
        summary_text = "I will search your Downloads folder for an Excel or CSV file. If I find more than one, I'll ask you to choose."
    return {
        "task_title": "Excel Summary from Downloads",
        "task_type": "excel_summary_from_downloads",
        "summary_for_user": summary_text,
        "risk_level": "medium",
        "requires_approval": True,
        "clarification_needed": False,
        "clarification_question": None,
        "can_save_workflow": True,
        "blocked_reason": None,
        "steps": [
            {
                "step_order": 1,
                "step_type": "file_find_in_downloads",
                "tool": "file_find_in_downloads",
                "target": "Downloads",
                "instruction": f"Search Downloads folder for Excel or CSV files matching '{query or 'any'}'.",
                "expected_result": "File found, needs file selected, or file picker shown.",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {
                    "query": query,
                    "extensions": [".xlsx", ".xls", ".csv"],
                    "max_results": 10,
                },
            },
            {
                "step_order": 2,
                "step_type": "excel_create_summary_from_file",
                "tool": "excel_create_summary_from_file",
                "target": "Excel file",
                "instruction": "Create a summary from the selected spreadsheet with auto-detected columns and totals.",
                "expected_result": "Summary created with grouped totals.",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"path": "{selected_file_path}"},
            },
        ],
    }


def _build_email_download_plan(query: str, normalized: str) -> dict:
    summary_text = f"I will search Gmail for invoice or report emails matching your request and download the attachments."
    return {
        "task_title": "Email Attachment Download",
        "task_type": "email_download",
        "summary_for_user": summary_text,
        "risk_level": "medium",
        "requires_approval": True,
        "clarification_needed": False,
        "clarification_question": None,
        "can_save_workflow": True,
        "blocked_reason": None,
        "steps": [
            {
                "step_order": 1,
                "step_type": "email_search",
                "tool": "email_search",
                "target": "Gmail",
                "instruction": "Search Gmail for invoice, receipt, bill, or report emails from the last 30 days.",
                "expected_result": "List of matched email messages found.",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {
                    "query": query or "has:attachment newer_than:30d (invoice OR receipt OR bill OR report)",
                    "max_results": 10,
                },
            },
            {
                "step_order": 2,
                "step_type": "email_preview_messages",
                "tool": "email_preview_messages",
                "target": "User",
                "instruction": "Show the matched emails with sender, subject, date, and attachment names for review.",
                "expected_result": "User reviews the email list.",
                "requires_approval": True,
                "risk_level": "low",
                "parameters": {},
            },
            {
                "step_order": 3,
                "step_type": "email_download_attachments",
                "tool": "email_download_attachments",
                "target": "Gmail attachments",
                "instruction": "Download all attachments from the approved emails to the local Downloads folder.",
                "expected_result": "Attachment files saved locally.",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {
                    "output_folder": "{downloads_folder}",
                },
            },
            {
                "step_order": 4,
                "step_type": "approval_checkpoint",
                "tool": "approval_request",
                "target": "User",
                "instruction": "Confirm the downloaded files and decide next steps.",
                "expected_result": "User reviews downloaded files.",
                "requires_approval": True,
                "risk_level": "low",
                "parameters": {"prompt": "Attachments downloaded. Would you like to open the folder or create an Excel summary?"},
            },
        ],
    }


def _build_pdf_unsupported_plan(query: str) -> dict:
    summary = f"I can find and open the PDF matching '{query}', but debit/credit extraction from PDF is not enabled in OfficePilot yet."
    if not query:
        summary = "I can find and open the PDF, but debit/credit extraction from PDF is not enabled yet."
    return {
        "task_title": "PDF Debit/Credit — Unsupported",
        "task_type": "needs_clarification",
        "summary_for_user": summary,
        "risk_level": "low",
        "requires_approval": False,
        "clarification_needed": True,
        "clarification_question": (
            "I can find and open the PDF, but debit/credit extraction from PDF is not enabled "
            "in OfficePilot yet. Would you like me to find and open the file for you instead?"
        ),
        "can_save_workflow": False,
        "blocked_reason": None,
        "steps": [
            {
                "step_order": 1,
                "step_type": "needs_clarification",
                "tool": "needs_clarification",
                "target": "user",
                "instruction": summary,
                "expected_result": "User decides next action.",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
        ],
    }


def build_accountant_plan(
    db: Session,
    command_text: str,
    user: object,
    force_new_plan: bool = False,
) -> dict:
    lang = detect_language(command_text)
    normalized = command_text.strip().lower()

    # Step 1: Safety gate — block dangerous commands (language-agnostic)
    risk = classify_task_risk(normalized, None)
    if risk.get("risk_level") == "blocked":
        blocked_reason = risk["reason"]
        summary = risk.get("message", risk["reason"])
        return {
            "task_title": "Blocked Task",
            "task_summary": summary,
            "platform_detected": "unknown",
            "risk_level": "blocked",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": blocked_reason,
            "clarification_needed": False,
            "clarification_question": None,
        }

    # Step 2: Navigation commands — handle before LLM (language-agnostic)
    NAVIGATION_COMMANDS = {
        "voice": re.compile(
            r"(open\s+voice\s+command|voice\s+commands?|voice\s+command\s+center)", re.IGNORECASE
        ),
        "workflow_memory": re.compile(
            r"(show\s+workflow\s+memory|workflow\s+memory|open\s+workflow\s+memory)", re.IGNORECASE
        ),
        "settings": re.compile(
            r"(open\s+settings|go\s+to\s+settings)", re.IGNORECASE
        ),
    }
    NAVIGATION_ROUTES = {
        "voice": "/voice",
        "workflow_memory": "/app/workflow-memory",
        "settings": "/app/settings",
    }
    for nav_key, nav_pattern in NAVIGATION_COMMANDS.items():
        if nav_pattern.search(normalized):
            return {
                "type": "navigation",
                "task_title": "Navigation",
                "task_type": "navigation",
                "target": nav_key,
                "route": NAVIGATION_ROUTES[nav_key],
                "message": f"Opening {nav_key.replace('_', ' ').title()}.",
                "status": "success",
                "language": lang,
                "risk_level": "low",
                "requires_approval": False,
                "can_save_workflow": False,
                "can_record_workflow": False,
                "steps": [],
                "blocked_reason": None,
                "clarification_needed": False,
                "clarification_question": None,
            }

    # Step 2.5: Emergency kill switch activation (multi-language)
    KILL_PHRASES = [
        "emergency stop", "kill switch", "abort",
        "arrêt d'urgence", "interrupteur d'arrêt",
        "parada de emergencia", "interruptor de emergencia", "detener",
        "notfall stop", "notaus", "sofort stop",
        "emergency band karo", "kill switch on karo",
        "stop karo sab", "sab band karo", "turant band karo",
        "fauri band karo", "stop everything",
    ]
    for phrase in KILL_PHRASES:
        if phrase in normalized:
            user_email = str(getattr(user, 'email', 'voice')) if user else 'voice'
            activate_kill_switch(db, activated_by=user_email, reason="Voice emergency stop")
            logger.warning("Kill switch activated via voice command by %s", user_email)
            return {
                "type": "kill_switch_activated",
                "task_title": "Kill Switch Activated",
                "task_type": "kill_switch_activated",
                "summary_for_user": "Kill switch activated. All automation is stopped.",
                "status": "completed",
                "language": lang,
                "risk_level": "low",
                "requires_approval": False,
                "can_save_workflow": False,
                "can_record_workflow": False,
                "steps": [],
                "blocked_reason": None,
                "clarification_needed": False,
                "clarification_question": None,
            }

    # --- LLM-first planning ---
    # All language-specific regex cascades (Roman Urdu Excel Downloads,
    # PDF Debit/Credit, Recording commands, Skill Match, Workflow Replay,
    # Folder Invoice, P&L Comparison, English Excel Commands) have been removed.
    # The LLM (mock or cloud provider) is the primary intent engine,
    # enabling understanding of commands in any natural language.
    #
    # The original command_text (in any language) is passed directly to the
    # LLM provider. The system prompt instructs the LLM to understand and
    # conceptually translate the input, then produce a structured JSON plan.

    plan_data = build_task_plan(command_text)

    context = build_agent_context(db, user)
    risk = classify_task_risk(command_text, context)

    plan_data["risk_level"] = risk.get("risk_level", plan_data.get("risk_level", "low"))
    plan_data["requires_approval"] = risk.get("requires_approval", plan_data.get("requires_approval", True))

    if "today" in normalized or "aaj" in normalized:
        plan_data = _resolve_today_variables(plan_data)
    if "yesterday" in normalized or "kal" in normalized:
        plan_data = _resolve_yesterday_variables(plan_data)

    # Detect needs_clarification from steps and auto-set clarification fields
    steps = plan_data.get("steps", [])
    has_clarification_step = any(
        s.get("step_type") == "needs_clarification" for s in steps
    )
    if has_clarification_step:
        plan_data["clarification_needed"] = True
        plan_data["task_title"] = "Clarification Needed"
        plan_data["task_type"] = "needs_clarification"
        if not plan_data.get("clarification_question"):
            plan_data["clarification_question"] = (
                "I can help with Excel summaries, Gmail attachment downloads, "
                "recording workflows, and local invoice processing. "
                "Could you be more specific about what you'd like me to do?"
            )

    # Only set can_save_workflow for real task plans, not navigation or fallback
    if plan_data.get("task_type") not in ("navigation", "needs_clarification") and plan_data.get("type") != "navigation":
        can_save = WORKFLOW_SAVE_PATTERNS.search(normalized) is not None
        # Preserve existing can_save_workflow from provider (e.g. mock sets True for Excel downloads)
        plan_data.setdefault("can_save_workflow", can_save)

    if not plan_data.get("task_title") or plan_data.get("task_title") in (
        "Parse Error",
        "Clarification Needed",
        "Cloud Unavailable (Fallback)",
    ):
        plan_data = _fallback_plan(
            normalized,
            plan_data.get("task_title", ""),
            risk_level=plan_data.get("risk_level", "low"),
            requires_approval=plan_data.get("requires_approval", True),
            blocked_reason=plan_data.get("blocked_reason"),
        )

    plan_data["language"] = lang
    return plan_data


def _check_workflow_replay(db: Session, normalized: str, user) -> dict | None:
    if not WORKFLOW_TRIGGER_PATTERNS.search(normalized):
        return None

    if YESTERDAY_PATTERNS.search(normalized):
        yesterday_wfs = find_yesterday_workflows(db, user_id=user.id)
        if yesterday_wfs:
            wf = yesterday_wfs[0]
            return {
                "task_title": f"Repeat Workflow: {wf.workflow_name}",
                "task_type": "workflow_replay",
                "language": detect_language(normalized),
                "summary_for_user": f"Repeating yesterday's workflow '{wf.workflow_name}' for today.",
                "risk_level": "medium",
                "requires_approval": True,
                "clarification_needed": False,
                "clarification_question": None,
                "can_save_workflow": False,
                "workflow_memory_id": wf.id,
                "workflow_name": wf.workflow_name,
                "is_replay": True,
                "steps": _steps_from_workflow(wf),
                "blocked_reason": None,
            }
        return None

    wf_name_match = re.search(
        r"(?:use|run|repeat)\s+['\"]?([a-zA-Z0-9\s_-]+?)['\"]?\s+(?:workflow|task|process)",
        normalized,
    )
    if wf_name_match:
        name = wf_name_match.group(1).strip()
        found = find_recent_workflow(db, name, user_id=user.id)
        if found:
            return {
                "task_title": f"Repeat Workflow: {found.workflow_name}",
                "task_type": "workflow_replay",
                "language": detect_language(normalized),
                "summary_for_user": f"Running workflow '{found.workflow_name}'.",
                "risk_level": "medium",
                "requires_approval": True,
                "clarification_needed": False,
                "clarification_question": None,
                "can_save_workflow": False,
                "workflow_memory_id": found.id,
                "workflow_name": found.workflow_name,
                "is_replay": True,
                "steps": _steps_from_workflow(found),
                "blocked_reason": None,
            }

    return None


FOLDER_INVOICE_TRIGGER_PHRASES = [
    "scan folders for invoices",
    "find today invoices",
    "aj ki invoices search karo",
    "invoice folder sa extract karo",
    "daily invoice excel banao",
    "daily invoices workflow",
    "sava ki invoices check karo",
    "sava detail excel mein daalo",
    "invoice total karo",
    "invoices ka total batao",
]


def _check_folder_invoice(normalized: str) -> dict | None:
    if not FOLDER_INVOICE_PATTERNS.search(normalized):
        return None
    return _build_folder_invoice_plan()


def _build_folder_invoice_plan() -> dict:
    return {
        "task_title": "Daily Invoices from Folder",
        "task_type": "local_folder_invoice_workflow",
        "language": "en",
        "summary_for_user": "I will scan your desktop / downloads / invoices folders for today's invoice files, extract data from each file, create a Daily Invoices Excel workbook, calculate totals, and save the workflow.",
        "risk_level": "medium",
        "requires_approval": True,
        "clarification_needed": False,
        "clarification_question": None,
        "can_save_workflow": True,
        "blocked_reason": None,
        "steps": [
            {
                "step_order": 1,
                "step_type": "scan_local_folder",
                "tool": "scan_local_folder",
                "target": "file system",
                "instruction": "Scan Desktop, Downloads, and Documents/invoices folders for invoice files (PDF, images, spreadsheets) created or modified today",
                "expected_result": "List of invoice files found in local folders",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"folder_path": "", "date_filter": "today", "keywords": True},
            },
            {
                "step_order": 2,
                "step_type": "extract_invoice_data",
                "tool": "extract_invoice_data",
                "target": "invoice files",
                "instruction": "Extract invoice data from each found file using OCR and PDF parser",
                "expected_result": "Structured invoice data (vendor, amount, date, invoice number) extracted from each file",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"filepath": "{filepath}"},
            },
            {
                "step_order": 3,
                "step_type": "create_daily_invoices_excel",
                "tool": "create_daily_invoices_excel",
                "target": "Excel",
                "instruction": "Create Daily_Invoices_{date}.xlsx with invoice detail sheet and summary sheet",
                "expected_result": "Excel workbook created in exports/invoices/ folder",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {},
            },
            {
                "step_order": 4,
                "step_type": "calculate_excel_total",
                "tool": "calculate_excel_total",
                "target": "Excel",
                "instruction": "Calculate total amounts from the Excel workbook (done by code, not LLM)",
                "expected_result": "Total invoice amount calculated and added to summary sheet",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
            {
                "step_order": 5,
                "step_type": "save_report_workflow",
                "tool": "save_report_workflow",
                "target": "workflow",
                "instruction": "Ask user if they want to save this invoice workflow for daily repeat",
                "expected_result": "Workflow saved if user agrees",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
        ],
    }


PNL_TRIGGER_PHRASES = [
    "monthly pnl comparison",
    "compare profit and loss",
    "compare quickbooks pnl",
    "last month pnl difference",
    "monthly profit report",
    "quickbooks monthly pnl",
    "pnl comparison",
]

# Excel/Skill Pack command patterns
EXCEL_PATTERNS = re.compile(
    r"(excel\s+summary|"
    r"summarize\s+(spreadsheet|excel|workbook)|"
    r"create\s+(excel\s+)?summary|"
    r"apply\s+formula|add\s+formula|calculate\s+total|sum\s+column|"
    r"create\s+pivot\s+table|pivot\s+by|summarize\s+by|"
    r"clean\s+(this\s+)?(excel|csv|spreadsheet|file)|"
    r"compare\s+(two\s+)?excel|find\s+difference|"
    r"split\s+by\s+category|"
    r"format\s+(excel|spreadsheet|report)|"
    r"freeze\s+(top\s+)?row|"
    r"header\s+format|"
    r"currency\s+format|"
    r"auto.?size\s+column|"
    r"old\s+excel|excel\s+2010|excel\s+2013|excel\s+2016|compatibility\s+mode|"
    r"google\s+sheet|"
    r"excel\s+workflow|"
    r"excel\s+skill)",
    re.IGNORECASE,
)

EXCEL_TRIGGER_PHRASES = [
    "create excel summary",
    "summarize this spreadsheet",
    "apply formula",
    "create pivot table by vendor",
    "clean this csv",
    "compare two excel files",
    "add total formula",
]


def _check_excel_command(normalized: str) -> dict | None:
    if not EXCEL_PATTERNS.search(normalized):
        return None
    return _build_excel_plan(normalized)


def _build_excel_plan(normalized: str) -> dict:
    # Detect specific intents
    is_summary = bool(re.search(r"(summary|summarize)", normalized))
    is_pivot = bool(re.search(r"(pivot|summarize\s+by|group\s+by)", normalized))
    is_formula = bool(re.search(r"(formula|total|sum\s+column|calculate)", normalized))
    is_clean = bool(re.search(r"(clean|fix)", normalized))
    is_compare = bool(re.search(r"(compare|difference)", normalized))
    is_split = bool(re.search(r"(split|category|separate)", normalized))
    is_format = bool(re.search(r"(format|header|freeze|auto.?size|currency)", normalized))
    is_compat = bool(re.search(r"(old\s+excel|compatibility|2010|2013|2016)", normalized))
    is_google = bool(re.search(r"google\s+sheet", normalized))

    clarity = ""
    if is_summary:
        clarity = "I will ask which Excel file to summarize. The tool auto-detects accounting columns and creates a grouped summary with totals."
    elif is_pivot:
        clarity = "I will ask which Excel file to use, the row field, and the value field for the pivot."
    elif is_formula:
        clarity = "I will ask which file, sheet, cell, and column/range for the formula."
    elif is_clean:
        clarity = "I will ask which CSV or Excel file to clean."
    elif is_compare:
        clarity = "I will ask for the two Excel files to compare."
    elif is_split:
        clarity = "I will ask which file and which category column to split by."
    elif is_format:
        clarity = "I will apply formatting to the active Excel file."
    elif is_compat:
        clarity = "I will use older Excel-compatible formulas."
    elif is_google:
        clarity = "Google Sheets integration is not yet configured."

    summary_text = (
        f"I will help you with your Excel task. {clarity}"
        if clarity else
        "I will help you with your Excel task. A backup copy will be created before any edits."
    )

    steps = []

    if is_summary or is_pivot:
        step_type = "excel_create_summary_from_file"
        steps.append({
            "step_order": 1,
            "step_type": step_type,
            "tool": step_type,
            "target": "Excel file",
            "instruction": "Select and analyze the Excel file to summarize, auto-detect columns, create grouped summary with totals, and save output copy",
            "expected_result": "Summary sheet created in output copy with grouped totals",
            "requires_approval": True,
            "risk_level": "medium",
            "parameters": {"path": "{file_path}", "source_sheet": "{sheet_name}", "group_by_column": "{group_by_column}", "value_column": "{value_column}"},
        })

    elif is_formula:
        steps.append({
            "step_order": 1,
            "step_type": "excel_open_workbook",
            "tool": "excel_open_workbook",
            "target": "Excel file",
            "instruction": "Open the Excel file to inspect",
            "expected_result": "Workbook info",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path}"},
        })
        mode = "excel_2010" if is_compat else "excel_2016"
        steps.append({
            "step_order": 2,
            "step_type": "excel_apply_total_formula",
            "tool": "excel_apply_total_formula",
            "target": "Excel",
            "instruction": f"Apply {'old Excel compatible ' if is_compat else ''}total formula to the amount column",
            "expected_result": "SUM formula added at bottom of column",
            "requires_approval": True,
            "risk_level": "medium",
            "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}", "column_letter": "{column_letter}", "compatibility_mode": mode},
        })

    elif is_clean:
        steps.append({
            "step_order": 1,
            "step_type": "excel_clean_csv",
            "tool": "excel_clean_csv",
            "target": "CSV/Excel file",
            "instruction": "Clean the file by removing empty rows and columns",
            "expected_result": "Cleaned Excel file with normalized data",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path}"},
        })

    elif is_compare:
        steps.append({
            "step_order": 1,
            "step_type": "excel_open_workbook",
            "tool": "excel_open_workbook",
            "target": "Excel file A",
            "instruction": "Open first Excel file",
            "expected_result": "First workbook info",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path_a}"},
        })
        steps.append({
            "step_order": 2,
            "step_type": "excel_open_workbook",
            "tool": "excel_open_workbook",
            "target": "Excel file B",
            "instruction": "Open second Excel file",
            "expected_result": "Second workbook info",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path_b}"},
        })
        steps.append({
            "step_order": 3,
            "step_type": "excel_compare_workbooks",
            "tool": "excel_compare_workbooks",
            "target": "both files",
            "instruction": "Compare the two workbooks and report differences",
            "expected_result": "Comparison report with row-by-row differences",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path_a": "{file_path_a}", "path_b": "{file_path_b}"},
        })

    elif is_split:
        steps.append({
            "step_order": 1,
            "step_type": "excel_open_workbook",
            "tool": "excel_open_workbook",
            "target": "Excel file",
            "instruction": "Open the Excel file",
            "expected_result": "Workbook info",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path}"},
        })
        steps.append({
            "step_order": 2,
            "step_type": "excel_split_by_category",
            "tool": "excel_split_by_category",
            "target": "Excel",
            "instruction": "Split data into separate sheets by category column",
            "expected_result": "Multiple category sheets created",
            "requires_approval": True,
            "risk_level": "medium",
            "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}", "category_column": "{category_column}"},
        })

    elif is_format or is_google:
        steps.append({
            "step_order": 1,
            "step_type": "excel_format_header",
            "tool": "excel_format_header",
            "target": "Excel file",
            "instruction": "Format the Excel report with proper headers, alignment, and column sizing",
            "expected_result": "Formatted Excel report",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {"path": "{file_path}", "sheet_name": "{sheet_name}"},
        })

    else:
        steps.append({
            "step_order": 1,
            "step_type": "excel_open_workbook",
            "tool": "excel_open_workbook",
            "target": "Excel file",
            "instruction": "Ask user which Excel file to work with and what to do",
            "expected_result": "User provides file path and task details",
            "requires_approval": False,
            "risk_level": "low",
            "parameters": {},
        })

    task_title = "Excel Task"
    task_type = "excel_skill"
    if is_summary:
        task_title = "Create Excel Summary"
        task_type = "excel_summary"
    elif is_pivot:
        task_title = "Create Pivot Table"
        task_type = "excel_pivot"
    elif is_formula:
        task_title = "Apply Formula"
        task_type = "excel_formula"
    elif is_clean:
        task_title = "Clean Excel/CSV"
        task_type = "excel_clean"
    elif is_compare:
        task_title = "Compare Excel Reports"
        task_type = "excel_compare"
    elif is_split:
        task_title = "Split by Category"
        task_type = "excel_split"
    elif is_google:
        task_title = "Google Sheets (Not Configured)"
        task_type = "excel_google_sheets"
    elif is_format:
        task_title = "Format Excel Report"
        task_type = "excel_format"

    needs_file = any(
        "{file_path}" in str(s.get("parameters", {}))
        for s in steps
    )
    needs_sheet = any(
        "{sheet_name}" in str(s.get("parameters", {}))
        for s in steps
    )
    needs_columns = any(
        "{group_by_column}" in str(s.get("parameters", {}))
        for s in steps
    )

    clarifications = []
    if needs_file:
        clarifications.append("Which Excel file should I use?")
    if needs_sheet:
        clarifications.append("Which sheet contains the data?")
    if needs_columns and is_pivot:
        clarifications.append("Which column should I use as the row field and which as the value?")
    elif needs_columns:
        clarifications.append("Which column should I group by and which should I aggregate?")
    if is_formula and not needs_columns:
        clarifications.append("Which column should I total?")

    return {
        "task_title": task_title,
        "task_type": task_type,
        "language": "en",
        "summary_for_user": summary_text,
        "risk_level": "medium",
        "requires_approval": True,
        "clarification_needed": len(clarifications) > 0,
        "clarification_question": " ".join(clarifications) if clarifications else None,
        "can_save_workflow": True,
        "blocked_reason": "Google Sheets integration not configured. Set up Google OAuth credentials to enable." if is_google and not is_format else None,
        "steps": steps,
    }


def _check_pnl_comparison(normalized: str) -> dict | None:
    if not PNL_COMPARISON_PATTERNS.search(normalized):
        return None
    return _build_pnl_plan()


def _build_pnl_plan() -> dict:
    return {
        "task_title": "Monthly P&L Comparison",
        "task_type": "accounting_report_comparison",
        "language": "en",
        "summary_for_user": "I will open QuickBooks, extract this month and last month Profit & Loss reports, compare them, and save the comparison to Excel.",
        "risk_level": "medium",
        "requires_approval": True,
        "clarification_needed": False,
        "clarification_question": None,
        "can_save_workflow": True,
        "blocked_reason": None,
        "steps": [
            {
                "step_order": 1,
                "step_type": "open_accounting_platform",
                "tool": "open_accounting_platform",
                "target": "QuickBooks",
                "instruction": "Open QuickBooks accounting platform",
                "expected_result": "QuickBooks is open and ready",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"platform": "QuickBooks"},
            },
            {
                "step_order": 2,
                "step_type": "wait_for_manual_login",
                "tool": "wait_for_manual_login",
                "target": "user",
                "instruction": "Log in to QuickBooks manually",
                "expected_result": "User is logged in",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
            {
                "step_order": 3,
                "step_type": "navigate_to_profit_loss_report",
                "tool": "navigate_to_profit_loss_report",
                "target": "QuickBooks",
                "instruction": "Navigate to Profit and Loss report",
                "expected_result": "P&L report page is visible",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"platform": "QuickBooks"},
            },
            {
                "step_order": 4,
                "step_type": "set_report_date_range",
                "tool": "set_report_date_range",
                "target": "QuickBooks",
                "instruction": "Set report date range to current month",
                "expected_result": "Date range set to current month",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"period": "current_month", "date_range": "Current Month"},
            },
            {
                "step_order": 5,
                "step_type": "export_accounting_report",
                "tool": "export_accounting_report",
                "target": "QuickBooks",
                "instruction": "Export current month P&L report",
                "expected_result": "Current month P&L exported",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"period": "current_month", "format": "json"},
            },
            {
                "step_order": 6,
                "step_type": "watch_downloaded_report",
                "tool": "watch_downloaded_report",
                "target": "downloads",
                "instruction": "Wait for current month report download",
                "expected_result": "Current month report file detected",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"period": "current_month"},
            },
            {
                "step_order": 7,
                "step_type": "set_report_date_range",
                "tool": "set_report_date_range",
                "target": "QuickBooks",
                "instruction": "Set report date range to previous month",
                "expected_result": "Date range set to previous month",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"period": "previous_month", "date_range": "Previous Month"},
            },
            {
                "step_order": 8,
                "step_type": "export_accounting_report",
                "tool": "export_accounting_report",
                "target": "QuickBooks",
                "instruction": "Export previous month P&L report",
                "expected_result": "Previous month P&L exported",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {"period": "previous_month", "format": "json"},
            },
            {
                "step_order": 9,
                "step_type": "watch_downloaded_report",
                "tool": "watch_downloaded_report",
                "target": "downloads",
                "instruction": "Wait for previous month report download",
                "expected_result": "Previous month report file detected",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"period": "previous_month"},
            },
            {
                "step_order": 10,
                "step_type": "read_pnl_report_file",
                "tool": "read_pnl_report_file",
                "target": "P&L report",
                "instruction": "Read current month P&L report file",
                "expected_result": "Current month P&L data parsed",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"period": "current_month"},
            },
            {
                "step_order": 11,
                "step_type": "read_pnl_report_file",
                "tool": "read_pnl_report_file",
                "target": "P&L report",
                "instruction": "Read previous month P&L report file",
                "expected_result": "Previous month P&L data parsed",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"period": "previous_month"},
            },
            {
                "step_order": 12,
                "step_type": "compare_pnl_reports",
                "tool": "compare_pnl_reports",
                "target": "P&L data",
                "instruction": "Compare current and previous month P&L reports",
                "expected_result": "P&L comparison calculated (by code, not LLM)",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
            {
                "step_order": 13,
                "step_type": "create_pnl_comparison_excel",
                "tool": "create_pnl_comparison_excel",
                "target": "Excel",
                "instruction": "Create Excel workbook with P&L comparison",
                "expected_result": "P&L comparison Excel file created",
                "requires_approval": True,
                "risk_level": "medium",
                "parameters": {},
            },
            {
                "step_order": 14,
                "step_type": "speak_pnl_difference",
                "tool": "speak_pnl_difference",
                "target": "user",
                "instruction": "Tell the user the P&L difference",
                "expected_result": "User hears the P&L comparison summary",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {"language": "en"},
            },
            {
                "step_order": 15,
                "step_type": "save_report_workflow",
                "tool": "save_report_workflow",
                "target": "workflow",
                "instruction": "Ask user to save this as a workflow",
                "expected_result": "Workflow saved if user agrees",
                "requires_approval": False,
                "risk_level": "low",
                "parameters": {},
            },
        ],
    }


def _steps_from_workflow(wf) -> list[dict]:
    try:
        if wf.steps_json:
            steps = json.loads(wf.steps_json)
            if isinstance(steps, list):
                return steps
    except (json.JSONDecodeError, TypeError):
        pass
    return [{"step_order": 1, "step_type": "read_screen", "target": "screen", "instruction": "Read current screen", "requires_approval": False, "risk_level": "low"}]


def _resolve_today_variables(plan_data: dict) -> dict:
    today_str = date.today().isoformat()
    for step in plan_data.get("steps", []):
        params = step.get("parameters", {})
        for k, v in params.items():
            if isinstance(v, str):
                params[k] = v.replace("{today}", today_str).replace("{current_date}", today_str)
    return plan_data


def _resolve_yesterday_variables(plan_data: dict) -> dict:
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    for step in plan_data.get("steps", []):
        params = step.get("parameters", {})
        for k, v in params.items():
            if isinstance(v, str):
                params[k] = v.replace("{yesterday}", yesterday_str).replace("{current_date}", yesterday_str)
    return plan_data


SYSTEM_TODAY = date.today()


def get_system_today() -> date:
    return SYSTEM_TODAY


def _fallback_plan(normalized: str, error: str, risk_level: str = "low", requires_approval: bool = True, blocked_reason: str | None = None) -> dict:
    return {
        "task_title": "Clarification Needed",
        "task_type": "needs_clarification",
        "language": "en",
        "summary_for_user": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
        "risk_level": risk_level,
        "requires_approval": False,
        "clarification_needed": True,
        "clarification_question": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
        "can_save_workflow": False,
        "steps": [
            {
                "step_order": 1,
                "step_type": "needs_clarification",
                "tool": "needs_clarification",
                "action": "inform",
                "target": "user",
                "parameters": {},
                "requires_approval": False,
                "expected_result": "User provides a clearer command.",
                "validation_rule": None,
            },
        ],
        "blocked_reason": blocked_reason,
    }



