from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..config import get_settings

logger = logging.getLogger("officepilot.accountant_agent")

SENSITIVE_PATTERNS = re.compile(
    r"(password|secret|token|api_key|2fa|otp|cvv|ssn|pin|banking|login|credential)",
    re.IGNORECASE,
)

BLOCKED_PAYMENT_PATTERNS = re.compile(
    r"(pay|payment|bank.transfer|delete.*record|password.*entry|security.*setting"
    r"|tax.*filing.*submit|payroll.*submit|irreversible.*submit|submit.*payment"
    r"|make.*payment|send.*money|wire.*transfer|ach.*transfer)",
    re.IGNORECASE,
)

BLOCKED_EMAIL_PATTERNS = re.compile(
    r"(send.*email|send.*mail|email.*vendor|email.*customer"
    r"|reply.*to.*email|reply.*all|forward.*email|forward.*invoice"
    r"|forward.*message|compose.*email|draft.*and.*send"
    r"|send.*invoice.*email"
    r"|delete.*email|delete.*all.*email|move.*email"
    r"|move.*emails.*to.*trash|archive.*email|archive.*emails"
    r"|mark.*as.*read|mark.*all.*as.*read|mark.*unread"
    r"|star.*email|label.*email|remove.*label|report.*spam"
    r"|unsubscribe"
    r"|modify.*gmail|gmail.*modify|full.*gmail.*access"
    r"|mail\.google\.com|send.*permission|delete.*permission)",
    re.IGNORECASE,
)

DANGEROUS_KEYWORDS = [
    "delete all", "delete every", "delete invoice", "remove all", "remove invoice",
    "destroy", "wipe", "clear all", "truncate", "drop table",
    "bypass security", "bypass login", "crack password", "hack",
    "transfer money", "make payment", "send money", "transfer funds",
    "submit taxes", "file taxes", "submit payroll",
]


def _check_local_llm_reachable(endpoint: str, timeout: int = 5) -> bool:
    """Quick health check for a local LLM endpoint (Ollama / Llama.cpp)."""
    import urllib.request
    import urllib.error
    try:
        url = f"{endpoint.rstrip('/')}/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_agent_status() -> dict:
    settings = get_settings()
    provider = os.environ.get("AGENT_PROVIDER", "mock")
    api_key = os.environ.get("AGENT_API_KEY", "")
    allow_cloud = os.environ.get("AGENT_ALLOW_CLOUD", "false").lower() in ("1", "true", "yes", "on")
    local_endpoint = os.environ.get("LOCAL_LLM_ENDPOINT", settings.local_llm_endpoint)

    status: str
    if provider == "mock":
        status = "mock"
    elif provider == "local":
        if _check_local_llm_reachable(local_endpoint):
            status = "connected"
        else:
            status = "local_unreachable"
    elif allow_cloud and api_key:
        status = "connected"
    elif allow_cloud and not api_key:
        status = "missing_api_key"
    elif not allow_cloud:
        status = "cloud_disabled"
    else:
        status = "unknown"

    return {
        "provider": provider,
        "status": status,
        "allow_cloud": allow_cloud,
        "model": os.environ.get("AGENT_MODEL", ""),
        "api_base_url": os.environ.get("AGENT_API_BASE_URL", ""),
        "local_llm_endpoint": local_endpoint if provider == "local" else "",
        "dry_run_default": os.environ.get("AGENT_DRY_RUN_DEFAULT", "true").lower() in ("1", "true", "yes", "on"),
        "timeout_seconds": int(os.environ.get("AGENT_TIMEOUT_SECONDS", "60")),
        "max_steps": int(os.environ.get("AGENT_MAX_STEPS", "20")),
    }


def redact_context(context: dict) -> dict:
    redacted = {}
    for k, v in context.items():
        if isinstance(v, str) and SENSITIVE_PATTERNS.search(v):
            redacted[k] = "[REDACTED]"
        elif isinstance(v, dict):
            redacted[k] = redact_context(v)
        elif isinstance(v, list):
            redacted[k] = [redact_context(i) if isinstance(i, dict) else i for i in v]
        else:
            redacted[k] = v
    return redacted


