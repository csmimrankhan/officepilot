"""Runtime configuration loaded from environment variables (.env supported)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = _project_root() / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@lru_cache(maxsize=1)
def _settings_singleton() -> "Settings":
    _load_dotenv()
    storage_root = Path(
        os.environ.get(
            "OFFICEPILOT_STORAGE_ROOT",
            str(_project_root() / "storage"),
        )
    )
    return Settings(
        database_url=os.environ.get(
            "OFFICEPILOT_DB_URL", "sqlite:///./officepilot.db"
        ),
        storage_root=storage_root,
        ocr_enabled=os.environ.get("OFFICEPILOT_OCR_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        tesseract_cmd=os.environ.get("OFFICEPILOT_TESSERACT_CMD", ""),
        # Phase 38.5 — Multilingual OCR. Comma-separated Tesseract language
        # codes, e.g. "eng+fra+spa+deu+ara+hin+urd". PaddleOCR uses ISO 639-1
        # two-letter codes. Default is English-only.
        ocr_languages=os.environ.get("OFFICEPILOT_OCR_LANGUAGES", ""),
        max_upload_mb=int(os.environ.get("OFFICEPILOT_MAX_UPLOAD_MB", "20")),
        confidence_threshold=float(
            os.environ.get("OFFICEPILOT_CONFIDENCE_THRESHOLD", "0.6")
        ),
        cors_origins=os.environ.get(
            "OFFICEPILOT_CORS_ORIGINS",
            # Vite dev server (browser mode) + the Tauri 2 webview
            # origins. Tauri 2 uses ``http://tauri.localhost`` on
            # Windows when ``withGlobalTauri = true``; we also
            # include the legacy ``tauri://localhost`` and the
            # ``https://tauri.localhost`` forms some platforms
            # report. Override with OFFICEPILOT_CORS_ORIGINS for
            # production deployments that are not the bundled
            # Tauri shell.
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "tauri://localhost,"
            "http://tauri.localhost,"
            "https://tauri.localhost"
        ),
        app_env=os.environ.get("OFFICEPILOT_ENV", "development"),
        gmail_client_id=os.environ.get("OFFICEPILOT_GMAIL_CLIENT_ID", ""),
        gmail_client_secret=os.environ.get("OFFICEPILOT_GMAIL_CLIENT_SECRET", ""),
        gmail_redirect_uri=os.environ.get(
            "OFFICEPILOT_GMAIL_REDIRECT_URI",
            "http://127.0.0.1:8000/api/integrations/gmail/callback",
        ),
        # 44-char url-safe base64 Fernet key. Generated lazily for dev if blank.
        gmail_token_key=os.environ.get("OFFICEPILOT_GMAIL_TOKEN_KEY", ""),
        # Where the OAuth state -> credentials are kept between connect/callback.
        # Defaults to a sibling file of the database, in the storage root.
        gmail_state_dir=Path(
            os.environ.get(
                "OFFICEPILOT_GMAIL_STATE_DIR",
                str(storage_root / "gmail"),
            )
        ),
        # Tunable knobs
        gmail_min_score=float(os.environ.get("OFFICEPILOT_GMAIL_MIN_SCORE", "0.4")),
        gmail_max_results=int(os.environ.get("OFFICEPILOT_GMAIL_MAX_RESULTS", "50")),
        gmail_search_days=int(os.environ.get("OFFICEPILOT_GMAIL_SEARCH_DAYS", "30")),
        # If true, sync will use the real Gmail API. If false, every call to
        # the client is intercepted by a fake (used in tests and for offline dev).
        gmail_allow_real=os.environ.get("OFFICEPILOT_GMAIL_ALLOW_REAL", "true").lower()
        in ("1", "true", "yes", "on"),
        # Phase 5: parser engine selection. Default is "existing" so
        # the production behavior is unchanged. Options:
        #   existing - Phase 1-3 pipeline (PyMuPDF/pdfplumber/OCR + regex)
        #   docling  - Docling layout-aware parser (graceful fallback)
        #   ocr      - OCR-first (PaddleOCR or Tesseract) + regex
        #   hybrid   - run all three and reconcile
        parser_engine=os.environ.get("OFFICEPILOT_PARSER_ENGINE", "existing").lower(),
        # Phase 7: local desktop shell. ``data_dir`` is the parent of
        # every persisted artefact (invoices, exports, audit, cache,
        # workflow recordings). Defaults to a ``data/`` folder next
        # to ``storage/`` so existing data keeps working.
        data_dir=Path(
            os.environ.get(
                "OFFICEPILOT_DATA_DIR",
                str(_project_root() / "data"),
            )
        ),
        # The host/port the local FastAPI agent listens on. The
        # Tauri shell uses these to point its WebView at the API.
        agent_host=os.environ.get("OFFICEPILOT_AGENT_HOST", "127.0.0.1"),
        agent_port=int(os.environ.get("OFFICEPILOT_AGENT_PORT", "8000")),
        # Phase 12: browser automation. Off by default; the
        # operator must explicitly enable it from the Settings page.
        browser_enabled=os.environ.get("BROWSER_AUTOMATION_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        browser_headless=os.environ.get("BROWSER_HEADLESS", "false").lower()
        in ("1", "true", "yes", "on"),
        browser_screenshots_enabled=os.environ.get(
            "BROWSER_SCREENSHOTS_ENABLED", "true"
        ).lower() in ("1", "true", "yes", "on"),
        # Comma-separated allowlist. Empty -> use the in-code
        # default allowlist. ``*`` is treated as "deny all"
        # because the spec is default-deny.
        browser_allowed_domains=os.environ.get("BROWSER_ALLOWED_DOMAINS", ""),
        browser_blocked_domains=os.environ.get("BROWSER_BLOCKED_DOMAINS", ""),
        browser_require_approval_for_write=os.environ.get(
            "BROWSER_REQUIRE_APPROVAL_FOR_WRITE", "true"
        ).lower() in ("1", "true", "yes", "on"),
        browser_require_approval_for_submit=os.environ.get(
            "BROWSER_REQUIRE_APPROVAL_FOR_SUBMIT", "true"
        ).lower() in ("1", "true", "yes", "on"),
        # Maximum number of browser action runs to keep on disk.
        # Older runs are pruned by the lifespan handler.
        browser_max_runs=int(os.environ.get("BROWSER_MAX_RUNS", "200")),
        # Where Playwright stores downloaded Chromium binaries
        # (defaults to the standard cache dir).
        browser_playwright_dir=os.environ.get(
            "BROWSER_PLAYWRIGHT_BROWSERS_PATH", ""
        ),
        # Phase 32: Browser automation mode (mock | playwright).
        browser_automation_mode=os.environ.get(
            "BROWSER_AUTOMATION_MODE", "mock"
        ).lower(),
        # Allow live browser execution (requires mode=playwright).
        browser_automation_allow_live=os.environ.get(
            "BROWSER_AUTOMATION_ALLOW_LIVE", "false"
        ).lower() in ("1", "true", "yes", "on"),
        # Download watching directory for guided download mode.
        browser_download_watch_dir=os.environ.get(
            "BROWSER_DOWNLOAD_WATCH_DIR", ""
        ),
        # Phase 13: QuickBooks / Xero accounting sync.
        accounting_sync_enabled=os.environ.get(
            "ACCOUNTING_SYNC_ENABLED", "false"
        ).lower() in ("1", "true", "yes", "on"),
        accounting_require_approval=os.environ.get(
            "ACCOUNTING_REQUIRE_APPROVAL", "true"
        ).lower() in ("1", "true", "yes", "on"),
        accounting_draft_only=os.environ.get(
            "ACCOUNTING_DRAFT_ONLY", "true"
        ).lower() in ("1", "true", "yes", "on"),
        accounting_block_duplicates=os.environ.get(
            "ACCOUNTING_BLOCK_DUPLICATES", "true"
        ).lower() in ("1", "true", "yes", "on"),
        quickbooks_client_id=os.environ.get("QUICKBOOKS_CLIENT_ID", ""),
        quickbooks_client_secret=os.environ.get("QUICKBOOKS_CLIENT_SECRET", ""),
        quickbooks_redirect_uri=os.environ.get(
            "QUICKBOOKS_REDIRECT_URI",
            "http://127.0.0.1:8000/api/accounting/quickbooks/callback",
        ),
        quickbooks_env=os.environ.get("QUICKBOOKS_ENV", "mock").lower(),
        quickbooks_scopes=os.environ.get("QUICKBOOKS_SCOPES", "mock").lower(),
        xero_client_id=os.environ.get("XERO_CLIENT_ID", ""),
        xero_client_secret=os.environ.get("XERO_CLIENT_SECRET", ""),
        xero_redirect_uri=os.environ.get(
            "XERO_REDIRECT_URI",
            "http://127.0.0.1:8000/api/accounting/xero/callback",
        ),
        xero_env=os.environ.get("XERO_ENV", "mock").lower(),
        xero_scopes=os.environ.get("XERO_SCOPES", "mock").lower(),
        # Phase 14 — workflow recording.
        workflow_recording_enabled=os.environ.get(
            "WORKFLOW_RECORDING_ENABLED", "false"
        ).lower() in ("1", "true", "yes", "on"),
        recording_screenshots_enabled=os.environ.get(
            "WORKFLOW_RECORDING_SCREENSHOTS_ENABLED", "false"
        ).lower() in ("1", "true", "yes", "on"),
        recording_redact_sensitive=os.environ.get(
            "WORKFLOW_RECORDING_REDACT_SENSITIVE", "true"
        ).lower() in ("1", "true", "yes", "on"),
        replay_default_mode=os.environ.get(
            "WORKFLOW_REPLAY_DEFAULT_MODE", "dry_run"
        ),
        replay_require_approval=os.environ.get(
            "WORKFLOW_REPLAY_REQUIRE_APPROVAL", "true"
        ).lower() in ("1", "true", "yes", "on"),
        recording_max_events=int(os.environ.get("WORKFLOW_RECORDING_MAX_EVENTS", "1000")),
        # Phase 15: screen control.
        screen_control_enabled=os.environ.get("SCREEN_CONTROL_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_permission_level=int(os.environ.get("SCREEN_PERMISSION_LEVEL", "0")),
        screen_screenshots_enabled=os.environ.get("SCREEN_SCREENSHOTS_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_ocr_enabled=os.environ.get("SCREEN_OCR_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_click_enabled=os.environ.get("SCREEN_CLICK_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_type_enabled=os.environ.get("SCREEN_TYPE_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_clipboard_enabled=os.environ.get("SCREEN_CLIPBOARD_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        screen_require_approval_for_click=os.environ.get(
            "SCREEN_REQUIRE_APPROVAL_FOR_CLICK", "true"
        ).lower() in ("1", "true", "yes", "on"),
        screen_require_approval_for_type=os.environ.get(
            "SCREEN_REQUIRE_APPROVAL_FOR_TYPE", "true"
        ).lower() in ("1", "true", "yes", "on"),
        screen_require_approval_for_submit=os.environ.get(
            "SCREEN_REQUIRE_APPROVAL_FOR_SUBMIT", "true"
        ).lower() in ("1", "true", "yes", "on"),
        screen_require_approval_for_clipboard=os.environ.get(
            "SCREEN_REQUIRE_APPROVAL_FOR_CLIPBOARD", "true"
        ).lower() in ("1", "true", "yes", "on"),
        screen_emergency_stop_enabled=os.environ.get("SCREEN_EMERGENCY_STOP_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        screen_allowed_apps=os.environ.get("SCREEN_ALLOWED_APPS", ""),
        screen_blocked_apps=os.environ.get("SCREEN_BLOCKED_APPS", ""),
        screen_allowed_folders=os.environ.get("SCREEN_ALLOWED_FOLDERS", ""),
        screen_screenshot_storage=os.environ.get("SCREEN_SCREENSHOT_STORAGE", ""),
        # Phase 16A: UI automation execution layer.
        screen_ocr_engine=os.environ.get("SCREEN_OCR_ENGINE", "tesseract"),
        screen_tesseract_cmd=os.environ.get("TESSERACT_CMD", ""),
        screen_ui_automation_enabled=os.environ.get("SCREEN_UI_AUTOMATION_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        screen_pyautogui_fallback=os.environ.get("SCREEN_PYAUTOGUI_FALLBACK", "false").lower()
        in ("1", "true", "yes", "on"),
        screen_block_unknown_apps=os.environ.get("SCREEN_BLOCK_UNKNOWN_APPS", "true").lower()
        in ("1", "true", "yes", "on"),
        screen_execution_step_delay_ms=int(os.environ.get("SCREEN_EXECUTION_STEP_DELAY_MS", "300")),
        # Phase 17 — Authentication.
        jwt_secret=os.environ.get("JWT_SECRET", ""),
        allow_open_registration=os.environ.get("ALLOW_OPEN_REGISTRATION", "false").lower()
        in ("1", "true", "yes", "on"),
        allow_first_owner_bootstrap=os.environ.get("ALLOW_FIRST_OWNER_BOOTSTRAP", "true").lower()
        in ("1", "true", "yes", "on"),
        # Phase 18 — Demo mode.
        demo_mode=os.environ.get("DEMO_MODE", "false").lower()
        in ("1", "true", "yes", "on"),
        demo_seed_on_first_run=os.environ.get("DEMO_SEED_ON_FIRST_RUN", "false").lower()
        in ("1", "true", "yes", "on"),
        # Phase 19 — Pilot readiness.
        usage_tracking_enabled=os.environ.get("USAGE_TRACKING_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        external_analytics_enabled=os.environ.get("EXTERNAL_ANALYTICS_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        # Phase 20 — Public landing page & pilot waitlist.
        public_analytics_enabled=os.environ.get("PUBLIC_ANALYTICS_ENABLED", "true").lower()
        in ("1", "true", "yes", "on"),
        # Phase 21 — Performance, cleanup, retention.
        log_retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "90")),
        demo_data_retention_days=int(os.environ.get("DEMO_DATA_RETENTION_DAYS", "30")),
        max_audit_exports=int(os.environ.get("MAX_AUDIT_EXPORTS", "50")),
        max_bug_report_packages=int(os.environ.get("MAX_BUG_REPORT_PACKAGES", "50")),
        # Phase 22.6 — Voice engine & STT.
        voice_provider=os.environ.get("VOICE_PROVIDER", "mock").lower(),
        voice_stt_model=os.environ.get("VOICE_STT_MODEL", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        local_whisper_path=os.environ.get("LOCAL_WHISPER_PATH", ""),
        voice_allow_cloud_stt=os.environ.get("VOICE_ALLOW_CLOUD_STT", "false").lower()
        in ("1", "true", "yes", "on"),
        voice_audio_max_seconds=int(os.environ.get("VOICE_AUDIO_MAX_SECONDS", "30")),
        voice_audio_max_mb=int(os.environ.get("VOICE_AUDIO_MAX_MB", "10")),
        voice_demo_mode=os.environ.get("VOICE_DEMO_MODE", "false").lower()
        in ("1", "true", "yes", "on"),
        # Phase 23 — Accountant Agent / LLM Provider.
        agent_provider=os.environ.get("AGENT_PROVIDER", "mock").lower(),
        agent_api_base_url=os.environ.get("AGENT_API_BASE_URL", ""),
        agent_api_key=os.environ.get("AGENT_API_KEY", ""),
        agent_model=os.environ.get("AGENT_MODEL", ""),
        agent_allow_cloud=os.environ.get("AGENT_ALLOW_CLOUD", "false").lower()
        in ("1", "true", "yes", "on"),
        agent_timeout_seconds=int(os.environ.get("AGENT_TIMEOUT_SECONDS", "60")),
        agent_max_steps=int(os.environ.get("AGENT_MAX_STEPS", "20")),
        agent_dry_run_default=os.environ.get("AGENT_DRY_RUN_DEFAULT", "true").lower()
        in ("1", "true", "yes", "on"),
        # Phase 38.5 — Local LLM (Ollama / Llama.cpp).
        local_llm_endpoint=os.environ.get("LOCAL_LLM_ENDPOINT", "http://localhost:11434/v1"),
        # Phase 23 — Voice Approval.
        voice_approval_enabled=os.environ.get("VOICE_APPROVAL_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
        voice_approval_high_risk_allowed=os.environ.get("VOICE_APPROVAL_HIGH_RISK_ALLOWED", "false").lower()
        in ("1", "true", "yes", "on"),
        # Phase 23B — Accountant AutoPilot.
        tts_provider=os.environ.get("TTS_PROVIDER", "none").lower(),
        tts_enabled=os.environ.get("TTS_ENABLED", "false").lower() in ("1", "true", "yes", "on"),
        tts_language=os.environ.get("TTS_LANGUAGE", "en").lower(),
        stt_provider=os.environ.get("STT_PROVIDER", "browser").lower(),
        stt_language=os.environ.get("STT_LANGUAGE", "en").lower(),
        multilingual_enabled=os.environ.get("MULTILINGUAL_ENABLED", "false").lower() in ("1", "true", "yes", "on"),
        account_platform_mode=os.environ.get("ACCOUNT_PLATFORM_MODE", "universal").lower(),
        daily_invoice_max=int(os.environ.get("DAILY_INVOICE_MAX", "50")),
        excel_snapshots_enabled=os.environ.get("EXCEL_SNAPSHOTS_ENABLED", "true").lower() in ("1", "true", "yes", "on"),
        workflow_auto_save=os.environ.get("WORKFLOW_AUTO_SAVE", "false").lower() in ("1", "true", "yes", "on"),
        # Phase 17+ — SMTP / Email.
        smtp_host=os.environ.get("SMTP_HOST", ""),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_username=os.environ.get("SMTP_USERNAME", ""),
        smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        smtp_from_email=os.environ.get("SMTP_FROM_EMAIL", "noreply@officepilot.ai"),
        smtp_from_name=os.environ.get("SMTP_FROM_NAME", "OfficePilot AI"),
        smtp_tls=os.environ.get("SMTP_TLS", "true").lower() in ("1", "true", "yes", "on"),
        smtp_ssl=os.environ.get("SMTP_SSL", "false").lower() in ("1", "true", "yes", "on"),
        smtp_timeout=int(os.environ.get("SMTP_TIMEOUT", "30")),
        frontend_url=os.environ.get("FRONTEND_URL", "http://localhost:5173"),
        # Phase 17+ — OAuth login.
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        google_redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback"),
        microsoft_client_id=os.environ.get("MICROSOFT_CLIENT_ID", ""),
        microsoft_client_secret=os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
        microsoft_tenant_id=os.environ.get("MICROSOFT_TENANT_ID", "common"),
        # Phase 23B — Feature flags.
        pilot_tools_enabled=os.environ.get("PILOT_TOOLS_ENABLED", "false").lower() in ("1", "true", "yes", "on"),
        advanced_tools_enabled=os.environ.get("ADVANCED_TOOLS_ENABLED", "true").lower() in ("1", "true", "yes", "on"),
        dev_tools_enabled=os.environ.get("DEV_TOOLS_ENABLED", "false").lower() in ("1", "true", "yes", "on"),
        # Phase 35 — Billing bypass for local dev.
        allow_billing_bypass=os.environ.get("ALLOW_BILLING_BYPASS", "true").lower()
        in ("1", "true", "yes", "on"),
        # Phase 35 — App current version.
        app_version=os.environ.get("OFFICEPILOT_APP_VERSION", "0.36.1"),
        # Phase 27 — Windows Voice Layer.
        voice_layer_enabled=os.environ.get("VOICE_LAYER_ENABLED", "true").lower() in ("1", "true", "yes", "on"),
        voice_mode_default=os.environ.get("VOICE_MODE_DEFAULT", "dictation"),
        voice_local_engine=os.environ.get("VOICE_LOCAL_ENGINE", "whisper_cpp"),
        voice_whisper_cli_path=os.environ.get("VOICE_WHISPER_CLI_PATH", ""),
        voice_whisper_model_path=os.environ.get("VOICE_WHISPER_MODEL_PATH", ""),
        voice_language=os.environ.get("VOICE_LANGUAGE", "auto"),
        voice_push_to_talk=os.environ.get("VOICE_PUSH_TO_TALK", "true").lower() in ("1", "true", "yes", "on"),
        voice_shortcut_dictation=os.environ.get("VOICE_SHORTCUT_DICTATION", "Ctrl+Alt+Space"),
        voice_shortcut_ai=os.environ.get("VOICE_SHORTCUT_AI", "Ctrl+Alt+A"),
        voice_shortcut_agent=os.environ.get("VOICE_SHORTCUT_AGENT", "Ctrl+Alt+O"),
        voice_confirm_before_paste=os.environ.get("VOICE_CONFIRM_BEFORE_PASTE", "true").lower() in ("1", "true", "yes", "on"),
        voice_save_history=os.environ.get("VOICE_SAVE_HISTORY", "true").lower() in ("1", "true", "yes", "on"),
        voice_history_limit=int(os.environ.get("VOICE_HISTORY_LIMIT", "100")),
        voice_beep_enabled=os.environ.get("VOICE_BEEP_ENABLED", "true").lower() in ("1", "true", "yes", "on"),
        voice_overlay_enabled=os.environ.get("VOICE_OVERLAY_ENABLED", "true").lower() in ("1", "true", "yes", "on"),
        ai_mode_provider=os.environ.get("AI_MODE_PROVIDER", "openai_compatible"),
        ai_mode_model=os.environ.get("AI_MODE_MODEL", ""),
        ai_mode_api_key=os.environ.get("AI_MODE_API_KEY", ""),
        ai_mode_allow_cloud=os.environ.get("AI_MODE_ALLOW_CLOUD", "false").lower() in ("1", "true", "yes", "on"),
    )


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_root: Path
    ocr_enabled: bool
    tesseract_cmd: str
    ocr_languages: str
    max_upload_mb: int
    confidence_threshold: float
    cors_origins: str
    app_env: str
    gmail_client_id: str
    gmail_client_secret: str
    gmail_redirect_uri: str
    gmail_token_key: str
    gmail_state_dir: Path
    gmail_min_score: float
    gmail_max_results: int
    gmail_search_days: int
    gmail_allow_real: bool
    parser_engine: str
    data_dir: Path
    agent_host: str
    agent_port: int
    browser_enabled: bool
    browser_headless: bool
    browser_screenshots_enabled: bool
    browser_allowed_domains: str
    browser_blocked_domains: str
    browser_require_approval_for_write: bool
    browser_require_approval_for_submit: bool
    browser_max_runs: int
    browser_playwright_dir: str
    browser_automation_mode: str
    browser_automation_allow_live: bool
    browser_download_watch_dir: str
    accounting_sync_enabled: bool
    accounting_require_approval: bool
    accounting_draft_only: bool
    accounting_block_duplicates: bool
    quickbooks_client_id: str
    quickbooks_client_secret: str
    quickbooks_redirect_uri: str
    quickbooks_env: str
    quickbooks_scopes: str
    xero_client_id: str
    xero_client_secret: str
    xero_redirect_uri: str
    xero_env: str
    xero_scopes: str
    # Phase 14 — workflow recording.
    workflow_recording_enabled: bool
    recording_screenshots_enabled: bool
    recording_redact_sensitive: bool
    replay_default_mode: str
    replay_require_approval: bool
    recording_max_events: int
    # Phase 15 — screen control.
    screen_control_enabled: bool
    screen_permission_level: int
    screen_screenshots_enabled: bool
    screen_ocr_enabled: bool
    screen_click_enabled: bool
    screen_type_enabled: bool
    screen_clipboard_enabled: bool
    screen_require_approval_for_click: bool
    screen_require_approval_for_type: bool
    screen_require_approval_for_submit: bool
    screen_require_approval_for_clipboard: bool
    screen_emergency_stop_enabled: bool
    screen_allowed_apps: str
    screen_blocked_apps: str
    screen_allowed_folders: str
    screen_screenshot_storage: str
    # Phase 16A — UI automation execution layer.
    screen_ocr_engine: str
    screen_tesseract_cmd: str
    screen_ui_automation_enabled: bool
    screen_pyautogui_fallback: bool
    screen_block_unknown_apps: bool
    screen_execution_step_delay_ms: int
    # Phase 17 — Authentication.
    jwt_secret: str
    allow_open_registration: bool
    allow_first_owner_bootstrap: bool

    # Phase 18 — Demo mode.
    demo_mode: bool
    demo_seed_on_first_run: bool
    # Phase 19 — Pilot readiness.
    usage_tracking_enabled: bool
    external_analytics_enabled: bool
    # Phase 20 — Public landing page & pilot waitlist.
    public_analytics_enabled: bool
    # Phase 21 — Performance, cleanup, retention.
    log_retention_days: int
    demo_data_retention_days: int
    max_audit_exports: int
    max_bug_report_packages: int

    # Phase 22.6 — Voice engine & STT.
    voice_provider: str
    voice_stt_model: str
    openai_api_key: str
    local_whisper_path: str
    voice_allow_cloud_stt: bool
    voice_audio_max_seconds: int
    voice_audio_max_mb: int
    voice_demo_mode: bool

    # Phase 23 — Accountant Agent / LLM Provider.
    agent_provider: str
    agent_api_base_url: str
    agent_api_key: str
    agent_model: str
    agent_allow_cloud: bool
    agent_timeout_seconds: int
    agent_max_steps: int
    agent_dry_run_default: bool

    # Phase 23 — Voice Approval.
    voice_approval_enabled: bool
    voice_approval_high_risk_allowed: bool

    # Phase 23B — Accountant AutoPilot.
    tts_provider: str
    tts_enabled: bool
    tts_language: str
    stt_provider: str
    stt_language: str
    multilingual_enabled: bool
    account_platform_mode: str
    daily_invoice_max: int
    excel_snapshots_enabled: bool
    workflow_auto_save: bool

    # Phase 17+ — SMTP / Email.
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_tls: bool
    smtp_ssl: bool
    smtp_timeout: int
    frontend_url: str

    # Phase 17+ — OAuth login.
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    microsoft_client_id: str
    microsoft_client_secret: str
    microsoft_tenant_id: str

    # Phase 23B — Feature flags.
    pilot_tools_enabled: bool
    advanced_tools_enabled: bool
    dev_tools_enabled: bool

    # Phase 35 — Billing bypass.
    allow_billing_bypass: bool
    app_version: str

    # Phase 38.5 — Local LLM (Ollama / Llama.cpp).
    local_llm_endpoint: str

    # Phase 27 — Windows Voice Layer.
    voice_layer_enabled: bool
    voice_mode_default: str
    voice_local_engine: str
    voice_whisper_cli_path: str
    voice_whisper_model_path: str
    voice_language: str
    voice_push_to_talk: bool
    voice_shortcut_dictation: str
    voice_shortcut_ai: str
    voice_shortcut_agent: str
    voice_confirm_before_paste: bool
    voice_save_history: bool
    voice_history_limit: int
    voice_beep_enabled: bool
    voice_overlay_enabled: bool
    ai_mode_provider: str
    ai_mode_model: str
    ai_mode_api_key: str
    ai_mode_allow_cloud: bool

    @property
    def project_root(self) -> Path:
        return _project_root()

    @property
    def invoices_dir(self) -> Path:
        return self.storage_root / "invoices"

    @property
    def exports_dir(self) -> Path:
        return self.storage_root / "exports"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def audit_dir(self) -> Path:
        return self.data_dir / "audit"

    @property
    def recordings_dir(self) -> Path:
        return self.data_dir / "recordings"

    @property
    def logs_dir(self) -> Path:
        # Phase 8: agent + supervisor log files live here. The
        # directory is created by the lifespan handler in main.py
        # and by the Tauri supervisor.
        return self.data_dir / "logs"

    @property
    def snapshots_dir(self) -> Path:
        # Phase 10: file snapshots for the "Undo Automation"
        # feature. ``data/snapshots/<file_type>/<YYYY>/<MM>/<DD>/<uuid>.<ext>``
        # is the on-disk layout; the metadata lives in the
        # ``file_snapshots`` table.
        return self.data_dir / "snapshots"

    @property
    def browser_snapshots_dir(self) -> Path:
        # Phase 12: PNG screenshots for browser action runs and
        # per-step captures. ``data/browser_snapshots/<run_id>/<step>_<ts>.png``
        return self.data_dir / "browser_snapshots"

    @property
    def screen_snapshots_dir(self) -> Path:
        # Phase 15: PNG screenshots for screen control contexts.
        return self.data_dir / "screen_snapshots"

    @property
    def browser_allowed_domain_list(self) -> list[str]:
        # Resolve the env override, falling back to the in-code
        # default allowlist shipped with the policy model.
        if not self.browser_allowed_domains:
            from .models.browser_automation_policy import DEFAULT_ALLOWED_DOMAINS

            return list(DEFAULT_ALLOWED_DOMAINS)
        return [
            d.strip().lower()
            for d in self.browser_allowed_domains.split(",")
            if d.strip()
        ]

    @property
    def browser_blocked_domain_list(self) -> list[str]:
        if not self.browser_blocked_domains:
            from .models.browser_automation_policy import DEFAULT_BLOCKED_DOMAINS

            return list(DEFAULT_BLOCKED_DOMAINS)
        return [
            d.strip().lower()
            for d in self.browser_blocked_domains.split(",")
            if d.strip()
        ]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def gmail_configured(self) -> bool:
        return bool(self.gmail_client_id and self.gmail_client_secret)

    @property
    def quickbooks_scopes_list(self) -> list[str]:
        if self.quickbooks_scopes == "mock":
            return [
                "com.intuit.quickbooks.accounting",
                "openid",
                "profile",
                "email",
            ]
        return [s.strip() for s in self.quickbooks_scopes.split(",") if s.strip()]

    @property
    def xero_scopes_list(self) -> list[str]:
        if self.xero_scopes == "mock":
            return [
                "openid",
                "profile",
                "email",
                "accounting.contacts",
                "accounting.transactions",
                "accounting.settings",
            ]
        return [s.strip() for s in self.xero_scopes.split(",") if s.strip()]


def get_settings() -> Settings:
    """Public accessor used by FastAPI dependencies."""
    return _settings_singleton()
