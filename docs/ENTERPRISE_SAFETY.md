# Enterprise Safety

## Overview

OfficePilot AI includes a centralized **Safety Policy Center** that controls all
risky automation features. All automation is **disabled by default** and must be
explicitly enabled by an authorized administrator or owner.

## Default-Safe Configuration

| Feature | Default |
|---------|---------|
| Cloud AI processing | Disabled (requires approval) |
| Browser automation | Disabled |
| Screen control | Disabled |
| Workflow recording | Disabled |
| Accounting sync | Disabled |
| Voice commands | Disabled |
| Screenshots | Disabled |
| OCR | Disabled |
| Require approval for write | Enabled |
| Require snapshot for file changes | Enabled |
| Block unknown apps | Enabled |
| Block unknown domains | Enabled |

## How to Enable Safely

1. Open **Safety Policy Center** (requires `owner` role).
2. Enable only the specific features you need.
3. Review approval requirements — keep "Require approval for write" enabled.
4. Save policies.
5. Verify the feature works as expected before using in production.

## Role Permissions

Only the **Owner** role can change safety policies. Other roles have restricted
permissions:

- **Admin**: Can manage workflows, integrations, but cannot disable core safety
  requirements.
- **Reviewer**: Can review and approve invoices; cannot change policies.
- **Staff**: Can upload/edit invoices; cannot approve accounting sync or enable
  screen control.
- **Viewer**: Read-only access to reports and logs.

## What Is Intentionally Blocked

- Banking/payment website automation
- Password/credential capture
- Login, CAPTCHA, 2FA bypass
- Unrestricted mouse/keyboard control
- Autonomous background agents
- Email sending
- Payroll/tax filing automation
- Cloud backup
- Multi-agent autonomous workflows
- Marketplace

## Global Kill Switch

The **Emergency Safety** page provides a "Stop All Automation" button that
immediately halts:

- Browser automation
- Screen control
- Workflow recording & replay
- Accounting sync

While the kill switch is active, all automation actions are blocked at the API
level. Use the "Resume Automation" button to restore service (only services
that are enabled in policy will resume).