def classify_task_risk(command: str, context: dict | None = None) -> dict:
    cmd_lower = command.lower()

    for kw in DANGEROUS_KEYWORDS:
        if kw in cmd_lower:
            return {"risk_level": "blocked", "requires_approval": False, "reason": f"Command contains blocked keyword: '{kw}'"}

    if BLOCKED_EMAIL_PATTERNS.search(cmd_lower):
        return {"risk_level": "blocked", "requires_approval": False, "reason": "email_write_not_supported", "message": "OfficePilot Gmail automation is read-only. Sending, forwarding, deleting, moving, or marking emails is not supported."}

    if BLOCKED_PAYMENT_PATTERNS.search(cmd_lower):
        return {"risk_level": "blocked", "requires_approval": False, "reason": "Payment, deletion, or irreversible action detected. Blocked by safety policy."}

    if any(w in cmd_lower for w in ["write", "update", "create", "edit", "modify", "paste", "type", "click"]):
        return {"risk_level": "medium", "requires_approval": True, "reason": "Write action detected — requires approval."}

    if any(w in cmd_lower for w in ["delete", "remove", "clear"]):
        return {"risk_level": "high", "requires_approval": True, "reason": "Destructive action detected — requires approval."}

    if any(w in cmd_lower for w in ["read", "show", "list", "get", "check", "view", "what"]):
        return {"risk_level": "low", "requires_approval": True, "reason": "Read-only action — low risk."}

    if any(w in cmd_lower for w in ["save", "record", "remember"]):
        return {"risk_level": "low", "requires_approval": True, "reason": "Save/record action — low risk."}

    if any(w in cmd_lower for w in ["repeat", "replay", "rerun"]):
        return {"risk_level": "medium", "requires_approval": True, "reason": "Workflow repeat action — requires approval."}

    return {"risk_level": "low", "requires_approval": True, "reason": "Command accepted — requires review."}


def call_agent_provider(prompt: str, redacted_context: dict | None = None) -> str:
    settings = get_settings()
    provider = os.environ.get("AGENT_PROVIDER", "mock")
    allow_cloud = os.environ.get("AGENT_ALLOW_CLOUD", "false").lower() in ("1", "true", "yes", "on")

    if provider == "mock":
        return _mock_agent_response(prompt, redacted_context)

    if provider == "local":
        try:
            return _call_local_provider(prompt, redacted_context)
        except Exception as e:
            logger.error("Local LLM call failed: %s", e)
            return _fallback_mock_response(prompt, redacted_context, str(e))

    if provider in ("openai_compatible", "deepseek"):
        if not allow_cloud:
            raise ValueError("Cloud agent calls are disabled. Set AGENT_ALLOW_CLOUD=true to enable.")
        api_key = os.environ.get("AGENT_API_KEY", "")
        if not api_key:
            raise ValueError("AGENT_API_KEY is required for cloud provider calls.")
        try:
            return _call_cloud_provider(prompt, redacted_context, provider)
        except Exception as e:
            logger.error("Cloud agent call failed: %s", e)
            return _fallback_mock_response(prompt, redacted_context, str(e))

    raise ValueError(f"Unknown agent provider: {provider}")


