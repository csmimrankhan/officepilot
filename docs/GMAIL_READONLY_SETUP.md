# Gmail Read-Only Automation Setup

OfficePilot supports read-only Gmail automation using the `gmail.readonly` OAuth scope. No emails are sent, deleted, or modified — only search, preview, and attachment download.

## Prerequisites

1. A Google Cloud Platform (GCP) project
2. Gmail API enabled
3. OAuth 2.0 credentials (Client ID + Client Secret)

## Step 1: Create GCP Project & Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **APIs & Services → Library**
4. Search for "Gmail API" and click **Enable**

## Step 2: Configure OAuth Consent Screen

1. Navigate to **APIs & Services → OAuth consent screen**
2. Choose **External** user type
3. Fill required fields (App name, User support email, Developer contact)
4. Add scope: `https://www.googleapis.com/auth/gmail.readonly`
5. Add test users if in testing mode

## Step 3: Create OAuth Credentials

1. Navigate to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: `OfficePilot Gmail Client`
5. Download the JSON file

## Step 4: Configure Environment

Set the following environment variables on the backend:

```bash
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/email/oauth/callback
```

On the backend, `app/services/gmail_client.py` reads these at startup. If unset, the Gmail client falls back to **mock mode** (no real Gmail connection — test data only).

## Mock Mode

Without real credentials, the Gmail endpoints return mock data:

- `email_connect_gmail` → returns "mock-user@gmail.com"
- `email_search` → returns pre-defined test messages with invoice/receipt attachments
- `email_download_attachments` → returns mock download paths
- All marked with `mode: "mock"` in responses

This is the default for development and testing.

## API Endpoints

All at prefix `/api/email`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/accounts` | GET | List connected Gmail accounts |
| `/search` | POST | Search emails (`provider`, `query`, `max_results`) |
| `/preview` | POST | Preview a specific email by `message_id` |
| `/attachments/preview` | POST | Preview attachments for messages |
| `/attachments/download` | POST | Download a single attachment |
| `/batch-download` | POST | Batch download attachments (`message_ids[]`, `output_folder`) |

## Frontend Cards

The chat timeline renders 4 cards based on step results:

| Card | Trigger | Action |
|------|---------|--------|
| `GmailConnectCard` | `output.needs_connection` | Connect Gmail account |
| `EmailSearchPreviewCard` | `output.email_search_results` | Select messages to download |
| `AttachmentDownloadCard` | Approval required | Choose output folder |
| `EmailDownloadResultCard` | `output.attachment_download_success` | Create Excel Summary, Save as Skill, Open Folder |

## Safety

- `gmail.readonly` scope — never sends, deletes, or modifies
- All downloads require explicit approval
- Search results show attachment sizes and types before download
- Output folder path is user-specified
- File snapshots created on download for restore capability
- Audit logs on every email action
