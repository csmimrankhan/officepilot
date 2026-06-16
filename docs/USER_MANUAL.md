# OfficePilot AI / InvoicePilot User Manual

Welcome to OfficePilot AI (formerly InvoicePilot), your safe, local-first office automation assistant. This manual will guide you through the core features and daily operations of the app.

## 1. What OfficePilot AI Does
OfficePilot AI automates the tedious parts of back-office work:
- **Invoice Processing**: Imports and extracts data from PDFs, images, and emails.
- **Review & Approval**: Provides a clear interface to verify AI-extracted data.
- **Exporting**: Syncs approved data to Excel or prepares drafts in QuickBooks and Xero.
- **Safety & Audit**: Keeps a permanent record of every action and allows you to "undo" or restore data.
- **Voice Assistant**: Control your workspace using natural voice commands.
- **Smart Assistance**: Safe, controlled browser and screen automation.

## 2. First-Time Setup
1. **Install**: Run the OfficePilot installer on your Windows machine.
2. **First Run**: Open the app. The first user to register will automatically become the **System Owner**.
3. **Agent Check**: Ensure the "Local Agent" indicator is green (bottom status bar).
4. **Demo Data**: If you want to explore, go to **Admin > Demo Center** and click **"Load Sample Dataset"**.
5. **Readiness**: Visit the **Readiness Dashboard** to confirm all engines (OCR, Browser, Accounting) are configured.

## 3. Dashboard Overview
The dashboard is your command center:
- **Pending Invoices**: Needs your review.
- **Approved Invoices**: Ready for export or sync.
- **Recent Activity**: A live feed of what the system has been doing.
- **Safety Status**: Confirmation that the "Kill Switch" is off and policies are active.

## 4. Manual Invoice Upload
1. Navigate to the **Invoices** page.
2. Click **Upload Invoice** and select a PDF or image file.
3. Wait for the **Extraction Engine** to process the file.
4. Click the invoice in the list to open the **Review Screen**.
5. Verify fields, edit if necessary, and click **Approve**.

## 5. Importing from Email
1. Go to **Settings > Email Connections**.
2. Connect your **Gmail** or **Outlook** account (Read-only access).
3. The system will automatically search for invoice-related emails.
4. Attachments are downloaded and placed in your **Review Queue**.

## 6. Reviewing Data
The Review Screen shows extracted fields:
- **Vendor & Invoice #**: Basic identification.
- **Dates**: Issue date and due date.
- **Currency & Totals**: Subtotal, Tax, and Grand Total.
- **Confidence Scores**: If the AI is unsure, fields will be highlighted.
- **Duplicate Warnings**: The system warns you if an invoice number has been seen before.

## 7. Approval Flow
- **Approve**: Moves the invoice to the "Approved" state for final export.
- **Reject**: Archives the invoice.
- **Mark Duplicate**: Prevents accidental double-payment.
- **Needs Review**: Flags for a manager or senior accountant.

## 8. Exporting to Excel
1. Select one or more approved invoices.
2. Click **Export to Excel**.
3. **Preview**: See exactly what rows will be added.
4. **Approve**: The system takes a "snapshot" of the file, then updates it.
5. **Restore**: If you made a mistake, you can restore the file from the previous snapshot.

## 9. Excel Reports
OfficePilot can automatically generate:
- **Vendor Summaries**: Total spend per vendor.
- **Monthly Reports**: Cash flow by month.
- **Tax Summaries**: Tax paid for audit compliance.

## 10. QuickBooks & Xero Sync
1. **Connect**: Link your accounting provider in **Settings**.
2. **Map**: Match OfficePilot vendors/categories to your accounting chart of accounts.
3. **Preview**: See the draft entry before it's sent.
4. **Sync**: Click **Approve Sync**. 
5. **Validation**: The system reads back the draft to confirm it matches exactly.
*Note: OfficePilot never makes payments or posts final entries without manual accounting review.*

## 11. Voice Assistant
Click the **floating microphone** at the bottom-right:
- **Push-to-Talk**: Speak your command.
- **Text Fallback**: Type if you don't have a mic.
- **Examples**:
  - "Show pending invoices"
  - "Open invoice INV-1001"
  - "Export approved invoices to Excel"
  - "Emergency Stop" (Stops all active automation)

## 12. Browser Automation
OfficePilot can help fill forms on the web:
- **Allowed Domains**: Only works on sites you approve.
- **Approval Required**: Every click or "submit" requires your permission.
- **Logs**: Every browser action is recorded.

## 13. Screen Assistant
- **Read-Only**: Can look at your screen to help copy data.
- **Emergency Stop**: Always visible while the assistant is active.
- **Blocked Apps**: Will hide itself if you open sensitive apps (e.g., banking).

## 14. Workflow Recording
1. Click **Record Workflow**.
2. Perform your task manually.
3. Stop recording to see a list of steps.
4. **Replay**: Run the task again. The system will stop at each step for your approval.

## 15. History & Restore
- **Versions**: View every change made to an invoice.
- **Excel Restore**: Roll back a spreadsheet to exactly how it looked before an export.
- **Audit Restore**: Restore data directly from the system audit logs.

## 16. Audit Logs
Every action—from login to sync—is logged. This provides:
- Accountability for team members.
- A paper trail for financial audits.
- Verification of AI actions.

## 17. Backup & Restore
- **Local Backup**: Run a full system backup from **Admin > Backup**.
- **Restore**: Revert the entire system to a previous state if the database is corrupted.

## 18. Safety Controls
- **Kill Switch**: Instantly stops all active AI and automation.
- **Approval Gates**: Nothing happens "behind your back."
- **Privacy**: Your data stays on your machine.

## 19. Troubleshooting
- **Sidecar Offline**: Restart the app or check your firewall.
- **Extraction Failed**: Ensure the file is a clear PDF or image.
- **Sync Failed**: Check your internet connection and re-authorize QuickBooks/Xero.
- **Mic Denied**: Check Windows Privacy Settings for Microphone.

## 20. FAQ
- **Is my data uploaded?** Only if you explicitly enable Cloud AI. Otherwise, it stays local.
- **Can it pay my bills?** No. OfficePilot only creates drafts for you to review in your accounting software.
- **Does it work offline?** Yes, the core features (OCR, Excel, Search) are fully local.