def _mock_agent_response(prompt: str, context: dict | None = None) -> str:
    cmd_lower = prompt.lower()
    risk = classify_task_risk(prompt, context)

    if risk["risk_level"] == "blocked":
        return json.dumps({
            "task_title": "Blocked Task",
            "task_summary": risk["reason"],
            "platform_detected": "unknown",
            "risk_level": "blocked",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": risk["reason"],
            "clarification_needed": False,
            "clarification_question": None,
        })

    if any(kw in cmd_lower for kw in ["unclear", "not sure", "what do you mean", "?"]):
        return json.dumps({
            "task_title": "Clarification Needed",
            "task_summary": "The command is unclear.",
            "platform_detected": "unknown",
            "risk_level": "low",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": None,
            "clarification_needed": True,
            "clarification_question": "Could you please clarify what you want to do? For example: 'Read this screen', 'Open yesterday's sales report', 'Create a vendor payment report'.",
        })

    # Detect language (simple heuristic)
    from .language_utils import detect_language_simple
    detected_lang = detect_language_simple(cmd_lower)

    # Multi-language Excel Downloads Summary intent (mock provider handles keyword-based detection)
    # English keywords
    en_matches = (("download" in cmd_lower or "downloads" in cmd_lower) and
        ("excel" in cmd_lower or "spreadsheet" in cmd_lower or "csv" in cmd_lower or "xlsx" in cmd_lower or "sheet" in cmd_lower) and
        ("summary" in cmd_lower or "summarize" in cmd_lower or "report" in cmd_lower or "total" in cmd_lower or "create" in cmd_lower))
    # French keywords
    fr_matches = (("téléchargement" in cmd_lower or "telechargement" in cmd_lower or "téléchargements" in cmd_lower or "telechargements" in cmd_lower) and
        ("fichier excel" in cmd_lower or "excel" in cmd_lower or "tableur" in cmd_lower or "csv" in cmd_lower) and
        ("résumé" in cmd_lower or "resume" in cmd_lower or "sommaire" in cmd_lower or "rapport" in cmd_lower or "créer" in cmd_lower or "creer" in cmd_lower))
    # Spanish keywords
    es_matches = (("descarga" in cmd_lower or "descargas" in cmd_lower or "descargar" in cmd_lower) and
        ("archivo de excel" in cmd_lower or "excel" in cmd_lower or "hoja de cálculo" in cmd_lower or "hoja de calculo" in cmd_lower or "csv" in cmd_lower) and
        ("resumen" in cmd_lower or "reporte" in cmd_lower or "informe" in cmd_lower or "total" in cmd_lower or "crear" in cmd_lower))
    # German keywords
    de_matches = (("download" in cmd_lower or "downloads" in cmd_lower or "herunterladen" in cmd_lower) and
        ("excel" in cmd_lower or "excel-datei" in cmd_lower or "tabelle" in cmd_lower or "csv" in cmd_lower) and
        ("zusammenfassung" in cmd_lower or "bericht" in cmd_lower or "report" in cmd_lower or "summe" in cmd_lower or "erstellen" in cmd_lower))

    if en_matches or fr_matches or es_matches or de_matches:
        from .accountant_autopilot import _build_excel_downloads_summary_plan, _extract_file_query
        query = _extract_file_query(cmd_lower)
        plan = _build_excel_downloads_summary_plan(query, cmd_lower)
        logger.info("Mock provider matched Excel downloads (lang=%s)", detected_lang)
        return json.dumps({
            "task_title": plan["task_title"],
            "task_type": plan.get("task_type", "excel_summary_from_downloads"),
            "task_summary": plan["summary_for_user"],
            "summary_for_user": plan["summary_for_user"],
            "platform_detected": "Excel",
            "risk_level": "medium",
            "requires_approval": True,
            "can_save_workflow": True,
            "can_record_workflow": False,
            "steps": plan["steps"],
            "blocked_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
        })

    # Multi-language Email Attachment Download intent
    # English
    email_en = (("download" in cmd_lower or "search" in cmd_lower) and
        ("email" in cmd_lower or "gmail" in cmd_lower or "mail" in cmd_lower) and
        ("attachment" in cmd_lower or "invoice" in cmd_lower or "receipt" in cmd_lower or "bill" in cmd_lower or "report" in cmd_lower))
    # Roman Urdu / Hinglish
    email_ur = (("download" in cmd_lower or "search" in cmd_lower) and
        ("email" in cmd_lower or "gmail" in cmd_lower or "mail" in cmd_lower) and
        any(w in cmd_lower for w in ["sa", "se", "sy", "mein", "me", "ka", "ki", "wali"]))
    # Generic email download (e.g., "email download karo", "gmail sa download karo", "invoice email download karo")
    email_generic = (("email" in cmd_lower or "gmail" in cmd_lower) and
        ("download" in cmd_lower or "karo" in cmd_lower))
    # French
    email_fr = (("télécharger" in cmd_lower or "telecharger" in cmd_lower or "chercher" in cmd_lower) and
        ("email" in cmd_lower or "courriel" in cmd_lower or "gmail" in cmd_lower) and
        ("pièce jointe" in cmd_lower or "piece jointe" in cmd_lower or "facture" in cmd_lower or "attachment" in cmd_lower))
    # Spanish
    email_es = (("descargar" in cmd_lower or "buscar" in cmd_lower) and
        ("email" in cmd_lower or "correo" in cmd_lower or "gmail" in cmd_lower) and
        ("adjunto" in cmd_lower or "factura" in cmd_lower or "attachment" in cmd_lower))

    if email_en or email_ur or email_generic or email_fr or email_es:
        from .accountant_autopilot import _build_email_download_plan
        email_cmd = cmd_lower.split("user command:")[-1].split("\n\ncontext:")[0].strip()
        query = email_cmd.replace("email", "").replace("gmail", "").replace("download", "").replace("karo", "").replace("sa", "").replace("se", "").replace("sy", "").strip()
        plan = _build_email_download_plan(query, email_cmd)
        logger.info("Mock provider matched email download (lang=%s)", detected_lang)
        return json.dumps({
            "task_title": plan["task_title"],
            "task_type": plan.get("task_type", "email_download"),
            "task_summary": plan["summary_for_user"],
            "summary_for_user": plan["summary_for_user"],
            "platform_detected": "Gmail",
            "risk_level": plan["risk_level"],
            "requires_approval": plan["requires_approval"],
            "can_save_workflow": True,
            "can_record_workflow": False,
            "steps": plan["steps"],
            "blocked_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
        })

    can_record = any(kw in cmd_lower for kw in ["record", "remember", "save"])
    platform = _detect_platform(cmd_lower)
    steps = _build_mock_steps(cmd_lower, platform)

    return json.dumps({
        "task_title": _extract_title(cmd_lower),
        "task_summary": f"Task: {prompt[:200]}",
        "platform_detected": platform,
        "risk_level": risk["risk_level"],
        "requires_approval": risk["requires_approval"],
        "can_record_workflow": can_record,
        "steps": steps,
        "blocked_reason": risk.get("reason") if risk["risk_level"] == "blocked" else None,
        "clarification_needed": False,
        "clarification_question": None,
    })


