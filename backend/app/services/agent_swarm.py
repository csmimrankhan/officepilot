from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from ..services.accountant_agent import build_task_plan
from ..services.tool_registry import TOOL_REGISTRY
from .agent_context import build_agent_context

logger = logging.getLogger("officepilot.agent_swarm")

SPECIALIST_PROFILES: dict[str, dict[str, Any]] = {
    "auditor": {
        "display_name": "Auditor",
        "system_prompt_additions": (
            "You are the OfficePilot AUDITOR agent. Your role is to inspect, verify, and analyze "
            "financial data for accuracy and completeness. Focus on finding duplicate invoices, "
            "missing data fields, anomalies in amounts, and consistency issues. "
            "You must ONLY use read-only tools. You MUST NOT write, edit, or modify any data. "
            "Be thorough and highlight any discrepancies you find."
        ),
        "allowed_tools": [
            "semantic_search_invoices",
            "extract_invoice_data",
            "excel_calculate_and_read",
            "email_search",
            "email_preview_messages",
            "drive_list_recent_files",
            "scan_local_folder",
            "bank_parse_feed",
            "screen_read_text",
            "desktop_get_active_window",
        ],
        "color": "blue",
        "icon": "search",
    },
    "tax": {
        "display_name": "Tax Agent",
        "system_prompt_additions": (
            "You are the OfficePilot TAX agent. Your role is to categorize expenses and ensure "
            "tax compliance. Focus on correct expense categorization, VAT/GST treatment, "
            "deductible vs non-deductible classification, and applying learned correction rules. "
            "You may use correction rules and categorization tools. "
            "You MUST NOT trigger any write-back or data entry tools."
        ),
        "allowed_tools": [
            "semantic_search_invoices",
            "extract_invoice_data",
            "excel_calculate_and_read",
            "bank_parse_feed",
            "bank_reconcile_and_report",
            "screen_read_text",
            "desktop_get_active_window",
        ],
        "color": "green",
        "icon": "calculator",
    },
    "data_entry": {
        "display_name": "Data Entry",
        "system_prompt_additions": (
            "You are the OfficePilot DATA ENTRY agent. Your role is to accurately enter and write "
            "financial data into accounting systems. You have access to write-back and live-editing tools. "
            "You MUST ALWAYS require explicit approval before executing any write operation. "
            "Double-check all values for accuracy before proposing them. Include clear summaries "
            "of what will be written and where."
        ),
        "allowed_tools": [
            "quickbooks_create_bill",
            "xero_create_bill",
            "excel_live_edit_active_workbook",
            "excel_create_pivot_table",
            "excel_switch_workbooks",
            "excel_advanced_formatting",
            "excel_create_chart",
            "excel_create_summary_from_file",
            "excel_create_workbook",
            "excel_append_rows",
            "excel_create_summary_sheet",
            "excel_add_total_row",
            "excel_apply_formula",
            "excel_apply_total_formula",
            "excel_apply_currency_format",
            "excel_auto_size_columns",
            "excel_format_header",
            "excel_freeze_top_row",
            "excel_split_by_category",
            "excel_save_workbook",
        ],
        "color": "red",
        "icon": "database",
    },
}

AUDITOR_PATTERNS = re.compile(
    r"(audit|review|check|verify|duplicate|anomaly|anomalies|inconsistency|discrepancy"
    r"|validate|inspect|find\s+mistake|missing\s+data"
    r"|audit\s+karo|check\s+karo|verify\s+karo)",
    re.IGNORECASE,
)

TAX_PATTERNS = re.compile(
    r"(tax|vat|gst|category|categorize|classification|deductible"
    r"|non-deductible|expense\s+type|tax\s+compliance|tax\s+rule"
    r"|correction\s+rule|correct\s+category|learned\s+rule"
    r"|tax\s+karo|category\s+set\s+karo)",
    re.IGNORECASE,
)

DATA_ENTRY_PATTERNS = re.compile(
    r"(enter\s+data|data\s+entry|write\s+back|push\s+to\s+quickbook"
    r"|push\s+to\s+xero|create\s+bill|live\s+edit|active\s+workbook"
    r"|record\s+transaction|post\s+entry|journal\s+entry"
    r"|data\s+enter\s+karo|bill\s+banao|entry\s+karo)",
    re.IGNORECASE,
)


def _deduplicate_tools(tools: list[str]) -> list[str]:
    seen = set()
    result = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


SPECIALIST_PROFILES["data_entry"]["allowed_tools"] = _deduplicate_tools(
    SPECIALIST_PROFILES["data_entry"]["allowed_tools"]
)


class SwarmManager:
    def __init__(self, db: Session, user: Any):
        self.db = db
        self.user = user

    def classify_and_route(self, command: str) -> str:
        cmd_lower = command.lower().strip()
        audit_match = AUDITOR_PATTERNS.search(cmd_lower)
        tax_match = TAX_PATTERNS.search(cmd_lower)
        data_entry_match = DATA_ENTRY_PATTERNS.search(cmd_lower)

        has_write_keywords = any(
            kw in cmd_lower for kw in ["write back", "write-back", "quickbooks", "xero", "create bill", "push to"]
        )
        has_audit_keywords = any(
            kw in cmd_lower for kw in ["audit", "duplicate", "anomaly", "anomalies", "inconsistency", "discrepancy", "verify", "validate"]
        )
        has_tax_keywords = any(
            kw in cmd_lower for kw in ["tax", "vat", "gst", "categorize", "category", "classification", "deductible"]
        )

        if audit_match or has_audit_keywords:
            return "auditor"
        if data_entry_match or has_write_keywords:
            return "data_entry"
        if tax_match or has_tax_keywords:
            return "tax"
        return "general"

    def execute_swarm_task(
        self,
        command: str,
        agent_profile: str | None = None,
    ) -> dict:
        if agent_profile is None or agent_profile == "general":
            assigned = self.classify_and_route(command)
        else:
            assigned = agent_profile

        profile = SPECIALIST_PROFILES.get(assigned)
        allowed_tools = None
        system_prompt_additions = None
        if profile is not None:
            allowed_tools = profile["allowed_tools"]
            system_prompt_additions = profile["system_prompt_additions"]

        plan = build_task_plan(
            command,
            db=self.db,
            user=self.user,
            agent_profile={"allowed_tools": allowed_tools, "system_prompt_additions": system_prompt_additions}
            if profile
            else None,
        )

        plan["assigned_agent"] = profile["display_name"] if profile else "General"

        return plan


def list_agent_profiles() -> dict[str, dict[str, Any]]:
    result = {}
    for key, profile in SPECIALIST_PROFILES.items():
        result[key] = {
            "display_name": profile["display_name"],
            "color": profile["color"],
            "icon": profile["icon"],
            "tool_count": len(profile["allowed_tools"]),
        }
    return result
