# Phase 39 — Background Daemon, Drive Integration, Planner Wiring & Frontend UX

## Manual QA Checklist

### Task 1 — Background Task Runner

1. Open the OfficePilot app and navigate to the Accountant Agent chat.
2. Type a plan that will succeed (e.g., "analyze this dataset") and approve it.
3. Verify the plan runs step-by-step and completes normally.

### Task 2 — Background Tasks via API

1. Create a background task directly via the API:
   ```bash
   curl -X POST http://localhost:8000/api/agent/run-background \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"command": "test analysis", "plan_json": "{\"steps\":[{\"tool\":\"analyze_invoice_dataset\",\"params\":{\"invoices_data\":[{\"vendor\":\"Test\",\"total_amount\":100}]}}]}"}'
   ```
2. Verify `GET /api/agent/background-tasks` returns the task with status "completed".
3. Verify `GET /api/agent/background-tasks/{id}` returns the detail with `result_summary_json`.

### Task 3 — Google Drive Read-Only Safety Gate

1. In the agent chat, type "upload invoice to google drive".
2. Verify the plan is blocked with "Google Drive write operations are not supported" message.
3. Type "list files from google drive".
4. Verify the Drive→Download→Analyze→Excel chain plan is generated.

### Task 4 — Background Task Frontend UX

1. Open the app and verify the TopBar shows no background icon initially.
2. Start a background plan from the chat.
3. Verify the TopBar shows the pulsing Loader icon with a count badge.
4. Click the icon — verify the dropdown shows the task with progress bar and Cancel button.
5. Click Cancel — verify the task disappears from active tasks.
6. Run another background task and wait for it to complete.
7. Verify a `BackgroundResultCard` appears in the chat timeline showing the summary.

### Task 5 — OS Notifications

1. Run a background task from the chat (e.g., "analyze this dataset in background").
2. Minimize the app window.
3. Wait for the task to complete.
4. **Verify**: A Windows toast notification appears with title "OfficePilot Task Complete" and body like "Processed 12 invoices. Biggest: $3,200.00. Click to view."
5. Click the notification — verify the app window comes to focus and the result card is visible.
6. Run a failing background task (e.g., with invalid data).
7. **Verify**: A failure notification appears with the error message.

### Task 6 — Load Completed Tasks on App Start

1. Close and reopen the app.
2. **Verify**: Any background tasks that completed while the app was closed appear as `BackgroundResultCard` entries in the chat timeline.

### Regression Tests

| Suite | Command | Expected |
|-------|---------|----------|
| Backend tests | `cd backend && python -m pytest tests/test_phase39_background.py tests/test_phase39_drive.py tests/test_phase39_planner.py -v -n 0` | 66 passed |
| Frontend tests | `cd frontend && npm test -- --run` | 536+ passed (30 files) |

### Environment Check

- The `@tauri-apps/plugin-notification` npm package must be installed (v2.x).
- Tauri capabilities must include `notification:default`, `notification:allow-is-permission-granted`, `notification:allow-request-permission`, `notification:allow-notify`.
- When running in web mode (no Tauri), the Web Notification API is used as fallback. Chrome/Edge/Firefox must allow notifications.
