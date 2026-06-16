# Complete Testing Process

OfficePilot AI maintains a rigorous testing standard. No feature is considered complete until it passes both automated and manual verification.

## 1. Testing Philosophy
- **Phase-Based**: Every development phase has a dedicated test file in `backend/tests`.
- **Regression-First**: We run the entire suite before every release to ensure new features don't break old ones.
- **Safety-Critical**: Any feature that moves files, syncs data, or controls the screen must be manually verified even if automated tests pass.

## 2. Current Test Status (Phase 22.7)
- **Backend Tests**: 553+ passing (Pytest).
- **Frontend Tests**: 94+ passing (Vitest).

---

## 3. Automated Backend Tests
Run all tests:
```powershell
cd backend
$env:PYTHONPATH = "."
python -m pytest
```

Run specific phase or module:
```powershell
# Accounting
python -m pytest tests/test_accounting.py -v

# Voice assistant (Phase 22.7)
python -m pytest tests/test_voice_22_7.py -v

# Workflow Orchestration
python -m pytest tests/test_workflows.py -v
```

---

## 4. Automated Frontend Tests
```powershell
cd frontend
npm test -- --run
```

Test specific components:
```powershell
npm test -- --run -t "VoiceCommandModal"
npm test -- --run -t "AccountingSync"
```

---

## 5. Manual End-to-End Checklist

### A. Authentication & Roles
- [ ] Register a new user (becomes Owner).
- [ ] Register second user (becomes Staff).
- [ ] Verify Staff cannot access "Safety Policies."
- [ ] Verify JWT token persists after page refresh.

### B. Invoice Lifecycle
- [ ] Upload a clear PDF invoice.
- [ ] Verify OCR extracts Vendor, Date, and Amount correctly.
- [ ] Edit a field and verify "Version History" captures the change.
- [ ] Approve the invoice.

### C. Excel & Snapshots
- [ ] Export approved invoices to a new Excel file.
- [ ] Open the file and verify data alignment.
- [ ] Use "Restore Snapshot" and verify the file reverts to its previous state.

### D. QuickBooks / Xero Sync
- [ ] Connect to a sandbox/mock provider.
- [ ] Preview a sync for an approved invoice.
- [ ] Approve Sync and verify "Draft Created" status.
- [ ] Verify sync logs are written to the database.

### E. Voice Assistant
- [ ] Toggle "Demo Mode" and say "Show pending invoices."
- [ ] Verify the Review Queue opens automatically.
- [ ] Type "delete all files" and verify it is **Blocked**.
- [ ] Say "Send it" and verify the **Clarification Flow** asks for detail.

### F. Safety & Kill Switch
- [ ] Start a browser automation task.
- [ ] Toggle the **Kill Switch** in the header.
- [ ] Verify the automation stops immediately and refuses to resume.

---

## 6. Build & Packaging Verification
1. **Sidecar Build**:
   ```powershell
   .\scripts\build_sidecar_windows.ps1
   ```
   - Verify `dist/officepilot_sidecar.exe` is created.
2. **Tauri Build**:
   ```powershell
   cd desktop/tauri
   npm run tauri build
   ```
   - Verify the `.msi` or `.exe` installer is generated.

---

## 7. Clean Windows QA
Before a release, the app must be tested on a machine **without** Python or Node installed:
- [ ] Sidecar starts automatically on port 8767.
- [ ] All bundled dependencies (OCR, Playwright) function correctly.
- [ ] Data persists in `AppData/Roaming/OfficePilot`.

---

## 8. Common Troubleshooting in Testing
- **"ModuleNotFoundError"**: Ensure `PYTHONPATH` is set to the backend root.
- **"Database Locked"**: Ensure only one instance of the backend is running.
- **"Port 8767 in Use"**: Kill any stray `python.exe` or `officepilot_sidecar.exe` processes.
- **"Microphone Permission"**: Ensure the browser/system allows mic access to `localhost`.
