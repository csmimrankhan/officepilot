# OfficePilot AI: Founder's Manual Testing Guide

This guide is designed for a non-technical founder to verify that OfficePilot AI is working correctly. No coding knowledge is required. Just follow the steps, click the buttons, and check the results.

---

## 1. Before You Start

**What you need:**
- OfficePilot AI installed on your Windows computer
- Your login email and password (or you just registered for the first time)
- A sample invoice PDF or image file (any real invoice from your desk)

**Important:** You can test everything using Demo Mode — no real client data is needed.

**Startup Checklist:**

- [ ] Double-click the OfficePilot AI icon to open the app
- [ ] The login screen opens without freezing or showing an error
- [ ] Enter your email and password, click **Log In**
- [ ] The main Dashboard loads — you should see summary cards (like total invoices, pending reviews)
- [ ] Look at the bottom bar or status indicator — does it say **Local Agent Online** with a green dot?
- [ ] No red error banner is visible at the top of the screen

> **If login fails**: Take a screenshot of the error message. Try "Forgot Password" or reinstall the app.
> **If Local Agent is offline**: The app cannot work. Stop here and fix before continuing.

---

## 2. Basic App Health Test

Checking if all the "engines" under the hood are running.

1. In the left menu, click **Admin** (or **Settings** depending on your version)
2. Click **Readiness Dashboard** (or **Diagnostics**)
3. Look at the colored cards on the screen:

   - **Green card** = Ready to go. No problems.
   - **Yellow card** = Working, but needs attention (like a missing API key or optional service).
   - **Red card** = Broken or disconnected. Needs fixing before you demo.

4. Count how many green cards you see.

**PASS:**
- App opens without crashing
- Readiness page loads fully
- At least "Database" and "Storage" cards show green

**FAIL:**
- App gets stuck on a loading spinner
- Readiness page is blank or shows an error
- Local Agent shows offline (red dot)

**If FAIL:** Take a screenshot of the whole page. Note which cards are red.

---

## 3. Demo Data Test

Testing with "fake" sample invoices so we don't mess up your real files.

1. Go to **Admin** in the left menu
2. Find **Demo Center** or **Demo Mode**
3. Click the big button: **Load Sample Dataset**
4. Wait for a success message (green bar that says "Demo data loaded" or "Success")
5. Click **Invoices** in the main menu
6. Do you see a list of fake invoices (like "Acme Corp," "Sample Vendor," or similar)?

- [ ] I clicked Load Sample Dataset
- [ ] I saw a success message
- [ ] I see fake/sample invoices in the list

**PASS:** Fake invoices appear and are clearly labeled "Sample," "Demo," or "Fake."

**FAIL:**
- No invoices appear at all
- Your real business data is mixed with demo data
- An error message appears

**If FAIL:** Take a screenshot. Note whether real data got mixed in — that would be a safety problem.

> **STOP HERE AND FIX**: If loading demo data causes an error or crashes the app, fix this before proceeding. Everything else depends on demo data working.

---

## 4. Invoice Upload Test

Testing if the AI can "read" a real document.

1. Go to the **Invoices** page
2. Click **Upload Invoice**
3. A file picker window opens — select any PDF or image of an invoice from your computer
4. Wait a few seconds while the status says "Processing" or "Extracting"
5. Once done, click on that invoice row to open the detail view
6. Look at the fields that appeared:

   - **Vendor Name**: Did it find the company name?
   - **Invoice Number**: Did it find a number like "INV-001"?
   - **Date**: Did it find a date?
   - **Total Amount**: Did it find the total?

- [ ] I selected a file
- [ ] Status changed from "Uploading" to "Extracting" to "Done"
- [ ] At least 3 out of 4 fields are filled in

**PASS:** The document uploaded without errors and the AI filled in most of the fields.

