# OfficePilot AI — Founder Pitch

## One-Line Pitch

OfficePilot AI turns invoice emails and PDFs into Excel and accounting drafts, with approval, audit logs, and restore.

---

## 30-Second Pitch

OfficePilot AI turns invoice emails and PDFs into Excel and accounting drafts, with approval, audit logs, and restore. It runs entirely on your machine — no cloud, no data sharing. Accountants, bookkeepers, and admin teams use it to stop manual data entry and get a clean audit trail. We're in pilot and looking for first users.

---

## 2-Minute Pitch

### The Problem

Manual invoice processing is slow, error-prone, and leaves no audit trail. Accounting teams receive invoices as email attachments or PDFs, retype the numbers into Excel or QuickBooks, and hope nothing was mistyped. A single decimal error cascades. There is no version history, no rollback, no way to prove what happened when. For a firm processing hundreds of invoices per week, the cost in hours and risk is enormous.

Existing software solutions fall into two camps. Cloud tools require uploading every invoice to a third-party server — your data, their AI. Desktop accounting tools like QuickBooks Desktop handle books well but offer no intelligent invoice capture. The gap between receiving an invoice and posting it is filled by manual labor.

### The Solution

OfficePilot AI is a desktop application that runs entirely on the user's machine. Drop in a PDF or forward an email — OfficePilot reads the invoice using local OCR and AI extraction, presents the data for human approval, then exports to Excel or drafts an entry in QuickBooks or Xero.

The workflow is straightforward:

1. An invoice arrives as a PDF or email attachment
2. OfficePilot extracts vendor, date, line items, totals, and tax using local AI
3. The extracted data is presented in a review queue with a side-by-side preview of the original document
4. The user reviews, corrects if needed, and clicks approve
5. OfficePilot writes to Excel or drafts an accounting entry in QuickBooks/Xero
6. Every action is logged. Every version is saved. Every restore is recorded with a mandatory reason

### Safety Built In

- Approval gates before any write or export
- Full audit log of every action, with actor, timestamp, and before/after state
- Version history for invoices, settings, and workflow state
- One-click restore with reason capture
- File snapshots before any modification — originals are never lost
- Global kill switch to halt all automation instantly
- Role-based permissions (5 roles, 18 permissions)
- No cloud, no data sharing, no AI training on your data
- No banking, payment, or password-manager automation
- Domain blocklist that always wins over allowlist
- Sensitive value redaction in all logs and previews

### Pilot

We are looking for 10–20 pilot users — accounting firms, bookkeepers, and finance teams — to use OfficePilot in their real workflow and help shape the product. Pilot users get direct access to the founding team, priority feature requests, and a lifetime discount.

What we ask in return: honest feedback, bug reports, feature requests, and a willingness to hop on a 30-minute call every few weeks. Your input directly determines what ships next.

---

## Investor-Style Pitch

### Problem

Small businesses and accounting firms waste thousands of hours on manual invoice data entry. Every invoice is a risk of mistyped numbers, lost files, and missing audit trails. Existing solutions are either cloud-based (data leaves your machine), expensive (enterprise ERP), or require complex integration and training.

The pain is universal: accounts payable teams, freelance bookkeepers managing 20+ clients, CPAs reviewing quarterly statements — all of them retyping the same data that already exists in a PDF.

### Solution

A local-first AI desktop app that reads invoice PDFs and emails, extracts structured data, presents it for human approval, and exports to Excel, QuickBooks, or Xero — all with full audit logging, version history, and one-click restore. No cloud dependency. No data sharing. No AI training on customer data.

Key architectural decisions that differentiate us:

- **Local-first by default**: The entire application runs on Windows. SQLite database, local OCR engines, local AI extraction. The cloud is optional and additive, never required.
- **Human-in-the-loop**: Every write, export, and sync requires explicit approval. Nothing happens automatically without a human saying yes.
- **Append-only history**: Versions are never deleted. Snapshots are never overwritten without a backup. The audit log is immutable.
- **Defense in depth**: Role permissions, domain blocklists, emergency kill switch, sensitive value redaction — safety is not a feature, it is the architecture.

### Market

- 8M+ small businesses in the United States alone, most using QuickBooks or Excel
- 500K+ accounting firms globally, from solo practitioners to top 100 firms
- Tens of millions of knowledge workers who process invoices daily as part of their role
- Growing regulatory pressure for audit trails (SOC 2, GDPR, SOX, IRS requirements)
- Invoice processing software market valued at $30B+ and growing at 10% CAGR

### Traction

- Full working desktop application built on Tauri (Rust) + FastAPI (Python) + SQLite
- 548 passing backend tests, 94 frontend tests — CI-gated quality
- Invoice parsing with three local OCR engines: Tesseract, Windows OCR, PaddleOCR
- Accounting sync with QuickBooks Desktop, QuickBooks Online, and Xero — mock and sandbox modes included
- Browser automation via Playwright with domain allowlist, risk classification, and approval gating
- Screen control with read-only context detection, OCR, and approval-gated click/type actions
- Workflow recording with dry-run replay and approval checkpoints at every step
- Production authentication: PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 JWT tokens, no external dependencies
- Demo mode with sample dataset and 12-step guided onboarding
- 20 major phases shipped, app version 0.21.0, 200+ endpoints
- End-to-end Windows installer with Authenticode code signing and auto-update wiring
- 5-page documentation suite (architecture, security, deployment, release process, testing)

