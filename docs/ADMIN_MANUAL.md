# Admin and Owner Manual

This manual is for **System Owners** and **Administrators** responsible for managing OfficePilot AI, setting safety policies, and overseeing team activity.

## 1. System Roles
OfficePilot AI uses a hierarchical role system:
- **Owner**: Full system access, including Safety Policies, User Management, and Backups.
- **Admin**: Full access to all modules but cannot change system-wide Safety Policies.
- **Reviewer/Accountant**: Can process invoices, sync to accounting, and export Excel.
- **Staff**: Can upload and review invoices but cannot Approve or Sync.
- **Viewer**: Read-only access to logs and reports.

---

## 2. Safety Policy Center
This is the most critical area of the app (Owner only).
- **Kill Switch**: A global emergency stop. When "OFF," no automation (Browser, Screen, Accounting Sync) will execute.
- **Cloud AI Allowed**: Toggle this to `OFF` if you want a 100% local, "air-gapped" experience.
- **Browser/Screen Toggles**: Enable or disable these modules entirely.
- **Approval Gates**: We recommend keeping "Approval Required for Write" `ON` at all times.

---

## 3. User & Permission Management
- **Registration**: You can disable "Open Registration" to prevent unauthorized users from creating accounts.
- **Bootstrap**: The very first user to register on a fresh install is granted the **Owner** role automatically.

---

## 4. Audit & Compliance
- **Permanent Logging**: Every business action is logged with a timestamp and the user ID.
- **Audit Export**: Generate a "Compliance Package" (ZIP) containing all logs in JSON and CSV format for external auditors.
- **Redaction**: The system automatically redacts suspected passwords or credit card numbers from logs.

---

## 5. Backup and Disaster Recovery
- **Daily Backups**: We recommend running a "Full Backup" daily.
- **Restore Process**: Restoring a backup overwrites the current database. Always run a backup **before** you restore.
- **Snapshots**: If a specific file (like an Excel sheet) is corrupted, use the "File History" feature to restore that specific file rather than the whole system.

---

## 6. Managing Integrations
### Email (Gmail/Outlook)
- Connect using **OAuth**. 
- Permissions are requested as "Read-Only." 
- OfficePilot only downloads attachments; it never deletes or sends emails.

### Accounting (QuickBooks/Xero)
- **Mapping**: Admins must map OfficePilot vendors to the corresponding "Account Name" in QuickBooks.
- **Sync Limits**: You can set a maximum "Amount Limit" for voice-initiated syncs to prevent large errors.

---

## 7. Voice & Automation Settings
- **STT Provider**: Choose between "Mock" (safe), "Local Whisper" (private), or "OpenAI" (high accuracy).
- **Allowed Domains**: For browser automation, specify exactly which websites (e.g., `sheets.google.com`) the AI is allowed to visit.
- **Blocked Apps**: List applications (e.g., `Notepad`, `Banking.exe`) that the screen assistant should **never** look at.

---

## 8. Pilot Readiness Dashboard
Before rolling out to your team, check the **Readiness Dashboard**:
- **Health**: Are all local services (Database, Agent, Sidecar) green?
- **Config**: Are your API keys and certificates valid?
- **Safety**: Are your policies clearly defined?
- **Data**: Have you cleared the demo data before using real production invoices?

---

## 9. Security Best Practices
1. **Never Share Owner Credentials**: Use the Owner account only for policy changes.
2. **Review Logs Weekly**: Check for "Blocked Actions" in the audit log.
3. **Test Your Restore**: Run a restore on a test machine once a month to ensure your backups are valid.
4. **Kill Switch Awareness**: Ensure all staff know where the Kill Switch is located.
