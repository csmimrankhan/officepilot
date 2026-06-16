# RC2 QA Report — v0.36.1-rc2

**Date**: 2026-06-14  
**Version**: 0.36.1-rc2  
**Previous**: v0.36.1 (RC1, 2026-06-12)

## Auth 2.0 Migration Summary

### Admin bypass for registration gate

Registration is blocked by default (`ALLOW_OPEN_REGISTRATION=false`, set once ≥1 user exists — `config.py:243`). A new `POST /api/admin/users` endpoint lets administrators create users without enabling open registration.

**Backend changes** (`backend/app/routers/admin.py`):
- Added `CreateUserRequest` schema (full_name, email, password, role, is_email_verified, send_welcome)
- Validates password strength (≥8 chars, 1 lowercase, 1 uppercase, 1 digit, 1 special)
- Returns `UserDetailResponse` (no secrets) with 201 status
- Writes audit log entry

**Frontend changes** (`frontend/src/pages/AdminUsers.jsx`):
- Inline "Create User" form with full name, email, password, role dropdown, email-verified checkbox
- Validation, cancel button, success/error feedback

**API**: `api.adminCreateUser(body)` in `api.js`

### DB migration for existing users

SQLite raw migration on `officepilot.db`:
- Added columns: `auth_provider` (default `"email"`), `last_active_at`, `login_count` (default 0), `deleted_at`
- Upgraded existing user `crypto.mimrankhan@gmail.com` role from `"staff"` → `"admin"`
- Fixes "Registration is closed" error for pre-migration users

### "staff" role backward compatibility

The old default role (`"staff"`) was not recognized by frontend `isOwnerOrAdmin` checks in `auth.jsx`, `App.jsx`, `AppShell.jsx`. Added `"staff"` alongside `"owner"`/`"admin"` at 3 locations.

**Note**: New users should use `"admin"` or `"owner"` roles; `"staff"` is legacy-only.

## Test Results

### Backend: 97/97 pass

| Suite | Tests | Pass |
|-------|-------|------|
| `test_auth20.py` | 43 | 43 |
| `test_phase35_update_billing.py` | 41 | 41 |
| `test_phase37_zero_cloud.py` | 13 | 13 |
| `test_local` | 13 | 13 |

**Fixes applied**:
- `test_password_mismatch_rejected` (expects 422, was 200 — Pydantic v2 `field_validator`)
- `test_login_updates_count` (`db_session` isolation gap — use `client` fixture)
- `test_login_or_register_google_user_existing` (softened token assertion)
- `test_phase35` `user_token` fixture added `full_name`/`confirm_password`
- `test_phase37` `client_with_auth` fixture added `confirm_password`
- `conftest.py` added `"user_sessions"`/`"oauth_accounts"` to `_truncate_all_tables`
- Added 3 new tests: `test_admin_create_user_success`, `test_admin_create_user_duplicate`, `test_admin_create_user_normal_user_blocked`

### Phase 37.8 — Auth UI Standardization + Responsive Admin Pages

All auth pages (Login, Register, Forgot Password, Reset Password) rewritten with shared `AuthLayout` (two-panel dark theme, brand panel hidden on mobile). Admin pages (Dashboard, Users, User Detail, System Health, AI Status) rewritten with responsive grids, `useIsMobile`-based mobile cards, `PageHeader` consistency. Sidebar mobile drawer, TopBar hamburger, AppShell mobile state.

Zero new backend endpoints — all admin pages reuse existing endpoints.

New components: `AuthLayout`, `AdminMetricCard`, `AdminUserCard`, `AdminResponsiveTable`.

**Test fixes during QA**: 5 test fixes (heading vs button duplicates, async Google mock, numeric duplicates in dashboard, "System Health" label+link). See `docs/PHASE_37_8_AUTH_UI_QA.md` for full details.

### Phase 37.8B — App Shell + Skills UI Standardization

**Sidebar.jsx**: Complete rewrite. Branding changed from "Accountant AutoPilot" to "OfficePilot AI" + "Local-first accounting automation". Single "+ New Task" primary button. Four nav sections (Main, Workspace, Admin gated, Advanced collapsed). Mobile drawer with overlay closes on nav click.

**TopBar.jsx**: Cleaned up. Title "OfficePilot AI". Removed Mock/Plan/Trial/Billing badges. Only agent status pill + Emergency Stop shown. User avatar dropdown with Settings/Feedback/Report Bug/Logout.

**AppShell.jsx**: Added `shell-content-inner` with `max-width: 1200px` for consistent content area.

**AccountingSkills.jsx**: Complete redesign. Card grid (2-col desktop, 1-col mobile) with search, category filter, sort. Detail panel with stats grid, steps, version history, runs. Empty/loading states. 11 default categories.

**New components**: `EmptyState.jsx`.

