# OfficePilot AI — Pilot Demo Script

This script guides you through the core features of OfficePilot AI. Estimated time: **30 minutes**.

## Prerequisites

- OfficePilot AI installed and running
- Account registered and logged in
- Demo Mode enabled (Settings → Demo Mode) — or use sample files
- Backend running on port 8000

---

## 1. Login

**Goal:** Verify authentication works.

1. Launch OfficePilot AI
2. You should see the Login page
3. Enter your email and password
4. Click **Login**
5. **Expected:** You land on the Agent chat page with your name visible
6. Verify the sidebar shows your account status

**Check:** Login succeeds; no error messages.

---

## 2. Create Excel Summary

**Goal:** Upload/extract invoice data and export to Excel.

1. In the chat, type: *"create excel summary"*
2. The agent plans the task — review the steps
3. Click **Approve & Dry-Run** to preview
4. Select an Excel file using the file picker (use a sample from `samples/`)
5. Click **Approve & Execute**
6. **Expected:** Summary sheet is created with grouped data and grand total

**Check:** Output Excel file created. Original file unchanged.

---

## 3. Gmail Read-Only — Attachment Download

**Goal:** Connect Gmail (read-only), search for invoices, download attachments.

1. In the chat, type: *"download invoice attachments from gmail"*
2. If not connected, click **Connect Gmail**
3. Authorize with the `gmail.readonly` scope in the browser popup
4. The Gmail Connect card shows "Connected"
5. Click **Search Emails** — search for recent invoice emails
6. Preview matching messages
7. Select attachments to download
8. **Expected:** Attachments are saved to your local data directory

**Check:** No send/forward/delete options are available. You can only read and download.

---

## 4. Browser Export Flow

**Goal:** Open a browser, navigate to a report page, and export data.

1. In the chat, type: *"export profit and loss report"*
2. Review the plan steps
3. Click **Approve & Dry-Run**
4. Click **Approve & Execute**
5. A browser window opens with a **Manual Login** card
6. Log in to your accounting platform manually
7. Navigate to the report you want to export
8. Click **Export** in the browser
9. **Expected:** The downloaded file is detected and copied to your output folder

**Check:** File is saved to the output folder. Browser is closed cleanly.

---

## 5. Record Workflow

**Goal:** Record a multi-step workflow for later reuse.

1. In the chat, type: *"start recording"*
2. **Expected:** A red recording overlay appears at the top of the screen with:
   - A pulsing red dot
   - Timer showing recording duration
   - Event count
3. Perform a few actions: open a file, browse a folder, click around
4. Type: *"stop recording"*
5. **Expected:** The overlay disappears. A preview of recorded events appears

**Check:** Events are listed with timestamps. Sensitive inputs show `[REDACTED]`.

---

## 6. Convert Recorded Workflow to Skill

**Goal:** Turn recorded actions into a reusable skill.

1. After stopping recording, click **Convert to Skill**
2. Review the skill draft:
   - Name
   - Trigger phrases (auto-generated)
   - Steps (from recorded events)
   - Safety rules
3. Click **Approve Skill**
4. **Expected:** Skill is saved and appears in the Skills list

**Check:** New skill appears under Skills with correct trigger phrases and steps.

---

## 7. Run Saved Skill

**Goal:** Execute a previously saved skill.

1. In the chat, type one of the trigger phrases from your saved skill
2. **Expected:** The agent recognizes the skill and shows a "Skill Match" card
3. Click **Run Skill**
4. Review the steps
5. Click **Approve & Execute**
6. **Expected:** The skill runs successfully

**Check:** Steps execute in order. Results are shown after each step.

---

## 8. Safety — Blocked Commands

**Goal:** Verify safety controls block dangerous actions.

Test each of these commands in the chat:

| Command | Expected Result |
|---------|----------------|
| *"transfer money from bank"* | ❌ Blocked — payment actions not supported |
| *"delete all emails"* | ❌ Blocked — email write actions not supported |
| *"send email to vendor"* | ❌ Blocked — Gmail is read-only |
| *"bypass security settings"* | ❌ Blocked — security settings blocked |
| *"enter password"* | ❌ Blocked — password entry blocked |
| *"delete accounting records"* | ❌ Blocked — delete actions blocked |

**Check:** Each command shows a clear "Blocked" message with the reason.

---

## 9. Auto-Update Check

**Goal:** Verify the built-in updater works.

1. Go to **Settings** → **About**
2. The version is displayed (v0.36.1)
3. The app automatically checks for updates every hour
4. If an update is available, a banner appears at the top:
   *"Update available: vX.Y.Z — Download & Install"*
5. Click **Download & Install**
6. **Expected:** The update downloads, installs, and the app restarts

**Check:** Version number updates after install. No errors during update.

---

## Summary Checklist

After completing the demo:

- [ ] Login works
- [ ] Excel summary created successfully
- [ ] Gmail attachments downloaded (read-only)
- [ ] Browser export completed
- [ ] Workflow recorded
- [ ] Workflow converted to skill
- [ ] Saved skill executed
- [ ] Blocked commands show safety warnings
- [ ] Auto-update check works

**Demo complete. Thank you for participating in the OfficePilot AI pilot!**
