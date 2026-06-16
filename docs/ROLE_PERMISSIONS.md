# Role Permissions

## Overview

OfficePilot AI supports role-based access control through a permission system
that is enforced at the API level (not only frontend-hidden). Each role has a
set of enabled permissions that determine what actions the user can perform.

## Roles

| Role | Description |
|------|-------------|
| **owner** | Full access to all settings, integrations, policies, and features |
| **admin** | Can manage workflows, integrations, users; cannot disable core safety |
| **reviewer** | Can review and approve invoices; cannot change policies |
| **staff** | Can upload/import invoices and edit extracted fields |
| **viewer** | Read-only access to reports and logs |

## Permission Names

| Permission | Description |
|------------|-------------|
| `manage_safety_policies` | Change safety policy toggles |
| `manage_permissions` | Edit role permissions |
| `manage_integrations` | Configure Gmail, accounting, browser |
| `manage_accounting_sync` | Manage accounting sync settings |
| `manage_screen_control` | Enable/configure screen control |
| `manage_workflow_recording` | Enable/configure workflow recording |
| `manage_browser_automation` | Enable/configure browser automation |
| `manage_users` | Manage users |
| `manage_workflows` | Manage workflow runs |
| `export_audit` | Create audit exports |
| `view_audit_logs` | View audit logs and exports |
| `approve_invoices` | Approve/reject invoices |
| `approve_sync_previews` | Approve accounting sync previews |
| `edit_extracted_fields` | Edit invoice extracted fields |
| `upload_invoices` | Upload new invoices |
| `import_invoices` | Import invoices from email |
| `view_reports` | View reports |
| `view_logs` | View system logs |

## Backend Enforcement

All permission checks are performed in the API router layer using the
`check_permission()` function. If a user lacks the required permission, the API
returns a **403 Forbidden** response regardless of what the frontend shows.

## How to Manage

1. Open **Role Permissions** page.
2. Select a role from the dropdown.
3. Toggle individual permissions on/off.
4. Changes take effect immediately.