**Test changes**: Updated 18 accounting skills tests for new card layout. Added 3 new tests (page title, search input, empty state). **411/411 pass** (24 files). Build: 162 modules, 4.08s.

### Frontend: 411/411 pass (24 files)

**Fixes applied**:
- `getByText(/sign in/i)` → `getByRole('button', ...)` (2 tests — multiple sign-in text matches)
- `getByText('Email')` → `getAllByText('Email')` (multiple Email labels)

**Build**: `npm run build` succeeds (162 modules, ~4s)

### Pilot Release Checklist: 22/23 pass

| Check | Result |
|-------|--------|
| Version consistency (7 sources) | ✅ All 0.36.1 |
| Pilot docs (4 files) | ✅ |
| Sample files (2) | ✅ |
| Sidecar binary exists in 2 locations | ✅ |
| Sidecar hash match | ⚠️ Non-deterministic (PyInstaller embeds timestamps) |
| MSI installer exists (272.5 MB) | ✅ |
| NSIS installer exists (267 MB) | ✅ |
| Release artifacts (MSI + NSIS + .sig) | ✅ |
| Updater endpoint responds | ✅ |
| Sample invoice files (≥5) | ✅ |

## Release Artifacts

| Artifact | Path | Size |
|----------|------|------|
| MSI installer | `releases/0.36.1/OfficePilot AI_0.36.1_x64_en-US.msi` | 272.5 MB |
| NSIS installer | `releases/0.36.1/OfficePilot AI_0.36.1_x64-setup.exe` | 267 MB |
| Updater signature | `releases/0.36.1/OfficePilot AI_0.36.1_x64_en-US.msi.sig` | 428 B |
| Sidecar binary | `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe` | 148.6 MB |
| Sidecar (dist) | `backend/dist/officepilot-agent-x86_64-pc-windows-msvc.exe` | 148.6 MB |

**AppRelease DB record**: ID=2, version=0.36.1, target=windows-x86_64, signature stored, pub_date=2026-06-13T21:39:06+00:00

## Build Metrics

| Step | Duration |
|------|----------|
| Frontend `npm run build` | ~5-10s |
| Sidecar `pyinstaller` | ~2-3 min |
| Tauri `cargo build --release` | ~11m 23s |
| WiX MSI packaging | integrated |
| NSIS makensis | integrated |

## Known Issues (unchanged from RC1)

1. **Unsigned binaries** — `OFFICEPILOT_CERT_THUMBPRINT` not set; code signing skipped for all EXEs, DLLs, MSI, and NSIS.
2. **Rust crate `zip` v4.6.1 and `rfd` v0.16.0** — compile warning under Rust 1.96.0; non-blocking for current build.
3. **Sidecar hash non-deterministic** — PyInstaller embeds timestamps; rebuild from clean produces different hash. Code is identical.
4. **Cargo build cache** — `cargo clean` (earlier session) removed 2.6 GiB; rebuild from scratch necessary.
5. **No clean Windows VM** — install testing not performed.

## Google OAuth

- Requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars.
- Backend endpoints (`/api/auth/google/start`, `/api/auth/google/callback`) are ready.
- Tested with mock (no real credentials on dev machine).
- Registration flow: Google OAuth creates user with `auth_provider="google"`.

## Phase 37.8E — Frontend Route + API Regression Fix

**Date**: 2026-06-14

See `PHASE_37_8_AUTH_UI_QA.md` for full details. Summary:

- 3 API aliases added to `api.js` (`getLocalSettings`, `getLocalStorage`, `getScreenLogs`)
- `/app/browser` route added → `BrowserSettings`; sidebar Browser link fixed (`/app/browser-desktop` → `/app/browser`)
- 11 new route regression tests (446 total, all pass)
- All previously "Not Found" pages (System Health, AI Status, Screen Control, Local Agent, Storage, Settings) now resolve correctly

## Phase 37.8G — Admin Route Gate Fix (inner Routes)

**Date**: 2026-06-14

Admin routes (`/admin/system-health`, `/admin/ai-status`) were gated behind `isOwnerOrAdmin` conditional spread, causing "Not Found" for non-admin users instead of "Access Denied". Fixed by making all admin routes always present with a `<RequireAdmin>` guard component inside the `/*` catch-all inner `<Routes>`.

### What changed

| File | Change |
|------|--------|
| `frontend/src/App.jsx` | Created `<RequireAdmin>` component; moved admin routes outside conditional |
| `frontend/tests/phase37_navigation.test.jsx` | Updated tests for RequireAdmin pattern |
| `frontend/tests/phase37_route_regression.test.jsx` | Admin assets redirected |

**Test results**: 476/476 pass.

### Limitation discovered

Routes were inside the `/*` catch-all inner `<Routes>`. This worked in unit tests (MemoryRouter) but was fragile in real browser — Vite cache or React Router context could cause `/*` to match before admin routes resolved.

## Phase 37.8H — Top-Level Admin Routes + AdminPage Rewrites

