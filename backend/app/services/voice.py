"""Phase 22.6 & 22.7 — Voice engine services (STT + Intent Parser)."""

from __future__ import annotations

import logging
import re
import os
import subprocess
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

import httpx
from ..config import Settings

logger = logging.getLogger(__name__)


class VoiceSTTService:
    """Adapter for various Speech-to-Text providers."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def get_status(self) -> Dict[str, Any]:
        provider = self.settings.voice_provider
        configured = False
        message = ""

        if provider == "mock":
            configured = True
            message = "Mock STT is active (test/demo only)."
        elif provider == "openai":
            if not self.settings.voice_allow_cloud_stt:
                message = "OpenAI STT is disabled by policy (VOICE_ALLOW_CLOUD_STT=false)."
            elif not self.settings.openai_api_key:
                message = "OpenAI API key missing."
            else:
                configured = True
                message = "OpenAI STT Ready."
        elif provider == "local":
            if not self.settings.local_whisper_path:
                message = "Local Whisper path not configured."
            elif not os.path.exists(self.settings.local_whisper_path):
                message = f"Local Whisper executable not found at {self.settings.local_whisper_path}."
            else:
                configured = True
                message = "Local Whisper Ready."
        else:
            message = f"Unknown provider: {provider}"

        return {
            "provider": provider,
            "configured": configured,
            "cloud_allowed": self.settings.voice_allow_cloud_stt,
            "max_seconds": self.settings.voice_audio_max_seconds,
            "max_mb": self.settings.voice_audio_max_mb,
            "message": message,
            "demo_mode": self.settings.voice_demo_mode
        }

    async def transcribe(self, audio_content: bytes, filename: str) -> Dict[str, Any]:
        if self.settings.voice_demo_mode:
            logger.info("Voice Demo Mode active: using mock transcription.")
            return self._transcribe_mock()

        provider = self.settings.voice_provider
        
        if provider == "openai":
            return await self._transcribe_openai(audio_content, filename)
        elif provider == "local":
            return await self._transcribe_local(audio_content, filename)
        else:
            return self._transcribe_mock()

    def _transcribe_mock(self) -> Dict[str, Any]:
        return {
            "transcript": "show pending invoices",
            "provider": "mock",
            "duration_seconds": 1.5,
            "confidence": 0.95,
            "status": "completed"
        }

    async def _transcribe_openai(self, audio_content: bytes, filename: str) -> Dict[str, Any]:
        status = self.get_status()
        if not status["configured"]:
            return {
                "transcript": "",
                "provider": "openai",
                "status": "failed",
                "error_message": status["message"]
            }
        
        # Whisper API expects a file. We'll use a temp file and ensure it's deleted.
        # We use a suffix to help Whisper identify the format.
        suffix = os.path.splitext(filename)[1] or ".webm"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_content)
            tmp_path = tmp.name

        try:
            logger.info(f"Sending {len(audio_content)} bytes to OpenAI Whisper API...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(tmp_path, "rb") as audio_file:
                    files = {"file": (filename, audio_file, "audio/webm")}
                    data = {"model": "whisper-1"}
                    headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
                    
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers
                    )
                
                if response.status_code != 200:
                    logger.error(f"OpenAI error: {response.text}")
                    return {
                        "transcript": "",
                        "provider": "openai",
                        "status": "failed",
                        "error_message": f"OpenAI API error: {response.status_code}"
                    }
                
                res_data = response.json()
                return {
                    "transcript": res_data.get("text", ""),
                    "provider": "openai",
                    "status": "completed"
                }
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                "transcript": "",
                "provider": "openai",
                "status": "failed",
                "error_message": str(e)
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _transcribe_local(self, audio_content: bytes, filename: str) -> Dict[str, Any]:
        status = self.get_status()
        if not status["configured"]:
            return {
                "transcript": "",
                "provider": "local",
                "status": "failed",
                "error_message": status["message"]
            }
        
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_content)
            tmp_path = tmp.name

        try:
            # Example command: whisper_cli -m model.bin -f audio.wav --output-txt
            # Actual command depends on the exact CLI tool used.
            # Assuming it writes to stdout or we can read a file.
            # For Phase 22.7, we'll try a generic subprocess call.
            cmd = [
                self.settings.local_whisper_path,
                "-f", tmp_path,
                "--output-txt",
                "--language", "en"
            ]
            logger.info(f"Running local whisper: {' '.join(cmd)}")
            
            # Use subprocess.run with timeout
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.voice_audio_max_seconds + 10
            )
            
            if process.returncode != 0:
                return {
                    "transcript": "",
                    "provider": "local",
                    "status": "failed",
                    "error_message": f"Local Whisper failed: {process.stderr}"
                }
            
            # Some tools output to stdout, others to a file. 
            # If it's whisper.cpp, it usually prints to stdout.
            transcript = process.stdout.strip()
            
            return {
                "transcript": transcript,
                "provider": "local",
                "status": "completed"
            }
        except subprocess.TimeoutExpired:
            return {
                "transcript": "",
                "provider": "local",
                "status": "failed",
                "error_message": "Local Whisper timed out."
            }
        except Exception as e:
            return {
                "transcript": "",
                "provider": "local",
                "status": "failed",
                "error_message": str(e)
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class VoiceIntentParser:
    """Smarter rule-based intent parser for voice commands."""

    RULES = [
        # Domain: invoice
        (r"(show|list|open|see|view).*(pending|review|queue).*(invoice|bill)", "invoice", "list_pending", "low"),
        (r"(open|show|view).*(invoice|bill).*(?:number|#)?\s*([a-z0-9\-]+)", "invoice", "open_detail", "low"),
        (r"(copy|get).*(amount|total|vendor|name).*(this|current).*(invoice|bill)", "invoice", "copy_field", "medium"),
        
        # Domain: excel
        (r"(export|send|save).*(approved).*(excel|spreadsheet|csv)", "excel", "export_approved", "high"),
        (r"(create|make).*(monthly|vendor).*(summary|report|invoice)", "excel", "generate_report", "high"),
        
        # Domain: accounting
        (r"(export|send|sync|post).*(quickbooks|qbo)", "accounting", "sync_quickbooks", "high"),
        (r"(export|send|sync|post).*(xero)", "accounting", "sync_xero", "high"),
        (r"(show|list|see).*(failed|error).*(sync|accounting)", "accounting", "list_failed", "low"),
        
        # Domain: browser
        (r"(open|go to).*(google sheets|sheet|log)", "browser", "open_sheets", "low"),
        (r"(fill|populate).*(this).*(test|form)", "browser", "fill_test_form", "high"),
        
        # Domain: screen
        (r"(read|ocr|analyze).*(current|this).*(window|screen)", "screen", "read_screen", "medium"),
        (r"(open).*(invoice).*(folder|directory)", "screen", "open_folder", "medium"),
        (r"(stop|cancel|halt|emergency).*(everything|automation|all)?", "screen", "emergency_stop", "high"),
    ]

    BLOCKED_PATTERNS = [
        r"(delete|remove|erase).*",
        r"(pay|transfer|banking|credit card).*",
        r"(send|mail|post)\s+(money|payment|cash|email|mail|letter).*",
    ]

    SUGGESTIONS = {
        "invoice": ["show pending invoices", "open invoice INV-1001", "copy amount from this invoice"],
        "excel": ["export approved invoices to Excel", "create monthly summary"],
        "accounting": ["export to QuickBooks", "export to Xero", "show failed syncs"],
        "browser": ["open Google Sheets", "fill this into test form"],
        "screen": ["read current window", "open invoice folder", "emergency stop"],
    }

    def parse(self, text: str) -> Dict[str, Any]:
        clean_text = text.lower().strip()
        
        # Check blocked
        for pattern in self.BLOCKED_PATTERNS:
            if re.match(pattern, clean_text):
                return self._build_result(
                    domain="system",
                    intent="blocked",
                    risk_level="blocked",
                    preview_message=f"I cannot perform this action for safety reasons: '{text}' matches a blocked pattern.",
                    confidence=1.0
                )

        # Match rules
        best_match = None
        for pattern, domain, intent, risk in self.RULES:
            match = re.search(pattern, clean_text)
            if match:
                params = {}
                if intent == "open_detail" and match.groups():
                    params["invoice_number"] = match.group(match.lastindex)
                
                best_match = self._build_result(
                    domain=domain,
                    intent=intent,
                    risk_level=risk,
                    params=params,
                    preview_message=self._get_preview_message(domain, intent, params),
                    confidence=0.9
                )
                break
        
        if best_match:
            return best_match

        # Low confidence -> Clarification
        return self._build_result(
            domain="unknown",
            intent="clarify",
            risk_level="low",
            confidence=0.3,
            clarification_needed=True,
            clarification_question="I'm not sure what you mean. Did you want to see invoices or export something?",
            suggestions=["show pending invoices", "export approved to Excel", "read current screen"]
        )

    def _build_result(self, **kwargs) -> Dict[str, Any]:
        res = {
            "domain": "unknown",
            "intent": "unknown",
            "params": {},
            "risk_level": "low",
            "requires_approval": False,
            "confidence": 0.0,
            "preview_message": "I'm not sure how to help with that.",
            "clarification_needed": False,
            "clarification_question": None,
            "suggestions": []
        }
        res.update(kwargs)
        
        # Risk enforcement
        if res["risk_level"] in ("high", "medium"):
            res["requires_approval"] = True
            
        return res

    def _get_preview_message(self, domain: str, intent: str, params: Dict[str, Any]) -> str:
        if intent == "emergency_stop":
            return "EMERGENCY STOP: Halting all active automations immediately."
        if intent == "list_pending":
            return "Opening the Review Queue to show pending invoices."
        if intent == "open_detail":
            return f"Opening details for invoice {params.get('invoice_number', 'unknown')}."
        if intent == "export_approved":
            return "Exporting all approved invoices to a new Excel file."
        if intent == "sync_quickbooks":
            return "Preparing this invoice for QuickBooks sync."
        if intent == "sync_xero":
            return "Preparing this invoice for Xero sync."
        if intent == "read_screen":
            return "Capturing and reading the content of the active window."
        if intent == "open_folder":
            return "Opening the local folder containing your invoices."
        
        return f"I will perform the {intent} action in the {domain} domain."
