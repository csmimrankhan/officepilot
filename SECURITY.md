# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.36.x  | :white_check_mark: |
| < 0.36  | :x:                |

## Reporting a Vulnerability

OfficePilot AI takes security seriously. If you discover a security vulnerability,
please do **not** open a public GitHub issue. Instead, report it privately:

- **Email**: security@officepilot.ai
- **PGP Key**: Available on request

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (if known)

We will acknowledge receipt within 48 hours and provide a timeline for the fix.

## Security Features

- **Local-first**: All data stays on your machine by default.
- **Read-only Gmail**: The Gmail integration uses `gmail.readonly` scope only.
  Send, delete, modify, label, archive, and spam operations are blocked at every layer:
  planner regex, executor tool check, and tool registry.
- **Kill Switch**: A global kill switch instantly halts all automation.
- **Audit Logs**: Every state-changing action is logged with actor, timestamp, and details.
- **Input Redaction**: Sensitive values (passwords, tokens, API keys, OTP, CVV, SSN, PIN)
  are redacted from all logs, previews, and step results.
- **Domain Blocklist**: Banking, payment, password-manager, crypto, and government tax
  domains are blocked by default in browser automation.
- **App Blocklist**: Password managers, banking apps, credential dialogs are blocked
  from desktop control.
- **Approval Gates**: All write operations require explicit user approval.
- **Authentication**: Passwords are hashed with PBKDF2-HMAC-SHA256. JWT tokens use HMAC-SHA256.
- **No External Telemetry**: Usage tracking is local-only and opt-in.