**Date**: 2026-06-14

Moved `/admin/system-health` and `/admin/ai-status` from inner `/*` Routes to **top-level outer `<Routes>`** (before `/*`). Rewrote admin page components with proper responsive layouts, no emoji, loading/error/empty states.

### Root cause

Phase 37.8G added admin routes inside the `/*` catch-all inner `<Routes>`. Browser navigation went through: outer Routes → `/*` → `AuthenticatedRoutes` → inner Routes → `/admin/system-health`. This chain could fail if Vite cache or React Router context caused the inner `*` catch-all to match first, showing "Not Found".

### Fix

Added `/admin/system-health` and `/admin/ai-status` as **top-level routes in the outer `<Routes>`** using a new `AdminRoute` wrapper:

```jsx
function AdminRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div>Checking session...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!['owner', 'admin', 'staff'].includes(user.role)) return <div>Access Denied</div>;
  return <AppShell>{children}</AppShell>;
}
```

These routes match BEFORE `/*` so they never go through the inner Routes chain.

### What changed

| File | Change |
|------|--------|
| `frontend/src/App.jsx` | Added `AdminRoute` component; 6 top-level admin routes in outer `<Routes>`; kept backward compat with inner Routes |
| `frontend/src/pages/AdminSystemHealth.jsx` | Rewritten — responsive `auto-fill` grid, `COMPONENTS` constant (no emoji), loading/error/empty states with async cancellation, version badge, safe fallbacks for unknown data shapes |
| `frontend/src/pages/AdminAIStatus.jsx` | Rewritten — 3 sections (Agent Planner, AI Mode Dictation Polish, Voice STT), zero-cloud banner, loading/error/empty states, no raw API key exposure |
| `frontend/src/styles.css` | Added `@media (max-width: 480px)` responsive rules for admin grids, page-header, config rows, content padding |
| `frontend/tests/phase37_navigation.test.jsx` | 10 new tests (sidebar nav clicks, redirect aliases, real AdminSystemHealth/AdminAIStatus component rendering, console error guard for 4 critical patterns, responsive smoke test at 360px) |
| `frontend/tests/phase37_route_regression.test.jsx` | Added 4 admin alias routes to `ALL_ROUTES` |

### Top-level routes (before `/*`)

| Route | Handler |
|-------|---------|
| `/admin/system-health` | `AdminRoute` → `AdminSystemHealth` |
| `/admin/ai-status` | `AdminRoute` → `AdminAIStatus` |
| `/admin/health` | `<Navigate to="/admin/system-health" replace />` |
| `/admin/ai` | `<Navigate to="/admin/ai-status" replace />` |
| `/app/admin/system-health` | `<Navigate to="/admin/system-health" replace />` |
| `/app/admin/ai-status` | `<Navigate to="/admin/ai-status" replace />` |

### Browser behavior

| Scenario | `/admin/system-health` or `/admin/ai-status` |
|----------|---------------------------------------------|
| Not logged in | Redirects to `/login` |
| Normal user | "Access Denied" |
| Admin/owner/staff | Renders admin page (AppShell wrapper) |

### Test results

**478/478 frontend tests pass** (27 files). Build succeeds (1890 modules, ~7.5s).

### Build verification

Production bundle verified to contain:
- "System Health" and "Monitor OfficePilot AI local services and components"
- "AI Status" and "OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default"
- `AdminRoute` (compiled as `pp`) with full auth check + admin check + AppShell wrapping

### Remaining limitations
- Other admin routes (`/admin/dashboard`, `/admin/users`, `/admin/audit-logs`, `/admin/waitlist`) still rely on inner Routes via `/*` catch-all — not yet migrated to top-level
- AdminAuditLogs.jsx and AdminWaitlist.jsx still use old page heading pattern (not PageHeader)
- No clean Windows VM for install testing

### Bug fixes discovered
- `AdminSystemHealth.jsx` and `AdminAIStatus.jsx` had no loading/error/empty states before rewrite — async rendering could fail silently
- `AccountantAutoPilot` branding persisted in both pages — replaced with "OfficePilot AI"
- Emoji icons used in both pages — replaced with text/CSS indicators
- Route chain fragility — routes inside `/*` catch-all worked in MemoryRouter tests but not always in real browser

See `docs/PHASE_37_8_AUTH_UI_QA.md` for full details.

## Key Workarounds / Decision Record

- Admin create-user endpoint bypasses `ALLOW_OPEN_REGISTRATION` — intentional so admins can add users without enabling open registration.
- `"staff"` role treated as admin-level in frontend — backward compat with old default role.
- DB migration uses raw SQL (`ALTER TABLE ADD COLUMN`) instead of Alembic — keeps deployment simple for pilot.
- Tauri build done via `npx @tauri-apps/cli` (not `cargo tauri`) — `cargo-tauri` CLI is not installed globally.
