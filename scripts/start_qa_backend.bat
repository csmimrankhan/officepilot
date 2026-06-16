@echo off
set ALLOW_OPEN_REGISTRATION=true
set ALLOW_BILLING_BYPASS=true
cd /d "%~dp0..\backend"
python -m uvicorn app.main:app --reload --port 8765