def _fallback_mock_response(prompt: str, context: dict | None = None, error: str = "") -> str:
    return json.dumps({
        "task_title": "Clarification Needed",
        "task_summary": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
        "platform_detected": "unknown",
        "risk_level": "low",
        "requires_approval": False,
        "can_record_workflow": False,
        "steps": [{
            "step_order": 1,
            "step_type": "needs_clarification",
            "target": "user",
            "instruction": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
            "expected_result": "User provides a clearer command.",
            "requires_approval": False,
            "risk_level": "low",
        }],
        "blocked_reason": None,
        "clarification_needed": True,
        "clarification_question": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
    })


def _detect_platform(cmd_lower: str) -> str:
    platforms = {
        "quickbooks": "QuickBooks",
        "xero": "Xero",
        "zoho": "Zoho Books",
        "odoo": "Odoo",
        "freshbooks": "FreshBooks",
        "wave": "Wave",
        "sage": "Sage",
        "excel": "Excel",
        "spreadsheet": "Excel",
        "browser": "Browser",
        "accounting": "Accounting Platform",
        "invoice": "Invoice System",
        "erp": "ERP",
    }
    for kw, name in platforms.items():
        if kw in cmd_lower:
            return name
    return "Unknown"


def _extract_title(cmd_lower: str) -> str:
    if "read" in cmd_lower and "screen" in cmd_lower:
        return "Read Screen"
    if "stop" in cmd_lower and ("record" in cmd_lower or "recording" in cmd_lower):
        return "Stop Recording"
    if "record" in cmd_lower:
        return "Record Workflow"
    if "repeat" in cmd_lower or "replay" in cmd_lower:
        return "Repeat Workflow"
    if "create" in cmd_lower and "report" in cmd_lower:
        return "Create Report"
    if "update" in cmd_lower and "excel" in cmd_lower:
        return "Update Excel"
    if "copy" in cmd_lower:
        return "Copy Data"
    if "validate" in cmd_lower:
        return "Validate Entry"
    if "show" in cmd_lower and "memory" in cmd_lower:
        return "Show Workflow Memory"
    return "Execute Task"


DEMO_INVOICE_VALUES = [1250.00, 3400.50, 875.25, 2100.00]


