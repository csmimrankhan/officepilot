from __future__ import annotations

import logging
import os

from .multilingual_command import detect_language, generate_voice_reply

logger = logging.getLogger("officepilot.voice_reply")

TEMPLATE_FUNCTIONS = {
    "plan_preview": lambda language, summary, risk: (
        generate_voice_reply("plan_preview", language)
        if False
        else _inline_reply(
            language,
            f"Task plan ready: {summary}. Risk level: {risk}.",
            f"Task plan ready hai: {summary}. Risk level: {risk} hai.",
            f"ٹاسک پلان تیار ہے: {summary}۔ خطرے کی سطح: {risk}۔",
        )
    ),
    "invoice_count": lambda language, count: _inline_reply(
        language,
        f"I found {count} invoices.",
        f"Maine {count} invoices find ki hain.",
        f"میں نے {count} رسیدیں تلاش کی ہیں۔",
    ),
    "total_amount": lambda language, total: _inline_reply(
        language,
        f"The total amount is {total}.",
        f"Total amount {total} hai.",
        f"کل رقم {total} ہے۔",
    ),
    "excel_saved": lambda language, filename: _inline_reply(
        language,
        f"I saved the data to {filename}.",
        f"Maine data {filename} mein save kar diya hai.",
        f"میں نے ڈیٹا {filename} میں محفوظ کر دیا ہے۔",
    ),
    "workflow_saved": lambda language, name: _inline_reply(
        language,
        f"Workflow '{name}' has been saved.",
        f"Workflow '{name}' save ho gaya hai.",
        f"ورک فلو '{name}' محفوظ ہو گیا ہے۔",
    ),
    "workflow_repeated": lambda language, name: _inline_reply(
        language,
        f"Repeating workflow '{name}' for today.",
        f"Workflow '{name}' aaj ke liye repeat kar raha hoon.",
        f"ورک فلو '{name}' آج کے لیے دہرا رہا ہوں۔",
    ),
    "ask_save": lambda language: _inline_reply(
        language,
        "Do you want to save this as a workflow?",
        "Kya main is workflow ko save kar doon?",
        "کیا میں اس ورک فلو کو محفوظ کر دوں؟",
    ),
    "clarify": lambda language: _inline_reply(
        language,
        "Could you please clarify?",
        "Mujhy samajh nahi aaya. Aap kya karna chahtay hain?",
        "مجھے سمجھ نہیں آیا۔ آپ کیا کرنا چاہتے ہیں؟",
    ),
    "blocked": lambda language: _inline_reply(
        language,
        "This task is blocked for safety reasons.",
        "Ye task safety ki wajah se block hai.",
        "یہ ٹاسک حفاظتی وجوہات کی بنا پر بلاک ہے۔",
    ),
    "done": lambda language: _inline_reply(
        language,
        "Task completed successfully.",
        "Task successfully complete ho gaya.",
        "ٹاسک کامیابی سے مکمل ہو گیا۔",
    ),
    "stopped": lambda language: _inline_reply(
        language,
        "Emergency stop activated. All automation has been stopped.",
        "Emergency stop activate ho gaya. Sab automation stop kar diya gaya hai.",
        "ایمرجنسی اسٹاپ فعال ہو گیا۔ تمام آٹومیشن روک دی گئی ہے۔",
    ),
    "no_workflow": lambda language: _inline_reply(
        language,
        "I couldn't find a matching workflow.",
        "Mujhay matching workflow nahi mila.",
        "مجھے مماثل ورک فلو نہیں ملا۔",
    ),
}


def _inline_reply(language: str, en: str, roman_urdu: str, urdu: str) -> str:
    if language == "urdu":
        return urdu
    if language == "roman_urdu":
        return roman_urdu
    return en


def build_user_reply(event: str, language: str = "en", **kwargs) -> str:
    fn = TEMPLATE_FUNCTIONS.get(event)
    if fn:
        return fn(language, **kwargs)
    return generate_voice_reply(event, language, **kwargs)


def speak_text_if_enabled(text: str, language: str = "en") -> dict:
    tts_enabled = os.environ.get("TTS_ENABLED", "false").lower() in ("1", "true", "yes", "on")
    return {
        "text": text,
        "language": language,
        "tts_enabled": tts_enabled,
        "ssml": None,
    }


def return_text_response(text: str, language: str = "en") -> dict:
    return {
        "reply": text,
        "language": language,
        "type": "text",
    }