**FAIL:**
- Upload fails with an error message
- Invoice gets stuck at "Processing" for more than 2 minutes
- All fields are completely empty (the AI didn't read anything)
- The app crashes or freezes

**If FAIL:** Save the invoice file you tried to upload. Take a screenshot of the error. Note the file type (PDF, JPG, PNG).

---

## 5. Invoice Review and Approval Test

Testing the "human checks the robot" safety step.

1. Open one of your **Pending** invoices (from the list, click one that says "Pending")
2. Click into any editable field (like the Vendor Name)
3. Change the text slightly (for example, add the word "Test" to the vendor name)
4. Click **Save**
5. Click the **Approve** button
6. Go back to the invoice list — does the status now say **Approved**?

- [ ] I edited a field and clicked Save
- [ ] I clicked Approve
- [ ] The status changed to "Approved"

**PASS:** You could edit, save, and approve without errors.

**FAIL:**
- The **Save** button does nothing when clicked
- The **Approve** button is grayed out or does nothing
- The status stays "Pending" even after clicking Approve

**If FAIL:** Take a screenshot showing the invoice detail with the Approve button visible.

---

## 6. Version History / Restore Test

Testing the "Undo" safety net.

1. Open an **Approved** invoice from the list
2. Find the **Total Amount** field
3. Change it to a different number (e.g., if it says $100.00, change it to $999.99)
4. Click **Save**
5. Look for a tab or button called **Version History**, **History**, or **Versions** — click it
6. Do you see two versions listed? (The original and the edited one)
7. Click **Restore** on the older (original) version
8. Go back to the invoice — is the Total Amount back to the original value ($100.00)?

- [ ] I changed the total and saved
- [ ] Version History shows at least 2 entries
- [ ] Restore brought back the old value

**PASS:** The system remembered your change and let you undo it correctly.

**FAIL:**
- No Version History tab exists
- Version History is empty
- Clicking Restore does nothing or shows an error
- The wrong value comes back after restore

**If FAIL:** Take a screenshot of the Version History panel showing it's empty or showing the error.

---

## 7. Excel Export Test

Testing if approved data safely moves into a spreadsheet.

1. Go to the **Invoices** list
2. Find one or more **Approved** invoices
3. Check the checkbox next to them (to select them)
4. Find and click **Export to Excel** (may be a button at the top or in a menu)
5. A **Preview** popup should appear showing the data that will be exported
6. Check that the numbers shown in the preview look correct
7. Click **Approve Export**
8. A success message should appear — note the file path or download link
9. Open the generated Excel file on your computer
10. Look for a row with your invoice's vendor, date, and amount

- [ ] I see a preview before export
- [ ] I could approve the export
- [ ] The Excel file opens and contains my invoice data

**PASS:** An Excel file was created with the correct data.

**FAIL:**
- Preview shows wrong amounts or invoice numbers
- No file was created (no success message)
- The Excel file is empty or shows "Error"
- The file cannot be opened

**If FAIL:** Take a screenshot of the preview. Save the Excel file if it was created.

---

## 8. Excel Summary / Formula Test

Testing if the app can create totals and summaries in Excel.

1. Go to **Excel Automation** or **Excel Tools** in the menu
2. Select the approved invoice data (you may need to select invoices first)
3. Click **Create Vendor Summary**
4. Open the generated Excel file
5. Look at the bottom tabs — is there a sheet called "Vendor Summary" or similar?
6. Now go back and click **Create Monthly Summary**
7. Open the file again — is there a "Monthly Summary" sheet?

- [ ] Vendor Summary sheet exists with totals
- [ ] Monthly Summary sheet exists with totals

**PASS:** New summary sheets were created with calculated totals that look correct.

**FAIL:**
- Summary sheets are missing
- Excel cells show "REF!" or "VALUE!" or "ERROR"
- The totals don't add up (e.g., $100 + $200 = $300, but it shows $250)

**If FAIL:** Take a screenshot of the Excel file showing the error or wrong total.

---

## 9. Audit Log Test

Testing the "security camera recording" of the app.

1. Click **Audit Logs** or **Activity Log** in the menu
2. The page should show a list of actions with timestamps
3. Look for these actions from your testing:

   - [ ] **Invoice Upload** action appears
   - [ ] **Invoice Edit** action appears
   - [ ] **Invoice Approval** action appears
   - [ ] **Excel Export** action appears
   - [ ] **Restore** action appears (if you did the restore test)

4. Check that the timestamp matches roughly when you did the action

**PASS:** Every important action you performed is recorded with the correct time.

**FAIL:**
- The audit log is completely empty
- Major actions (like approval) are missing
- The wrong user name is shown (it shows someone else did it)
- The timestamp is completely wrong (shows yesterday or last year)

**If FAIL:** Take a screenshot showing the audit log alongside the actual time.

---

## 10. Backup Test

Testing how your data gets protected.

1. Go to **Admin > Backup** (or **Settings > Backup**)
2. Click **Run Local Backup**
3. Wait for a green success message
4. Look for the file path — note where the backup was saved
5. Click **Test Restore** (this just checks if the backup file is healthy, it does NOT actually restore)
6. Does the page say "Backup is valid" or "Restore test passed"?

- [ ] Backup completed without error
- [ ] A file path is shown
- [ ] Restore test passed

**PASS:** A backup file was created and the health check passed.

**FAIL:**
- Backup fails with an error
- Backup file size shows as 0 bytes
- Restore test says "Backup is corrupted" or fails
- No file path is shown

**If FAIL:** Take a screenshot showing the error message. Note your hard drive space (you may be out of disk space).

---

## 11. Kill Switch Test (CRITICAL)

Testing the "Emergency Stop" button that should stop all automation immediately.

1. Go to **Emergency Safety** or **Safety Center** in the menu
2. Click the red **Stop All Automation** button
3. The screen should show a warning: "Automation is Blocked" or "Kill Switch Active"
4. Now try to do something automated:
   - Go to Invoices and try **Export to Excel**
   - Or try **Browser Automation**
   - Does the app block you with a message?
5. Go back to Safety and click **Resume Automation**
6. Now try Export again — it should work again

- [ ] I clicked Stop All Automation
- [ ] I saw a warning message that automation is blocked
- [ ] Automation was blocked when I tried it
- [ ] Resume Automation worked

**PASS:** The app successfully blocked all automation while the kill switch was on, and resume worked.

**FAIL:**
- You could still export or run automation after clicking Stop All
- The kill switch button does nothing
- Resume does not work (automation stays blocked forever)

**Screenshot to save:** Show the kill switch active message AND demonstrate that automation still runs (this is a critical fail).

> **⚠️ STOP HERE AND FIX: If the kill switch does NOT stop automation, the app is not safe for any user. Do not proceed with testing until this is fixed. Do not demo to anyone.**

---

## 12. Voice Assistant Test (Text Mode)

Testing if you can "talk" to the app using text commands.

1. Find the small **Microphone** button at the bottom-right of the screen — click it
2. A voice/command panel opens
3. In the text box, type: `show pending invoices` and press Enter
4. Does the app show you the pending invoices list or a command preview?
5. Type: `export approved invoices to Excel` and press Enter
6. Does the app ask for your **Approval** before doing it?
7. Type: `delete all invoices` and press Enter
8. Does the app say **"Action Blocked"** or refuse to do it?
9. Type: `send it` or something vague — does the app ask **"What do you mean?"** or show a clarification question?

- [ ] `show pending invoices` worked (showed list or preview)
- [ ] `export approved invoices` asked for approval
- [ ] `delete all invoices` was blocked
- [ ] Vague command asked for clarification

**PASS:** The app understands basic commands, asks approval for risky actions, and blocks dangerous ones.

**FAIL:**
- Commands are ignored or show "I don't understand"
- Risky commands (export, approve) run WITHOUT asking for approval
- Dangerous commands (delete) are NOT blocked
- The voice panel doesn't open at all

**If FAIL:** Take a screenshot showing the command you typed and the response you got.

---

## 13. Microphone Test (Voice Mode)

Testing if the app can hear your actual voice.

1. Open the Voice Assistant (click the microphone button)
2. Click **Push to Talk** or **Start Recording**
3. If Windows asks for microphone permission, click **Allow**
4. Speak clearly into your microphone: `show pending invoices`
5. Click **Stop Recording** or release the button
6. Does your speech appear as text on the screen?

- [ ] Recording started when I clicked Push to Talk
- [ ] Recording stopped when I clicked Stop
- [ ] My speech turned into text
- [ ] The text was correct ("show pending invoices")

**PASS:** The app turned your voice into text correctly.

**FAIL:**
- The app doesn't show a recording indicator (no waveform/mic animation)
- No text appears after you stop recording
- The text says something completely different from what you said
- A message says "Microphone Access Denied"

**If FAIL:** Check Windows settings > Privacy > Microphone — make sure the browser/app has permission. Take a screenshot of the voice panel after recording.

---

## 14. Browser Automation Test

Testing the "safe robot" that fills web forms for you.

1. Go to **Settings > Browser Settings** (or **Browser Automation**)
2. Make sure **Enable Browser Automation** is toggled ON
3. Check that **localhost** or **test form** is in the allowed list
4. Click **Open Test Form** — a new browser tab opens with a dummy form
5. Go back to OfficePilot and select an approved invoice
6. Click **Build Fill-Form Preview** (or **Preview Automation**)
7. A preview panel should show what steps the robot will take
8. Does it show each step (e.g., "Fill Vendor field with 'Acme Corp'")?
9. Click **Approve**
10. Switch to the test form tab — are the fields filled in?

- [ ] Preview showed the steps before execution
- [ ] I had to click Approve before anything happened
- [ ] The form was filled correctly after approval

**PASS:** You saw a preview, gave approval, and the robot filled the form correctly.

**FAIL:**
- The robot filled the form WITHOUT asking for approval (runs immediately)
- A blocked domain (like a banking site) was allowed
- The form fields stayed empty after approval
- No log/record was created of the automation

**If FAIL:** If it ran without approval, take a screenshot showing the automation ran but no approval prompt appeared. This is dangerous.

> **STOP HERE AND FIX**: If browser automation runs without approval, the safety system has a hole. Fix before demoing.

---

## 15. Screen Assistant Test

Testing the assistant that can "see" what's on your screen.

1. Go to **Settings > Screen Assistant** (or **Screen Control**)
2. Toggle **Read-Only Mode** to ON
3. Click **Start Session** or **Start Screen Assistant**
4. Click **Read Current Window** — does the app show the name of the window you have open?
5. Open a safe app like Notepad or a folder window
6. Click **Read Current Window** again — does it show text from that window?
7. Now type the name of a blocked app like "Password Manager Pro" or "Banking App"
8. Does the app say **"Blocked"** or refuse to interact?
9. Go to your invoice detail page and click **Open Invoice Folder**
10. Does the app show a **preview** of what it will do before opening the folder?

- [ ] Read-only mode shows active window correctly
- [ ] Blocked app name was rejected
- [ ] Open folder showed a preview before executing

**PASS:** Read-only mode works, blocked apps are blocked, and actions require preview first.

**FAIL:**
- Unknown apps are allowed without warning
- A blocked app name is NOT blocked
- Actions run immediately without showing a preview first

**If FAIL:** Take a screenshot showing the blocked app being allowed, or the action running without preview.

---

## 16. Workflow Recording Test

Testing the "training" mode where you show the app what to do.

1. Go to **Workflow Recording** in the menu
2. Click **Enable Recording** (if it's off)
3. Click **Start Recording**
4. Go to the **Test Form** page
5. Type "Test" into one of the fields
6. Go back to Workflow Recording
7. Click **Stop Recording**
8. Do you see a list of **Steps** that were recorded (like "User typed 'Test' in field")?
9. Click **Dry Run** — does the app show what WOULD happen without actually doing it?
10. Now click **Step-by-Step Replay**
11. Does it ask for **approval** before each step?

- [ ] Recording created a list of steps
- [ ] Dry Run did NOT perform any real action
- [ ] Step-by-step replay asked for approval

**PASS:** The app recorded your actions, dry-run was safe, and replay asked for approval.

**FAIL:**
- Nothing was recorded (empty steps)
- Dry Run actually performed the actions (typing, clicking) instead of just showing them
- Replay ran all steps without asking for approval

**If FAIL:** Take a screenshot showing the recording panel empty, or the dry run doing real actions.

---

## 17. QuickBooks / Xero Demo Test (SANDBOX ONLY)

**⚠️ CRITICAL WARNING: Only test with Demo/Mock/Sandbox mode. Never use a real QuickBooks or Xero account.**

1. Confirm you are in **Demo Mode** or **Sandbox Mode** (check the banner at the top of the page)
2. Open an **Approved** invoice from the list
3. Look for a button called **Preview QuickBooks Sync** or **Preview Xero Sync** — click it
4. Does a preview popup appear showing the vendor, amount, and account?
5. Check the details — are they correct for this invoice?
6. Click **Approve** (only in sandbox/demo mode)
7. Does the app show a **Validation Result** (like "Sync successful" or "Validation passed")?

- [ ] I am in Demo/Sandbox mode (confirmed by a banner or label)
- [ ] Preview appeared before any sync happened
- [ ] I had to approve before it synced
- [ ] Validation result appeared after sync

**PASS:** You saw a preview, gave approval, and got a validation result — all in safe sandbox mode.

**FAIL:**
- The sync happened WITHOUT preview or approval
- A **payment** option or "Send Money" button appeared (there should be NO payment functionality)
- The preview showed wrong amounts or vendor names

**Critical fail:** If the system synced with a real external account during this test.

**Screenshot to save:** Show the preview popup with the invoice details visible.

> **⚠️ STOP HERE AND FIX: Never test with real accounting data until sandbox/demo tests are 100% passing. If payment options appear, stop testing immediately.**

---

## 18. Feedback and Bug Report Test

Testing how users can talk to you and report problems.

1. Look for a **Feedback** button (usually in the sidebar or bottom bar) — click it
2. Type a simple message like "This app is working well!"
3. Click **Submit**
4. Now go to **Admin > Feedback Inbox** — is your message visible?
5. Go back and click **Report Bug** (or **Bug Report**)
6. Click **Create Bug Package** (uncheck "Include Screenshot" if you don't want one)
7. Wait for the package to be created
8. Click **Download ZIP**
9. Open the ZIP file and look at the text files inside
10. Search for sensitive words like "password", "token", "secret", "api_key"
11. Are they hidden/replaced with `[REDACTED]`?

- [ ] Feedback was submitted and visible in the inbox
- [ ] Bug report ZIP was downloaded
- [ ] Sensitive data (passwords, tokens) is redacted in the ZIP files

**PASS:** Feedback is saved, bug report creates a ZIP, and your secrets are hidden.

**FAIL:**
- Feedback shows an error or disappears after submit
- Bug report creation fails
- ZIP download doesn't work
- The ZIP file contains your actual password, API keys, or tokens in plain text

**If FAIL:** If secrets are exposed in the ZIP, this is a security problem. Save the ZIP file as evidence. Do NOT share it publicly.

> **STOP HERE AND FIX**: If bug reports contain plain-text passwords or tokens, fix before any user has access to the app.

---

## 19. Waitlist / Landing Page Test

Testing the signup page for new users.

1. Open the **Landing Page** in your browser (this may be `http://localhost:8000/landing.html` or the live URL)
2. Find the **Waitlist** form (usually says "Join the Waitlist" or "Get Early Access")
3. Enter a test email (like `test@example.com`)
4. Enter a name and click **Join** or **Submit**
5. Now log in to OfficePilot AI as Admin
6. Go to **Admin > Waitlist** (or **Pilot Waitlist**)
7. Is your test email shown in the list?
8. Click **Export CSV** — does a CSV file download?

- [ ] Waitlist form accepted the email
- [ ] Admin can see the signup in the Waitlist page
- [ ] CSV export works

**PASS:** The waitlist captures signups correctly and admin can view/export them.

**FAIL:**
- The form crashes or shows an error after clicking Submit
- Submitting the same email twice causes a crash (it should show "already signed up")
- The signup does not appear in the Admin list
- CSV export fails or downloads an empty file

**If FAIL:** Take a screenshot showing the form error or the empty admin list.

---

## 20. Final "Pilot Demo" Test

Run this full flow from start to finish — exactly like you would show a customer.

**Run through every step and check each box:**

- [ ] **Step 1:** Open OfficePilot AI and log in
- [ ] **Step 2:** Go to Admin > Demo Center and click **Load Sample Dataset**
- [ ] **Step 3:** Go to Invoices and open a sample invoice
- [ ] **Step 4:** Edit the Vendor Name (add "Test") and click Save
- [ ] **Step 5:** Click **Approve** — status changes to Approved
- [ ] **Step 6:** Go to **Version History** — confirm old and new values appear
- [ ] **Step 7:** Go to **Audit Logs** — confirm upload, edit, and approval are recorded
- [ ] **Step 8:** Go back to Invoices, select the approved invoice, click **Export to Excel**, preview, approve, open the Excel file to confirm it's correct
- [ ] **Step 9:** Click the **Microphone** button, type `show pending invoices`, confirm the app responds
- [ ] **Step 10:** Go to **Emergency Safety**, click **Stop All Automation**, try to export — confirm it's blocked, then click **Resume Automation**
- [ ] **Step 11:** Go to **Admin > Backup**, run a backup, confirm it passes
- [ ] **Step 12:** Click **Feedback**, submit "Demo complete — all tests passed!"
- [ ] **Step 13:** Go to **Admin > Feedback Inbox** and confirm the feedback is there

**PASS:** Every checkbox above is checked. The demo ran without any crashes, errors, or safety failures.

**FAIL:**
- Any step causes the app to crash or freeze
- Demo data doesn't load
- Approval is missing (you could approve without clicking Approve)
- A safety feature (kill switch, approval, audit log) fails silently

**If any step FAILS:** Write down which step number, what happened, and take a screenshot. Do not demo to a customer until all steps pass.

---

## 21. How to Report a Bug

If any test fails, fill out this form for every failed test:

```
Test name: (e.g., "Section 4 - Invoice Upload Test")
What I clicked: (e.g., "I clicked the Upload Invoice button and selected a PDF")
What I expected: (e.g., "I expected the invoice to appear in the list with fields filled in")
What actually happened: (e.g., "The screen showed 'Error 500' and the invoice did not appear")
Screenshot or video saved? (Yes/No — name of file)
Error message on screen: (copy-paste the exact error text)
Can I repeat it? (Yes — happens every time / No — happened only once)
How serious is it? (Low / Medium / High / Critical)
```

**Defense levels:**
- **Low:** Small visual issue (button slightly misaligned, typo in text)
- **Medium:** Feature works but is inconvenient (need to click twice, slow but works)
- **High:** Feature is broken (can't upload, can't approve, can't export)
- **Critical:** Safety feature broken (kill switch fails, approval skipped, secrets exposed, data lost)

---

## 22. Final Testing Summary

**Copy this table and fill it out:**

| Area | Pass/Fail | Notes |
| :--- | :--- | :--- |
| Login / Auth | | |
| Demo Data | | |
| Invoice Upload | | |
| Invoice Review & Approval | | |
| Excel Export | | |
| Excel Summary / Formulas | | |
| Version History / Restore | | |
| Audit Log | | |
| Backup | | |
| Kill Switch | | |
| Voice Assistant (Text) | | |
| Voice Assistant (Microphone) | | |
| Browser Automation | | |
| Screen Assistant | | |
| Workflow Recording | | |
| Accounting Sync (Sandbox) | | |
| Feedback & Bug Reports | | |
| Waitlist / Landing Page | | |
| Final Pilot Demo Flow | | |

**Answer these questions after testing:**

- **Is the product ready for a live demo to a customer?** (Yes/No)
  - Only "Yes" if all safety features (kill switch, approval, audit log, version restore) pass.

- **Is the product ready for a pilot user to try on their own?** (Yes/No)
  - Only "Yes" if every section above passes AND there are no "High" or "Critical" failures.

- **What should be fixed first?**
  - List any "Critical" failures first, then "High" failures. Start with safety features.

- **What is safe to ignore for now?**
  - Small visual bugs (wrong color, misaligned button)
  - "Nice to have" features that aren't core (fancy animations, advanced formatting)
  - Features you won't demo (if you're not showing browser automation, a minor bug there is okay)

**Example of a good summary:**

| Area | Pass/Fail | Notes |
| :--- | :--- | :--- |
| Login / Auth | ✅ PASS | No issues |
| Demo Data | ✅ PASS | Loaded 8 invoices |
| Invoice Upload | ❌ FAIL | PDF upload stuck at "Processing" — see Bug Report #1 |
| Invoice Review & Approval | ✅ PASS | Edit, save, approve all work |
| ... | ... | ... |

**Ready for demo?** No — Invoice upload is broken, can't demo without it.
**Ready for pilot?** No — same reason.
**Fix first:** PDF invoice upload processing.
**Safe to ignore:** Slight color difference in the sidebar.

---

**End of Testing Guide**

Good luck with your testing! Start with Section 1 and work your way through. Take your time. Better to find bugs now than during a customer demo.