def build_hero_demo_plan() -> dict:
    today_str = date.today().isoformat()
    return {
        "task_title": "Daily Invoice Process",
        "task_type": "invoice_demo",
        "summary_for_user": "Download today's invoices from email, extract data, create Excel file, and calculate total.",
        "risk_level": "low",
        "requires_approval": True,
        "can_save_workflow": True,
        "platform_detected": "Excel",
        "steps": [
            {
                "step_order": 1,
                "step_type": "search_email",
                "tool": "search_email",
                "target": "email",
                "instruction": "Search for today's invoice emails.",
                "parameters": {"query": f"invoice {today_str}"},
                "expected_result": f"Invoice emails for {today_str} found.",
                "requires_approval": False, "risk_level": "low",
            },
            {
                "step_order": 2,
                "step_type": "download_attachments",
                "tool": "download_attachments",
                "target": "email",
                "instruction": "Download invoice attachments from found emails.",
                "parameters": {},
                "expected_result": "Invoice PDFs downloaded.",
                "requires_approval": False, "risk_level": "low",
            },
            {
                "step_order": 3,
                "step_type": "extract_invoice_data",
                "tool": "extract_invoice_data",
                "target": "invoices",
                "instruction": "Extract vendor, amount, and date from downloaded invoices.",
                "parameters": {},
                "expected_result": "Invoice data extracted: vendor, amount, date.",
                "requires_approval": False, "risk_level": "low",
            },
            {
                "step_order": 4,
                "step_type": "calculate_excel_total",
                "tool": "calculate_excel_total",
                "target": "Excel",
                "instruction": "Calculate total from extracted invoice amounts.",
                "parameters": {"values": DEMO_INVOICE_VALUES},
                "expected_result": "Total calculated: 7625.75",
                "requires_approval": False, "risk_level": "low",
            },
            {
                "step_order": 5,
                "step_type": "create_excel_workbook",
                "tool": "create_excel_workbook",
                "target": "Excel",
                "instruction": f"Create Excel workbook with invoice data for {today_str}.",
                "parameters": {
                    "filename": f"daily_invoices_{today_str}.xlsx",
                    "sheet_name": "Invoices",
                    "headers": ["Vendor", "Invoice No", "Amount", "Date"],
                },
                "expected_result": f"Excel file daily_invoices_{today_str}.xlsx created.",
                "requires_approval": False, "risk_level": "low",
            },
        ],
        "blocked_reason": None,
    }


