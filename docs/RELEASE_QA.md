# OfficePilot AI — Release QA Checklist

**Version:** 0.36.1 | **Phase:** 37 (Stability Freeze)

---

## Pre-Release Checklist

### 1. Version Consistency
- [ ] `backend/app/__init__.py` — 0.36.1
- [ ] `backend/app/config.py` — `app_version = "0.36.1"`
- [ ] `backend/app/main.py` — `version = "0.36.1"`
- [ ] `frontend/package.json` — 0.36.1
- [ ] `desktop/tauri/src-tauri/tauri.conf.json` — 0.36.1
- [ ] `desktop/tauri/src-tauri/Cargo.toml` — 0.36.1

### 2. Test Status
- [ ] Backend Phase 35 update/billing tests: **16 pass**
- [ ] Backend Phase 37 zero-cloud tests: **25 pass**
- [ ] Backend full regression (excluding timeouts): **pass**
- [ ] Frontend Phase 35 update/billing tests: **7 pass**
- [ ] Frontend full regression: **377 pass, 2 pre-existing (Tauri runtime)**
- [ ] Frontend build: **success**

### 3. Zero-Cloud-by-Default Verification
- [ ] `AGENT_PROVIDER=mock` — verified by tests
- [ ] No API keys configured by default — verified by tests
- [ ] Cloud planner blocked when disabled — verified by tests
- [ ] AI mode polish skipped when disabled — verified by tests
- [ ] Voice cloud STT skipped when disabled — verified by tests
- [ ] Local/mock fallback always works — verified by tests
- [ ] Admin AI Status page shows zero-cloud message — verified
- [ ] Admin AI Status page never exposes raw keys — verified

### 4. Admin Pages
- [ ] System Health page shows all 10 components
- [ ] AI Status page shows all 3 sections
- [ ] Sidebar links present for admin users
- [ ] Routes gated by `isOwnerOrAdmin`

### 5. Documentation
- [ ] `KNOWN_LIMITATIONS.md` updated with stability freeze items
- [ ] `ADMIN_GUIDE.md` created
- [ ] `RELEASE_QA.md` created

---

## Known Pre-existing Failures

| Test | Reason | Status |
|------|--------|--------|
| Frontend `UpdateBanner` (2 tests) | Requires Tauri runtime (jsdom limitation) | Skipped — non-blocking |
| Backend full suite timeout | 1100+ tests take ~9 min | Non-blocking — individual module tests pass |

---

## QA Pass Criteria

1. **All backend module tests pass** — ✅ (16 Phase 35 + 25 Phase 37)
2. **All frontend tests pass except known Tauri-gated tests** — ✅ (377/379)
3. **Default build makes zero cloud/LLM calls** — ✅ (all env vars default to mock/disabled)
4. **Admin can see system health** — ✅ (new endpoint + page)
5. **Admin can see AI status** — ✅ (new endpoint + page)
6. **API keys never exposed in UI** — ✅ (boolean flags only)
7. **No feature changes to Excel, Gmail, Browser, Workflow Recorder, Updater** — ✅ (bug fixes only)

---

## Post-Release Verification

1. Launch the app without any `.env` file
2. Verify Agent status shows "mock" in the AI Status page
3. Verify all 10 component statuses show in System Health
4. Run a task: "read this screen" — should return a plan without any network call
5. Verify no outbound connections to AI providers
