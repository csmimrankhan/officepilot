from __future__ import annotations

import logging
import re

logger = logging.getLogger("officepilot.multilingual_command")

LANGUAGE_PATTERNS = {
    "roman_urdu": re.compile(
        r"\b(karo|hai|sa|ka|ki|ko|se|ma|aur|yeh|woh|aaj|kal|mujhy|batao|nikal|download|upload|invoice|workflow)\b",
        re.IGNORECASE,
    ),
    "urdu": re.compile(r"[\u0600-\u06FF]"),
    "hinglish": re.compile(
        r"\b(karo|hai|sa|ka|ki|ko|se|ma|aur|yeh|woh|aaj|kal|mujhy|batao|nikalo|kijiye|dijiye)\b",
        re.IGNORECASE,
    ),
}

ROMAN_URDU_MAP = {
    "aaj": "today",
    "aj": "today",
    "kal": "yesterday",
    "sa": "from",
    "se": "from",
    "ma": "in",
    "mein": "in",
    "ka": "of",
    "ki": "of",
    "ke": "of",
    "ko": "to",
    "aur": "and",
    "yeh": "this",
    "woh": "that",
    "karo": "do",
    "kijiye": "do",
    "dijiye": "give",
    "hai": "is",
    "hain": "are",
    "mujhy": "me",
    "batao": "tell",
    "nikal": "extract",
    "nikalo": "extract",
    "download": "download",
    "upload": "upload",
    "invoice": "invoice",
    "workflow": "workflow",
    "save": "save",
    "karo": "do",
    "ho": "done",
    "gaya": "done",
    "thi": "was",
    "thay": "were",
    "raha": "ongoing",
    "rahi": "ongoing",
    "rahay": "ongoing",
}

URDU_TO_ENGLISH = {
    "آج": "today",
    "کل": "yesterday",
    "رسید": "invoice",
    "ڈاؤن لوڈ": "download",
    "محفوظ": "save",
    "کرو": "do",
    "ہے": "is",
    "اور": "and",
    "مجھے": "me",
    "بتاؤ": "tell",
    "نکال": "extract",
    "ایکسل": "Excel",
    "ای میل": "email",
    "پی ڈی ایف": "PDF",
}

PHRASE_MAP = [
    (re.compile(r"email\s+sa\b", re.IGNORECASE), "from email"),
    (re.compile(r"email\s+se\b", re.IGNORECASE), "from email"),
    (re.compile(r"\baaj\s+ki\b", re.IGNORECASE), "today's"),
    (re.compile(r"\baj\s+ki\b", re.IGNORECASE), "today's"),
    (re.compile(r"\bkal\s+wala\b", re.IGNORECASE), "yesterday's"),
    (re.compile(r"\bdownload\s+kar[o]?\b", re.IGNORECASE), "download"),
    (re.compile(r"\bsave\s+kar[o]?\b", re.IGNORECASE), "save"),
    (re.compile(r"\bextract\s+kar[o]?\b", re.IGNORECASE), "extract"),
    (re.compile(r"\bbanao\b|\bbana\s+do\b", re.IGNORECASE), "create"),
    (re.compile(r"\bdikhao\b|\bdikha\s+do\b", re.IGNORECASE), "show"),
    (re.compile(r"\bnikal\s+kar[o]?\b", re.IGNORECASE), "extract"),
    (re.compile(r"\bmujhy\s+batao\b", re.IGNORECASE), "tell me"),
    (re.compile(r"\bka\s+total\s+batao\b", re.IGNORECASE), "total"),
    (re.compile(r"\bPDF\s+ka\s+data\b", re.IGNORECASE), "PDF data"),
    (re.compile(r"\bka\s+data\b", re.IGNORECASE), "data of"),
    (re.compile(r"\bsingle\s+excel\s+file\s+ma\b", re.IGNORECASE), "in a single Excel file"),
    (re.compile(r"\bexcel\s+ma\b", re.IGNORECASE), "in Excel"),
    (re.compile(r"\bPDF\s+ka\s+data\b", re.IGNORECASE), "PDF data"),
    (re.compile(r"\bkar\s+ka\b", re.IGNORECASE), "and"),
    (re.compile(r"\bho\s+gaya\b", re.IGNORECASE), "completed"),
    (re.compile(r"\buse\s+karo\b", re.IGNORECASE), "use"),
    (re.compile(r"\bdo\s+the\s+task\s+for\s+today\b", re.IGNORECASE), "run for today"),
]