def _build_mock_steps(cmd_lower: str, platform: str) -> list[dict]:
    steps = []

    if ("invoice" in cmd_lower or "invoices" in cmd_lower) and (
        "download" in cmd_lower or "email" in cmd_lower
    ) and ("excel" in cmd_lower or "save" in cmd_lower or "total" in cmd_lower):
        return build_hero_demo_plan().get("steps", [])

    if "read" in cmd_lower and "screen" in cmd_lower:
        steps.append({
            "step_order": 1,
            "step_type": "read_screen",
            "target": "screen",
            "instruction": "Capture current screen context.",
            "expected_result": "Screen text and active window identified.",
            "requires_approval": False,
            "risk_level": "low",
        })
        steps.append({
            "step_order": 2,
            "step_type": "validation_checkpoint",
            "target": "user",
            "instruction": "Display captured context to user.",
            "expected_result": "User confirms context is correct.",
            "requires_approval": True,
            "risk_level": "low",
        })
        return steps

    if "record" in cmd_lower and "stop" not in cmd_lower:
        steps.append({
            "step_order": 1,
            "step_type": "read_screen",
            "target": "screen",
            "instruction": "Prepare to record workflow.",
            "expected_result": "Recording session initialized.",
            "requires_approval": False,
            "risk_level": "low",
        })
        steps.append({
            "step_order": 2,
            "step_type": "approval_checkpoint",
            "target": "user",
            "instruction": "Ask user to confirm recording start.",
            "expected_result": "User approves recording.",
            "requires_approval": True,
            "risk_level": "low",
        })
        return steps

    if "stop" in cmd_lower and ("record" in cmd_lower or "recording" in cmd_lower):
        steps.append({
            "step_order": 1,
            "step_type": "approval_checkpoint",
            "target": "user",
            "instruction": "Confirm stopping workflow recording.",
            "expected_result": "User confirms stop.",
            "requires_approval": True,
            "risk_level": "low",
        })
        steps.append({
            "step_order": 2,
            "step_type": "workflow_record_stop",
            "target": "recording",
            "instruction": "Stop recording session and convert to skill draft.",
            "expected_result": "Recording stopped, draft created.",
            "requires_approval": False,
            "risk_level": "low",
        })
        return steps

    if "repeat" in cmd_lower or "replay" in cmd_lower:
        steps.append({
            "step_order": 1,
            "step_type": "read_screen",
            "target": "workflow_memory",
            "instruction": "Find matching workflow in memory.",
            "expected_result": "Workflow found and loaded.",
            "requires_approval": False,
            "risk_level": "low",
        })
        steps.append({
            "step_order": 2,
            "step_type": "approval_checkpoint",
            "target": "user",
            "instruction": "Show workflow preview and ask for approval.",
            "expected_result": "User approves replay.",
            "requires_approval": True,
            "risk_level": "medium",
        })
        steps.append({
            "step_order": 3,
            "step_type": "click",
            "target": platform,
            "instruction": "Execute first step of workflow.",
            "expected_result": "Step executed successfully.",
            "requires_approval": True,
            "risk_level": "medium",
        })
        return steps

    if "create" in cmd_lower:
        steps.append({
            "step_order": 1,
            "step_type": "read_screen",
            "target": platform,
            "instruction": f"Read current {platform} screen.",
            "expected_result": "Screen context captured.",
            "requires_approval": False,
            "risk_level": "low",
        })
        steps.append({
            "step_order": 2,
            "step_type": "click",
            "target": platform,
            "instruction": f"Navigate to report section in {platform}.",
            "expected_result": "Report page loaded.",
            "requires_approval": True,
            "risk_level": "medium",
        })
        steps.append({
            "step_order": 3,
            "step_type": "excel_action",
            "target": "Excel",
            "instruction": "Update Excel sheet with report data.",
            "expected_result": "Excel updated.",
            "requires_approval": True,
            "risk_level": "medium",
        })
        return steps

    steps.append({
        "step_order": 1,
        "step_type": "needs_clarification",
        "target": "user",
        "instruction": "I can help with Excel summaries, Gmail attachment downloads, recording workflows, and local invoice processing. Could you be more specific about what you'd like me to do?",
        "expected_result": "User provides a clearer command.",
        "requires_approval": False,
        "risk_level": "low",
    })
    return steps


def _call_local_provider(prompt: str, context: dict | None = None) -> str:
    """Send prompt to a local LLM (Ollama / Llama.cpp) via OpenAI-compatible API."""
    settings = get_settings()
    api_base = os.environ.get("LOCAL_LLM_ENDPOINT", settings.local_llm_endpoint)
    model = os.environ.get("AGENT_MODEL", "llama3.1")
    timeout = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "120"))

    system_prompt = (
        "You are OfficePilot Accountant Agent. You ONLY plan tasks step by step. "
        "You NEVER execute steps. You NEVER calculate totals. You NEVER click."
        "\n\nSTRICT RULES:"
        "\n1. Return ONLY valid JSON. No markdown, no explanation, no code blocks."
        "\n2. You plan — the user's tools execute. Never say you \"did\" something."
        "\n3. Never include passwords, API keys, tokens, secrets, or credentials in any output field."
        "\n4. Never plan payments, bank transfers, tax filing, password entry, or security setting changes."
        "\n5. If the task involves sensitive data (passwords, OTP, 2FA, CVV, SSN), mark it blocked."
        "\n6. Accounting totals must be calculated by the user's tools. You ONLY describe what to do."
        "\n7. Do not output \"click here\" or \"click on\" — describe the logical step instead."
        "\n8. Always classify risk correctly. Deleting data = high. Writing data = medium. Reading = low."
        "\n9. If unclear, set clarification_needed=true and ask a specific question."
        "\n10. The user's command may be in ANY natural language (English, Urdu, French, Spanish, Hindi, etc.)."
        "\n    Understand it, translate it conceptually to English, and produce the JSON plan"
        "\n    using only the tools available to you. Do NOT mention the translation in your output."
        "\n"
        "Output JSON schema: "
        '{"task_title": str, "task_summary": str, "platform_detected": str, '
        '"risk_level": "low|medium|high|blocked", "requires_approval": bool, '
        '"can_record_workflow": bool, "steps": [{"step_order": int, "step_type": str, '
        '"target": str, "instruction": str, "expected_result": str, '
        '"requires_approval": bool, "risk_level": "low|medium|high|blocked"}], '
        '"blocked_reason": str|null, "clarification_needed": bool, '
        '"clarification_question": str|null}. '
        "Block payment, banking, password, delete, and security tasks. "
        "Ask for clarification if the task is unclear."
    )

    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {prompt}\nContext: {json.dumps(context or {})}"},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "stream": False,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    url = f"{api_base.rstrip('/')}/chat/completions"

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return content
    except urllib.error.HTTPError as e:
        logger.error("Local LLM HTTP %s: %s", e.code, e.read().decode("utf-8", errors="replace"))
        raise
    except urllib.error.URLError as e:
        logger.error("Local LLM URL error: %s", e.reason)
        raise