### Competition

| Product | Local-First | Full Audit Trail | Version History | Accounting Sync | Approval Gates |
|---------|-------------|------------------|-----------------|-----------------|----------------|
| OfficePilot AI | Yes | Yes | Yes | QB + Xero | Yes |
| Cloud OCR tools | No | Partial | No | Yes | No |
| QuickBooks native | N/A | No | No | Built-in | No |
| ERP systems | No | Yes | Partial | Built-in | Partial |
| Manual entry | N/A | No | No | Manual | N/A |

### Team

[Founder name] — [brief background]

### Business Model

- Desktop license: one-time purchase or annual subscription per seat
- Optional cloud sync subscription for multi-machine teams, backup, and cross-machine settings (future)
- Enterprise tier with SSO, dedicated support, on-prem deployment, custom integration (future)
- Revenue projection: $500–$1,000 per seat per year for desktop license

### Ask

- **Pilot users**: 10–20 accounting firms to use the product and provide feedback
- **Feedback**: What features matter most? What is missing? What is confusing?
- **Introductions**: Accounting firms, bookkeeping networks, industry events, podcasts
- **Mentorship**: Advice on SaaS motion, enterprise sales, and accounting channel partnerships
- **Advisors**: CPAs or bookkeeping firm owners willing to join an advisory board

---

## Accountant/Customer Pitch

Here's what OfficePilot does for you: your client sends an invoice PDF. OfficePilot reads it, extracts the numbers, and presents them for your approval. You click approve. It writes to Excel or drafts a QuickBooks entry. Everything is logged. If something goes wrong, you restore a previous version. No cloud. No AI training on your data. No bank access. Just invoice automation you can trust.

Let's be specific about what changes in your day:

- A client emails you an invoice. Instead of opening a PDF, copying the total, switching to Excel or QuickBooks, typing it in, double-checking, and moving on — you open OfficePilot, review the extraction, click approve. That is it.
- End of month. You need to prove what happened. Open the audit log and you have every approval, every change, every restore, with timestamps and actor names.
- A vendor sends a corrected invoice. OfficePilot captures the new version. The old version is snapshotted. You can compare them side by side before approving.
- You are onboarding a new client with two years of historical invoices. OfficePilot processes them in batch. You review at your pace. Every extraction is logged.
- You step away from your desk. Your junior staff have view-only access. Only senior staff can approve exports. OfficePilot enforces it.

---

## FAQ for Founders

**Is this SaaS?** No. OfficePilot runs entirely on your Windows machine. There is no cloud dependency for core functionality. A future cloud sync option will be optional and additive — never required for core operation.

**How is this different from cloud invoice tools like Bill.com, Melio, or Hubdoc?** Cloud tools require uploading every invoice to a third-party server for processing. Your data trains their AI. OfficePilot keeps everything local. Your data never leaves your machine unless you explicitly choose to export or sync to your accounting provider.

**What about accounting integrations?** OfficePilot can draft entries in QuickBooks Desktop, QuickBooks Online, and Xero. Sync is preview-and-approve gated — nothing is written automatically without your say-so. We support both mock/sandbox for testing and production sync.

**Do you handle my bank or payment data?** No. OfficePilot explicitly blocks automation of banking, payment, password-manager, and crypto-exchange sites. The domain blocklist is hard-coded and always wins over any allowlist. We do not connect to bank APIs, initiate payments, or store financial credentials.

**What if something breaks?** Every invoice version is saved. Every file is snapshotted before modification. Every restore is logged with a reason. You can roll back any entity, file, or workflow state at any time. There is no way to permanently lose data through the application.

**Is it ready now?** OfficePilot is in pilot with a full working product. We have shipped 20 phases covering upload, parsing, approval, export, accounting sync, browser automation, screen control, workflow recording, production auth, demo mode, and more. We are looking for pilot users to help us polish the remaining rough edges and prioritize the roadmap.

**Who is this for?** Accounting firms processing invoices for multiple clients. Bookkeepers managing accounts payable. Small business owners who want to stop typing numbers. Enterprise AP departments looking for a local-first alternative to cloud tools.

**Who is this not for?** Companies that need cloud access, mobile apps, multi-user real-time collaboration, or payment initiation. Those are future roadmap items, not current features.

**How long does setup take?** Download the installer, run it, and you are up in under 5 minutes. Demo mode gives you sample data to explore without connecting real invoices.

**What about data privacy compliance?** Since everything runs locally with no cloud dependency, there are no data residency concerns. No data is sent to external servers for processing. No AI models are trained on your invoices. This makes OfficePilot suitable for firms handling sensitive client data under GDPR, HIPAA, or SOC 2 obligations.

---

*OfficePilot AI — version 0.21.0 | Phase 21: Performance Optimization, Startup Speed, UI Polish, Release Readiness*