def detect_language(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    clean = text.strip()
    if LANGUAGE_PATTERNS["urdu"].search(clean):
        return "urdu"
    if LANGUAGE_PATTERNS["roman_urdu"].search(clean):
        return "roman_urdu"
    return "en"


def normalize_command(text: str) -> str:
    return text.strip().lower()


def translate_to_internal_english(text: str) -> str:
    lang = detect_language(text)
    if lang == "en":
        return text.strip().lower()
    clean = text.strip().lower()
    for pattern, replacement in PHRASE_MAP:
        clean = pattern.sub(replacement, clean)
    words = clean.split()
    translated = []
    for w in words:
        if w in ROMAN_URDU_MAP:
            translated.append(ROMAN_URDU_MAP[w])
        else:
            translated.append(w)
    return " ".join(translated)


REPLY_TEMPLATES = {
    "invoice_count": {
        "en": "I found {count} invoices.",
        "roman_urdu": "Maine {count} invoices find ki hain.",
        "urdu": "میں نے {count} رسیدیں تلاش کی ہیں۔",
    },
    "total_amount": {
        "en": "The total amount is {total}.",
        "roman_urdu": "Total amount {total} hai.",
        "urdu": "کل رقم {total} ہے۔",
    },
    "excel_saved": {
        "en": "I saved the data to {filename}.",
        "roman_urdu": "Maine data {filename} mein save kar diya hai.",
        "urdu": "میں نے ڈیٹا {filename} میں محفوظ کر دیا ہے۔",
    },
    "workflow_saved": {
        "en": "Workflow '{name}' has been saved.",
        "roman_urdu": "Workflow '{name}' save ho gaya hai.",
        "urdu": "ورک فلو '{name}' محفوظ ہو گیا ہے۔",
    },
    "workflow_repeated": {
        "en": "Repeating workflow '{name}' for today.",
        "roman_urdu": "Workflow '{name}' aaj ke liye repeat kar raha hoon.",
        "urdu": "ورک فلو '{name}' آج کے لیے دہرا رہا ہوں۔",
    },
    "ask_save_workflow": {
        "en": "Do you want to save this as a workflow?",
        "roman_urdu": "Kya main is workflow ko save kar doon?",
        "urdu": "کیا میں اس ورک فلو کو محفوظ کر دوں؟",
    },
    "clarification_needed": {
        "en": "Could you please clarify? For example: 'read this screen' or 'download today invoices'.",
        "roman_urdu": "Mujhy samajh nahi aaya. Aap kya karna chahtay hain? Jaise: 'aaj ki invoices download karo' ya 'screen read karo'.",
        "urdu": "مجھے سمجھ نہیں آیا۔ آپ کیا کرنا چاہتے ہیں؟",
    },
    "task_blocked": {
        "en": "This task is blocked for safety reasons.",
        "roman_urdu": "Ye task safety ki wajah se block hai.",
        "urdu": "یہ ٹاسک حفاظتی وجوہات کی بنا پر بلاک ہے۔",
    },
    "task_completed": {
        "en": "Task completed successfully.",
        "roman_urdu": "Task successfully complete ho gaya.",
        "urdu": "ٹاسک کامیابی سے مکمل ہو گیا۔",
    },
    "emergency_stop": {
        "en": "Emergency stop activated. All automation has been stopped.",
        "roman_urdu": "Emergency stop activate ho gaya. Sab automation stop kar diya gaya hai.",
        "urdu": "ایمرجنسی اسٹاپ فعال ہو گیا۔ تمام آٹومیشن روک دی گئی ہے۔",
    },
    "no_workflow_found": {
        "en": "I couldn't find a workflow matching your request.",
        "roman_urdu": "Mujhay aap ki request se matching workflow nahi mila.",
        "urdu": "مجھے آپ کی درخواست سے مماثل ورک فلو نہیں ملا۔",
    },
}


def generate_voice_reply(template_key: str, language: str, **kwargs) -> str:
    templates = REPLY_TEMPLATES.get(template_key, {})
    if language not in templates:
        language = "en"
    template = templates.get(language, templates.get("en", ""))
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def build_clarification_question(language: str) -> str:
    return generate_voice_reply("clarification_needed", language)


def get_supported_languages() -> list[dict]:
    return [
        {"code": "en", "name": "English"},
        {"code": "roman_urdu", "name": "Roman Urdu"},
        {"code": "urdu", "name": "Urdu"},
    ]
