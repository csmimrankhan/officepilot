# OfficePilot AI — Pilot Program Guide

Welcome to the OfficePilot AI pilot program. This guide will help you get started, understand the capabilities, and provide feedback.

## What is OfficePilot AI?

OfficePilot AI is a Universal Voice Accountant Agent — a Windows desktop app that automates accounting work. You tell it what to do by voice or text, it plans the task, shows the steps for approval, executes safely, and remembers workflows for later.

## Getting Started

### Installation

1. Run the MSI installer (`OfficePilot AI_<version>_x64_en-US.msi`)
2. Follow the setup wizard (installs per machine)
3. Launch OfficePilot AI from the Start Menu or desktop shortcut
4. The first launch takes up to 60 seconds as the backend sidecar starts

### First Launch

1. **Register an account** — Create an email + password account
2. **Login** — Use your credentials to access the app
3. **Demo Mode** — Toggle Demo Mode in Settings to explore with sample data
4. **Onboarding Checklist** — Follow the sidebar widget for a guided tour

### Architecture

```
┌─────────────────┐     ┌──────────────────┐
│ Tauri Desktop   │────▶│ Python Backend   │
│ (Rust shell)    │     │ (FastAPI + SQLite)│
│                 │◀────│                  │
│ Frontend (React)│     │ Port 8000        │
└─────────────────┘     └──────────────────┘
```

All data stays on your machine. No cloud dependency.

## Pilot Features

| Feature | Description |
|---------|-------------|
| **Excel Automation** | Create Excel summaries from invoice data. Auto-detect accounting columns. |
| **Browser Automation** | Open websites, navigate reports, export data. Manual login required (no passwords stored). |
| **Gmail Read-Only** | Search, preview, and download invoice attachments. No send/delete/mark-read ability. |
| **Workflow Recorder** | Record your actions, convert to reusable skills, run again later. |
| **Skills System** | Save workflows as skills. Trigger by matching phrases. |
| **Voice Commands** | Speak commands via whisper.cpp (Ctrl+Alt+Space). |
| **Safety Controls** | Emergency stop, blocked commands, approval gates, kill switch. |
| **Audit Log** | Every action is logged for review. |
| **Version History** | Restore previous versions of invoices, files, workflows. |
| **Auto-Update** | Automatic update checks via built-in updater. |

## Demo Script

For a step-by-step demo walkthrough, see `PILOT_DEMO_SCRIPT.md` in the `docs/` folder.

## Known Limitations

See `KNOWN_LIMITATIONS.md` for the current list of known issues and workarounds.

## Reporting Issues

Use the in-app **Bug Report** feature (Settings → Bug Report) to submit diagnostic packages, or use the template in `BUG_REPORT_TEMPLATE.md` for manual reports.

## Feedback

Use the in-app **Send Feedback** button in Settings. All feedback is stored locally and reviewed by the team.

## Support

During the pilot program:
- Submit bug reports via the in-app tool
- Send feedback through the Feedback form
- Contact your pilot coordinator for urgent issues

## Data Privacy

- **All data is local**. No data is sent to external servers.
- **Usage tracking** is local-only and can be disabled (`USAGE_TRACKING_ENABLED=false`).
- **Bug reports** are opt-in and sensitive data (passwords, tokens, emails) is automatically redacted.
- **Invoice files and screenshots** are never included in bug reports unless you explicitly choose to include them.