def _call_cloud_provider(prompt: str, context: dict | None, provider: str) -> str:
    import urllib.request
    import urllib.error

    api_key = os.environ.get("AGENT_API_KEY", "")
    api_base = os.environ.get("AGENT_API_BASE_URL", "")
    model = os.environ.get("AGENT_MODEL", "deepseek-chat")
    timeout = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "60"))

    if not api_base:
        if provider == "deepseek":
            api_base = "https://api.deepseek.com"
        else:
            api_base = "https://api.openai.com/v1"

    system_prompt = (
        "You are OfficePilot Accountant Agent. You ONLY plan tasks step by step. "
        "You NEVER execute steps. You NEVER calculate totals. You NEVER click."
        "\n\nSTRICT RULES:"
        "\n1. Return ONLY valid JSON. No markdown, no explanation, no code blocks."
        "\n2. You plan — the user's tools execute. Never say you \"did\" something."
        "\n3. Never include passwords, API keys, tokens, secrets, or credentials in any output field."
        "\n4. Never plan payments, bank transfers, tax filing, password entry, or security setting changes."
        "\n5. If the task involves sensitive data (passwords, OTP, 2FA, CVV, SSN), mark it blocked."
        "\n6. Accounting totals must be calculated by the user's tools. You ONLY describe what to do."
        "\n7. Do not output \"click here\" or \"click on\" — describe the logical step instead."
        "\n8. Always classify risk correctly. Deleting data = high. Writing data = medium. Reading = low."
        "\n9. If unclear, set clarification_needed=true and ask a specific question."
        "\n10. The user's command may be in ANY natural language (English, Urdu, French, Spanish, Hindi, etc.)."
        "\n    Understand it, translate it conceptually to English, and produce the JSON plan"
        "\n    using only the tools available to you. Do NOT mention the translation in your output."
        "\n"
        "Output JSON schema: "
        '{"task_title": str, "task_summary": str, "platform_detected": str, '
        '"risk_level": "low|medium|high|blocked", "requires_approval": bool, '
        '"can_record_workflow": bool, "steps": [{"step_order": int, "step_type": str, '
        '"target": str, "instruction": str, "expected_result": str, '
        '"requires_approval": bool, "risk_level": "low|medium|high|blocked"}], '
        '"blocked_reason": str|null, "clarification_needed": bool, '
        '"clarification_question": str|null}. '
        "Block payment, banking, password, delete, and security tasks. "
        "Ask for clarification if the task is unclear."
    )

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {prompt}\nContext: {json.dumps(context or {})}"},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    url = f"{api_base.rstrip('/')}/chat/completions"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            return content
    except urllib.error.HTTPError as e:
        logger.error("Cloud provider HTTP %s: %s", e.code, e.read().decode("utf-8", errors="replace"))
        raise
    except urllib.error.URLError as e:
        logger.error("Cloud provider URL error: %s", e.reason)
        raise


