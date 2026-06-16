import '@testing-library/jest-dom/vitest'

// Phase 8 — the Local Agent page now talks to the Tauri bridge.
// In jsdom we have no Tauri shell, so the bridge falls back to
// the no-op stub. No additional global is required, but we
// guarantee ``window.__TAURI__`` is undefined so the
// ``isTauriContext()`` check returns false.
