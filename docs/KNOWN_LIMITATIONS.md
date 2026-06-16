# OfficePilot AI — Known Limitations

This document lists known limitations for the v0.36.1 pilot release.

## General

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 1 | First launch takes 30–60 seconds | Cold start: PyInstaller unpacks + Python imports | Wait for the "Agent Ready" indicator. Fixed in subsequent starts. |
| 2 | Only one user account per installation | Multi-user not yet supported | Use separate machines or VMs for multiple users |
| 3 | No cloud sync | All data is local to the machine | Regular backups recommended |
| 4 | Windows-only | Mac/Linux not supported | Use a Windows VM or Windows machine |
| 5 | SQLite database (no concurrent writes) | Two simultaneous users on same DB may conflict | Single-user mode only |
| 6 | Data directory not configurable after install | Storage path set at first launch | Set `OFFICEPILOT_DATA_DIR` env var before first run |

## Excel Automation

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 7 | Only `.xlsx` and `.csv` files supported | `.xls` (legacy Excel) not supported | Convert to `.xlsx` using Excel or LibreOffice |
| 8 | Large files (>100 MB) may timeout | Summary generation may fail | Split files into smaller chunks |
| 9 | Formula detection is basic | Some complex formulas may not be detected | Manually verify formula-heavy spreadsheets |
| 10 | File picker requires manual selection | No drag-and-drop in all views | Use the Browse button in the file picker |

## Browser Automation

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 11 | Manual login required for every session | Passwords are never stored or automated | Keep your credentials ready |
| 12 | Chromium bundled via Playwright | ~200 MB download on first run | Pre-download on fast connection |
| 13 | Some websites may detect automation | Login forms may show CAPTCHA | Complete CAPTCHA manually, then continue |
| 14 | Banking/payment/password-manager domains blocked | Cannot automate financial sites | Use the desktop's native browser for those tasks |
| 15 | Only one browser session at a time | Cannot run parallel browser automations | Wait for current session to finish |

## Gmail Integration

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 16 | **Read-only** — cannot send, forward, delete, or mark-read | Write operations explicitly blocked by design | Use Gmail's web interface for write operations |
| 17 | OAuth token expires after 7 days (offline) | Re-authorization required weekly | Re-connect Gmail when token expires |
| 18 | Only Gmail supported | Outlook/Exchange/Yahoo not supported | Use Gmail for automated flows |
| 19 | Attachment download limited to 25 MB per file | Larger attachments skipped | Download large files manually |

## Workflow Recorder

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 20 | Desktop click/type recording requires OCR | May not detect all UI elements precisely | Use keyboard shortcuts where possible |
| 21 | Recorded skills cannot be edited directly | Must delete and re-record to change steps | Plan your recording carefully |
| 22 | Skill matching uses simple phrase matching | May not match nuanced commands | Use clear, specific trigger phrases |
| 23 | Emergency stop stops all running automation | Cannot resume stopped workflow | Re-run the workflow from scratch |

## Voice Layer

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 24 | Whisper model downloads ~150 MB on first use | One-time download may take a few minutes | Use a stable internet connection |
| 25 | Voice recognition accuracy depends on microphone quality | Background noise reduces accuracy | Use a headset in quiet environments |
| 26 | Roman Urdu support is experimental | Some phrases may not be recognized correctly | Fall back to text input |
| 27 | Only English and Roman Urdu supported | Other languages not yet supported | Use text input for other languages |

## Performance

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 28 | High memory usage (~500 MB) during heavy automation | Sidecar uses Python + Chromium | Close unused apps while running automations |
| 29 | OCR processing takes 2–5 seconds per screen capture | Real-time feedback is not instant | Use keyboard navigation where possible |
| 30 | Backup/Restore of large databases (>100 MB) may be slow | Restore could take 1–2 minutes | Schedule backups during idle time |

## Security & Permissions

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 31 | No role-based access in pilot | All pilot users have full access | Trusted pilot users only |
| 32 | No audit log encryption | Logs stored as plaintext | Restrict physical machine access |
| 33 | Kill switch is per-machine, not per-user | One kill switch stops all automation on the machine | Coordinate with other users |

## Updater

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 34 | Update check only on app startup and every hour | May not detect updates immediately | Click "Check for Updates" in Settings |
| 35 | No delta/partial updates | Full MSI download for each update | Use fast internet connection |
| 36 | Update requires admin privileges (per-machine install) | Non-admin users cannot self-update | Contact IT for updates |

## Stability Freeze (v0.36.1)

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 37 | **Zero cloud AI by default** | Agent uses mock planner (rule-based) for all plans | Set `AGENT_PROVIDER`, `AGENT_ALLOW_CLOUD=true`, and API keys to enable LLM-powered plans |
| 38 | **Mock planner is rule-based** | Only handles predefined command patterns | Use clear English phrases matching known patterns (e.g., "read this screen", "create excel summary") |
| 39 | **Cloud AI disabled default** | All three AI integrations (agent planner, AI mode polish, voice STT) default to mock/local | Requires explicit opt-in via env vars |
| 40 | **API keys never exposed in UI** | Cannot verify which key is configured from the admin page | Check `AGENT_API_KEY` / `AI_MODE_API_KEY` / `OPENAI_API_KEY` in env or `.env` file |

## Pilot-Specific

| # | Limitation | Impact | Workaround |
|---|-----------|--------|------------|
| 41 | No multi-organization support | All data under one organization | Single-org use only |
| 42 | No team collaboration features | No shared workflows or permissions | Local single-user workflows only |
| 43 | No Premium/Billing features | License features are bypassed in pilot | All features available for free during pilot |
| 44 | 3–5 pilot user limit | Not designed for large-scale deployment | Scale out after pilot phase |

---

## Reporting New Limitations

If you discover a limitation not listed here, please report it via:
- In-app: **Settings → Bug Report**
- Template: `BUG_REPORT_TEMPLATE.md`