def parse_agent_response(response: str) -> dict:
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return {
            "task_title": "Parse Error",
            "task_summary": "Failed to parse agent response.",
            "platform_detected": "unknown",
            "risk_level": "low",
            "requires_approval": True,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": "Invalid JSON from agent provider.",
            "clarification_needed": False,
            "clarification_question": None,
        }

    required = ["task_title", "task_summary", "platform_detected", "risk_level", "requires_approval", "steps"]
    for field in required:
        if field not in parsed:
            return {
                "task_title": "Validation Error",
                "task_summary": f"Missing required field: {field}",
                "platform_detected": "unknown",
                "risk_level": "low",
                "requires_approval": True,
                "can_record_workflow": False,
                "steps": [],
                "blocked_reason": f"Agent response missing '{field}'.",
                "clarification_needed": False,
                "clarification_question": None,
            }

    if parsed.get("risk_level") == "blocked" and not parsed.get("blocked_reason"):
        parsed["blocked_reason"] = "Task blocked by safety policy."

    if parsed.get("clarification_needed") and not parsed.get("clarification_question"):
        parsed["clarification_question"] = "Could you please clarify your request?"

    return parsed


def validate_plan(plan: dict, context: dict | None = None) -> dict:
    errors = []

    if plan.get("risk_level") == "blocked":
        return {"valid": True, "blocked": True, "reason": plan.get("blocked_reason", "Blocked by safety policy."), "errors": []}

    if plan.get("clarification_needed"):
        return {"valid": True, "clarification_needed": True, "question": plan.get("clarification_question"), "errors": []}

    steps = plan.get("steps", [])
    if not steps:
        errors.append("Plan has no steps.")

    for step in steps:
        if not step.get("step_type"):
            errors.append(f"Step {step.get('step_order', '?')} has no step_type.")
        if not step.get("instruction"):
            errors.append(f"Step {step.get('step_order', '?')} has no instruction.")

    blocked_types = {"payment", "bank_transfer", "delete", "password_entry"}
    for step in steps:
        if step.get("step_type") in blocked_types:
            errors.append(f"Step {step.get('step_order', '?')} uses blocked action type: {step.get('step_type')}")

    return {"valid": len(errors) == 0, "blocked": False, "clarification_needed": False, "errors": errors}


def convert_plan_to_workflow_steps(plan: dict) -> list[dict]:
    steps = plan.get("steps", [])
    return [
        {
            "step_order": s.get("step_order", i + 1),
            "step_type": s.get("step_type", "unknown"),
            "target": s.get("target", ""),
            "instruction": s.get("instruction", ""),
            "expected_result": s.get("expected_result", ""),
            "requires_approval": s.get("requires_approval", True),
            "risk_level": s.get("risk_level", "low"),
        }
        for i, s in enumerate(steps)
    ]


def build_task_plan(command: str, context: dict | None = None) -> dict:
    risk = classify_task_risk(command, context)

    if risk["risk_level"] == "blocked":
        return {
            "task_title": "Blocked Task",
            "task_summary": risk["reason"],
            "platform_detected": "unknown",
            "risk_level": "blocked",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": risk["reason"],
            "clarification_needed": False,
            "clarification_question": None,
        }

    redacted_ctx = redact_context(context or {})
    prompt = f"User command: {command}\n\nContext: {json.dumps(redacted_ctx)}"

    try:
        raw_response = call_agent_provider(prompt, redacted_ctx)
    except ValueError as e:
        return {
            "task_title": "Provider Error",
            "task_summary": str(e),
            "platform_detected": "unknown",
            "risk_level": "low",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": str(e),
            "clarification_needed": False,
            "clarification_question": None,
        }

    plan = parse_agent_response(raw_response)
    validation = validate_plan(plan, context)

    if validation.get("blocked"):
        return {
            "task_title": "Blocked Task",
            "task_summary": validation["reason"],
            "platform_detected": "unknown",
            "risk_level": "blocked",
            "requires_approval": False,
            "can_record_workflow": False,
            "steps": [],
            "blocked_reason": validation["reason"],
            "clarification_needed": False,
            "clarification_question": None,
        }

    if validation.get("clarification_needed"):
        plan["clarification_needed"] = True
        plan["clarification_question"] = validation.get("question")

    return plan
