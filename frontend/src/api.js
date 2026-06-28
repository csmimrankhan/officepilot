/**
 * Tiny API client for the OfficePilot AI Phase 1 backend.
 * All requests are JSON-friendly; uploads use FormData.
 */

const API_BASE = import.meta.env.VITE_API_BASE || ''

let _authToken = null

export function setAuthToken(token) {
  _authToken = token
}

function authHeaders() {
  if (_authToken) {
    return { 'Authorization': `Bearer ${_authToken}` }
  }
  return {}
}

async function handle(res) {
  if (res.ok) {
    if (res.status === 204) return null
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) return res.json()
    return res
  }
  let detail = `HTTP ${res.status}`
  try {
    const data = await res.json()
    detail = data.detail || JSON.stringify(data)
  } catch (_) {
    try { detail = await res.text() } catch (_) {}
  }
  const err = new Error(detail)
  err.status = res.status
  throw err
}

function _fetch(url, options = {}) {
  const auth = authHeaders()
  const hasAuth = Object.keys(auth).length > 0
  const hasOptHeaders = options.headers && Object.keys(options.headers).length > 0
  if (hasAuth || hasOptHeaders) {
    return fetch(url, { ...options, headers: { ...auth, ...options.headers } })
  }
  return fetch(url, options)
}

function _fetchJson(url, method = 'GET', body = undefined) {
  const headers = { ...authHeaders(), 'Content-Type': 'application/json' }
  const opts = { method, headers }
  if (body !== undefined) opts.body = JSON.stringify(body)
  return fetch(url, opts).then(handle)
}

export const api = {
  base: API_BASE,

  setAuthToken(token) {
    _authToken = token
  },

  // ── Auth 2.0: Authentication + OAuth ───────────────────────────────
  login(body) {
    return _fetchJson(`${API_BASE}/api/auth/login`, 'POST', body)
  },
  register(body) {
    return _fetchJson(`${API_BASE}/api/auth/register`, 'POST', body)
  },
  refreshToken(body) {
    return _fetchJson(`${API_BASE}/api/auth/refresh`, 'POST', body)
  },
  logout(refresh_token) {
    return _fetchJson(`${API_BASE}/api/auth/logout`, 'POST', { refresh_token })
  },
  getMe() {
    return _fetchJson(`${API_BASE}/api/auth/me`)
  },
  verifyEmail(token) {
    return _fetchJson(`${API_BASE}/api/auth/verify-email`, 'POST', { token })
  },
  resendVerification(email) {
    return _fetchJson(`${API_BASE}/api/auth/resend-verification`, 'POST', { email })
  },
  forgotPassword(email) {
    return _fetchJson(`${API_BASE}/api/auth/forgot-password`, 'POST', { email })
  },
  resetPassword(token, new_password) {
    return _fetchJson(`${API_BASE}/api/auth/reset-password`, 'POST', { token, new_password })
  },
  changePassword(current_password, new_password) {
    return _fetchJson(`${API_BASE}/api/auth/change-password`, 'POST', { current_password, new_password })
  },
  googleAuthStart() {
    return _fetchJson(`${API_BASE}/api/auth/google/start`)
  },
  googleAuthCallback(code, state) {
    return _fetchJson(`${API_BASE}/api/auth/google/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`)
  },
  adminListUsers(page = 1, page_size = 20, search = '', role = '', status = '', auth_provider = '') {
    const params = new URLSearchParams({ page, page_size })
    if (search) params.set('search', search)
    if (role) params.set('role', role)
    if (status) params.set('status', status)
    if (auth_provider) params.set('auth_provider', auth_provider)
    return _fetchJson(`${API_BASE}/api/admin/users?${params}`)
  },
  adminGetUser(user_id) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}`)
  },
  adminCreateUser(body) {
    return _fetchJson(`${API_BASE}/api/admin/users`, 'POST', body)
  },
  adminUpdateUser(user_id, body) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}`, 'PATCH', body)
  },
  adminSuspendUser(user_id) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}/suspend`, 'POST')
  },
  adminActivateUser(user_id) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}/activate`, 'POST')
  },
  adminForceLogout(user_id) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}/force-logout`, 'POST')
  },
  adminResetPasswordLink(user_id) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}/reset-password-link`, 'POST')
  },
  adminUserAudit(user_id, page = 1, page_size = 50) {
    return _fetchJson(`${API_BASE}/api/admin/users/${user_id}/audit?page=${page}&page_size=${page_size}`)
  },
  adminListAuditLogs(page = 1, page_size = 50, action = '') {
    const params = new URLSearchParams({ page, page_size })
    if (action) params.set('action', action)
    return _fetchJson(`${API_BASE}/api/admin/audit-logs?${params}`)
  },
  getAdminSystemHealth() {
    return _fetchJson(`${API_BASE}/api/admin/system-health`)
  },
  getAdminAIStatus() {
    return _fetchJson(`${API_BASE}/api/admin/ai-status`)
  },

  health() {
    return _fetch(`${API_BASE}/api/health`).then(handle)
  },

  listInvoices({ status, limit = 100, offset = 0 } = {}) {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    params.set('offset', String(offset))
    return _fetch(`${API_BASE}/api/invoices?${params}`).then(handle)
  },

  getInvoice(id) {
    return _fetch(`${API_BASE}/api/invoices/${id}`).then(handle)
  },

  uploadInvoice(file, actor = 'user') {
    const fd = new FormData()
    fd.append('file', file)
    return _fetch(`${API_BASE}/api/invoices/upload?actor=${encodeURIComponent(actor)}`, {
      method: 'POST',
      body: fd
    }).then(handle)
  },

  updateInvoice(id, patch, actor = 'user') {
    return _fetch(`${API_BASE}/api/invoices/${id}?actor=${encodeURIComponent(actor)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    }).then(handle)
  },

  approveInvoice(id, actor = 'user') {
    return _fetch(`${API_BASE}/api/invoices/${id}/approve?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },

  rejectInvoice(id, reason, actor = 'user') {
    const url = `${API_BASE}/api/invoices/${id}/reject?actor=${encodeURIComponent(actor)}` +
      (reason ? `&reason=${encodeURIComponent(reason)}` : '')
    return fetch(url, { method: 'POST' }).then(handle)
  },

  // ---- Phase 3: trust layer ----
  markDuplicate(id, duplicateOf, actor = 'user') {
    const url = `${API_BASE}/api/invoices/${id}/mark-duplicate` +
      `?duplicate_of=${encodeURIComponent(duplicateOf)}` +
      `&actor=${encodeURIComponent(actor)}`
    return fetch(url, { method: 'POST' }).then(handle)
  },

  organizeFile(id, actor = 'user') {
    return _fetch(`${API_BASE}/api/invoices/${id}/organize-file?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },

  invoiceAuditTimeline(id, limit = 200) {
    return _fetch(`${API_BASE}/api/invoices/${id}/audit?limit=${limit}`).then(handle)
  },

  reviewQueue(limitPerStatus = 50) {
    return _fetch(`${API_BASE}/api/invoices/review-queue?limit_per_status=${limitPerStatus}`).then(handle)
  },

  getFolderRules() {
    return _fetch(`${API_BASE}/api/settings/folder-rules`).then(handle)
  },

  updateFolderRules(patch, actor = 'user') {
    return _fetch(`${API_BASE}/api/settings/folder-rules?actor=${encodeURIComponent(actor)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    }).then(handle)
  },

  folderRulesAudit(limit = 50) {
    return _fetch(`${API_BASE}/api/settings/folder-rules/audit?limit=${limit}`).then(handle)
  },

  exportExcelUrl() {
    return `${API_BASE}/api/invoices/export/excel?actor=user`
  },

  fileUrl(id) {
    return `${API_BASE}/api/invoices/${id}/file?inline=true`
  },

  fileDownloadUrl(id) {
    return `${API_BASE}/api/invoices/${id}/file?inline=false`
  },

  listAuditLogs({ action, entity_type, entity_id, limit = 200 } = {}) {
    const params = new URLSearchParams()
    if (action) params.set('action', action)
    if (entity_type) params.set('entity_type', entity_type)
    if (entity_id != null) params.set('entity_id', String(entity_id))
    params.set('limit', String(limit))
    return _fetch(`${API_BASE}/api/audit-logs?${params}`).then(handle)
  },

  // ---- Phase 2: Gmail integration ----
  gmailStatus() {
    return _fetch(`${API_BASE}/api/integrations/gmail/status`).then(handle)
  },
  gmailConnect() {
    return _fetch(`${API_BASE}/api/integrations/gmail/connect`).then(handle)
  },
  gmailSync(actor = 'user') {
    return _fetch(`${API_BASE}/api/integrations/gmail/sync-invoices?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },
  gmailDisconnect(actor = 'user') {
    return _fetch(`${API_BASE}/api/integrations/gmail/disconnect?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },

  // ---- Phase 34: Email Automation (Gmail Read-Only) ----
  emailListAccounts() {
    return _fetchJson(`${API_BASE}/api/email/accounts`)
  },
  emailSearch(params = {}) {
    return _fetchJson(`${API_BASE}/api/email/search`, 'POST', params)
  },
  emailPreview(params = {}) {
    return _fetchJson(`${API_BASE}/api/email/preview`, 'POST', params)
  },
  emailAttachmentsPreview(params = {}) {
    return _fetchJson(`${API_BASE}/api/email/attachments/preview`, 'POST', params)
  },
  emailDownloadAttachment(params = {}) {
    return _fetchJson(`${API_BASE}/api/email/attachments/download`, 'POST', params)
  },
  emailBatchDownload(params = {}) {
    return _fetchJson(`${API_BASE}/api/email/batch-download`, 'POST', params)
  },

  listEmailImports({ account_id, status, limit = 100, offset = 0 } = {}) {
    const params = new URLSearchParams()
    if (account_id != null) params.set('account_id', String(account_id))
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    params.set('offset', String(offset))
    return _fetch(`${API_BASE}/api/email-imports?${params}`).then(handle)
  },
  getEmailImport(id) {
    return _fetch(`${API_BASE}/api/email-imports/${id}`).then(handle)
  },

  // ---- Phase 5: parser benchmark ----
  listParserEngines() {
    return _fetch(`${API_BASE}/api/parser/engines`).then(handle)
  },

  async runParserBenchmark({ engines, format = 'json' } = {}) {
    const params = new URLSearchParams()
    if (engines && engines.length) params.set('engines', engines.join(','))
    params.set('format', format)
    const res = await fetch(`${API_BASE}/api/parser/benchmark?${params}`)
    if (format === 'csv') {
      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try { detail = await res.text() } catch (_) {}
        const err = new Error(detail); err.status = res.status; throw err
      }
      return res.text()
    }
    return handle(res)
  },

  // ---- Phase 6: LangGraph workflows ----
  listWorkflowGraphs() {
    return _fetch(`${API_BASE}/api/workflows/graphs`).then(handle)
  },

  startWorkflow(name, input = {}, actor = 'user') {
    return _fetch(`${API_BASE}/api/workflows/run/${encodeURIComponent(name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input, actor })
    }).then(handle)
  },

  listWorkflowRuns({ workflow_name, status, limit = 50 } = {}) {
    const params = new URLSearchParams()
    if (workflow_name) params.set('workflow_name', workflow_name)
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    return _fetch(`${API_BASE}/api/workflows/runs?${params}`).then(handle)
  },

  getWorkflowRun(id) {
    return _fetch(`${API_BASE}/api/workflows/runs/${id}`).then(handle)
  },

  listWorkflowApprovals(runId) {
    return _fetch(`${API_BASE}/api/workflows/runs/${runId}/approvals`).then(handle)
  },

  approveWorkflowRun(id, actor = 'user', note = '') {
    return _fetch(`${API_BASE}/api/workflows/runs/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, note: note || null })
    }).then(handle)
  },

  rejectWorkflowRun(id, actor = 'user', note = '') {
    return _fetch(`${API_BASE}/api/workflows/runs/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, note: note || null })
    }).then(handle)
  },

  cancelWorkflowRun(id, actor = 'user', note = '') {
    return _fetch(`${API_BASE}/api/workflows/runs/${id}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, note: note || null })
    }).then(handle)
  },

  retryWorkflowRun(id, actor = 'user', fromNode = null) {
    return _fetch(`${API_BASE}/api/workflows/runs/${id}/retry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, from_node: fromNode })
    }).then(handle)
  },

  // ---- Phase 7: local desktop shell ----
  getLocalStatus() {
    return _fetch(`${API_BASE}/api/local/status`).then(handle)
  },
  localStatus() {
    return _fetch(`${API_BASE}/api/local/status`).then(handle)
  },
  localSettings() {
    return _fetch(`${API_BASE}/api/local/settings`).then(handle)
  },
  getLocalSettings() {
    return _fetch(`${API_BASE}/api/local/settings`).then(handle)
  },
  patchLocalSettings(patch) {
    return _fetch(`${API_BASE}/api/local/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patch })
    }).then(handle)
  },
  localStorage() {
    return _fetch(`${API_BASE}/api/local/storage`).then(handle)
  },
  getLocalStorage() {
    return _fetch(`${API_BASE}/api/local/storage`).then(handle)
  },
  exportAudit(limit = 1000) {
    return _fetch(`${API_BASE}/api/local/export-audit?limit=${limit}`, {
      method: 'POST'
    }).then(handle)
  },
  exportLogs() {
    return _fetch(`${API_BASE}/api/local/export-logs`, {
      method: 'POST'
    }).then(handle)
  },
  clearLocalCache(confirm = false) {
    const flag = confirm ? 'true' : 'false'
    return _fetch(`${API_BASE}/api/local/clear-cache?confirm=${flag}`, {
      method: 'POST'
    }).then(handle)
  },

  // ----- Phase 10: version history, file snapshots, restore -----
  listVersions(entityType, entityId, { limit = 200 } = {}) {
    return fetch(
      `${API_BASE}/api/versions/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}?limit=${limit}`
    ).then(handle)
  },
  getVersion(entityType, entityId, versionNumber) {
    return fetch(
      `${API_BASE}/api/versions/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/${versionNumber}`
    ).then(handle)
  },
  diffVersions(entityType, entityId, fromVersion, toVersion = null) {
    const params = new URLSearchParams({ from: String(fromVersion) })
    if (toVersion !== null) params.set('to', String(toVersion))
    return fetch(
      `${API_BASE}/api/versions/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/diff?${params}`
    ).then(handle)
  },
  restoreVersion(entityType, entityId, versionNumber, { actor = 'user', reason = '' } = {}) {
    return fetch(
      `${API_BASE}/api/versions/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}/restore?version=${versionNumber}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor, reason }),
      }
    ).then(handle)
  },
  changeTimeline(entityType, entityId, { limit = 100 } = {}) {
    return fetch(
      `${API_BASE}/api/change-timeline/${encodeURIComponent(entityType)}/${encodeURIComponent(entityId)}?limit=${limit}`
    ).then(handle)
  },
  listFileSnapshots({ fileType = null, originalPath = null, limit = 200 } = {}) {
    const params = new URLSearchParams({ limit: String(limit) })
    if (fileType) params.set('file_type', fileType)
    if (originalPath) params.set('original_path', originalPath)
    return _fetch(`${API_BASE}/api/file-snapshots?${params}`).then(handle)
  },
  getFileSnapshot(id) {
    return _fetch(`${API_BASE}/api/file-snapshots/${id}`).then(handle)
  },
  restoreFileSnapshot(id, { actor = 'user', reason = '', targetPath = null } = {}) {
    const params = new URLSearchParams()
    if (targetPath) params.set('target_path', targetPath)
    const q = params.toString() ? `?${params}` : ''
    return _fetch(`${API_BASE}/api/file-snapshots/${id}/restore${q}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, reason }),
    }).then(handle)
  },
  listWorkflowVersions(workflowId, { limit = 200 } = {}) {
    return fetch(
      `${API_BASE}/api/workflows/${workflowId}/versions?limit=${limit}`
    ).then(handle)
  },
  restoreWorkflowVersion(workflowId, versionNumber, { actor = 'user', reason = '' } = {}) {
    return fetch(
      `${API_BASE}/api/workflows/${workflowId}/versions/${versionNumber}/restore`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor, reason }),
      }
    ).then(handle)
  },
  listRestoreLogs({ limit = 100 } = {}) {
    return _fetch(`${API_BASE}/api/restore-logs?limit=${limit}`).then(handle)
  },

  // ---- Phase 12: browser automation ----
  getBrowserPolicies() {
    return _fetch(`${API_BASE}/api/browser/policies`).then(handle)
  },
  updateBrowserPolicies(patch, actor = 'user') {
    return _fetch(`${API_BASE}/api/browser/policies?actor=${encodeURIComponent(actor)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    }).then(handle)
  },
  getBrowserStatus() {
    return _fetch(`${API_BASE}/api/browser/status`).then(handle)
  },
  stopBrowser(actor = 'user') {
    return _fetch(`${API_BASE}/api/browser/stop?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },
  previewOpenUrl(payload) {
    return _fetch(`${API_BASE}/api/browser/preview-open-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  previewFillForm(payload) {
    return _fetch(`${API_BASE}/api/browser/preview-fill-form`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  previewAppendInvoiceRow(payload) {
    return _fetch(`${API_BASE}/api/browser/preview-append-invoice-row`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  fillTestFormPreview(payload) {
    return _fetch(`${API_BASE}/api/browser/test-form/fill-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  approveBrowserAction(id, payload = { actor: 'user' }) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  rejectBrowserAction(id, payload = { actor: 'user' }) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  cancelBrowserAction(id, payload = { actor: 'user' }) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  listBrowserActions({ limit = 50, status } = {}) {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    params.set('limit', String(limit))
    return _fetch(`${API_BASE}/api/browser/actions?${params}`).then(handle)
  },
  getBrowserAction(id) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}`).then(handle)
  },
  getBrowserActionSteps(id) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}/steps`).then(handle)
  },
  getBrowserActionSnapshots(id) {
    return _fetch(`${API_BASE}/api/browser/actions/${id}/snapshot`).then(handle)
  },
  listVoiceIntents() {
    return _fetch(`${API_BASE}/api/browser/voices`).then(handle)
  },
  dispatchVoiceIntent(payload) {
    return _fetch(`${API_BASE}/api/browser/voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  testFormUrl() {
    return `${API_BASE}/api/browser/test-form`
  },

  // ---- Phase 13: QuickBooks/Xero accounting sync ----
  getAccountingStatus() {
    return _fetch(`${API_BASE}/api/accounting/status`).then(handle)
  },
  quickbooksConnect() {
    return _fetch(`${API_BASE}/api/accounting/quickbooks/connect`).then(handle)
  },
  xeroConnect() {
    return _fetch(`${API_BASE}/api/accounting/xero/connect`).then(handle)
  },
  disconnectAccountingConnection(id) {
    return _fetch(`${API_BASE}/api/accounting/connections/${id}/disconnect`, {
      method: 'POST'
    }).then(handle)
  },
  quickbooksSyncStatus() {
    return _fetch(`${API_BASE}/api/quickbooks/status`).then(handle)
  },
  quickbooksSync() {
    return _fetch(`${API_BASE}/api/quickbooks/sync`, { method: 'POST' }).then(handle)
  },
  listAccountingConnections() {
    return _fetch(`${API_BASE}/api/accounting/connections`).then(handle)
  },
  listAccountingFieldMappings(provider) {
    const params = provider ? `?provider=${encodeURIComponent(provider)}` : ''
    return _fetch(`${API_BASE}/api/accounting/mappings${params}`).then(handle)
  },
  updateAccountingFieldMappings(mappings, actor = 'user') {
    return _fetch(`${API_BASE}/api/accounting/mappings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mappings })
    }).then(handle)
  },
  searchAccountingVendors(provider, query) {
    return _fetch(`${API_BASE}/api/accounting/vendors/search?provider=${encodeURIComponent(provider)}&query=${encodeURIComponent(query)}`).then(handle)
  },
  mapAccountingVendor(payload) {
    return _fetch(`${API_BASE}/api/accounting/vendors/map`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  searchAccountingCategories(provider, query) {
    return _fetch(`${API_BASE}/api/accounting/categories?provider=${encodeURIComponent(provider)}&query=${encodeURIComponent(query)}`).then(handle)
  },
  mapAccountingCategory(payload) {
    return _fetch(`${API_BASE}/api/accounting/categories/map`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  listAccountingVendorMappings(provider) {
    const params = `?provider=${encodeURIComponent(provider)}`
    return _fetch(`${API_BASE}/api/accounting/vendor-mappings${params}`).then(handle)  },
  listAccountingCategoryMappings(provider) {
    const params = `?provider=${encodeURIComponent(provider)}`
    return _fetch(`${API_BASE}/api/accounting/category-mappings${params}`).then(handle)
  },
  previewAccountingSync(invoiceId, provider) {
    return _fetch(`${API_BASE}/api/accounting/invoices/${invoiceId}/preview-sync?provider=${encodeURIComponent(provider)}`, {
      method: 'POST'
    }).then(handle)
  },
  getAccountingPreview(previewId) {
    return _fetch(`${API_BASE}/api/accounting/previews/${previewId}`).then(handle)
  },
  approveAccountingPreview(previewId, payload = { actor: 'user', reason: 'Approved.' }) {
    return _fetch(`${API_BASE}/api/accounting/previews/${previewId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  rejectAccountingPreview(previewId, payload = { actor: 'user', reason: 'Rejected.' }) {
    return _fetch(`${API_BASE}/api/accounting/previews/${previewId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  syncAccountingPreview(previewId, actor = 'user') {
    return _fetch(`${API_BASE}/api/accounting/previews/${previewId}/sync?actor=${encodeURIComponent(actor)}`, {
      method: 'POST'
    }).then(handle)
  },
  validateAccountingSync(syncLogId) {
    return _fetch(`${API_BASE}/api/accounting/sync-logs/${syncLogId}/validate`, {
      method: 'POST'
    }).then(handle)
  },
  getAccountingValidations(invoiceId) {
    return _fetch(`${API_BASE}/api/accounting/validations/${invoiceId}`).then(handle)
  },
  listAccountingSyncLogs({ provider, status, invoice_id, limit = 50 } = {}) {
    const params = new URLSearchParams()
    if (provider) params.set('provider', provider)
    if (status) params.set('status', status)
    if (invoice_id) params.set('invoice_id', String(invoice_id))
    params.set('limit', String(limit))
    return _fetch(`${API_BASE}/api/accounting/sync-logs?${params}`).then(handle)
  },
  listFailedAccountingSyncs(limit = 50) {
    return _fetch(`${API_BASE}/api/accounting/failed-syncs?limit=${limit}`).then(handle)
  },
  accountingVoicePreview(payload) {
    return _fetch(`${API_BASE}/api/accounting/voice/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },

  // ---- Phase 14: Workflow Recording ----
  getRecordingPolicies() {
    return _fetch(`${API_BASE}/api/recording/policies`).then(handle)
  },
  updateRecordingPolicies(payload) {
    return _fetch(`${API_BASE}/api/recording/policies`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  startRecording() {
    return _fetch(`${API_BASE}/api/recording/start`, { method: 'POST' }).then(handle)
  },
  stopRecording(sessionId) {
    return _fetch(`${API_BASE}/api/recording/stop?session_id=${sessionId}`, { method: 'POST' }).then(handle)
  },
  captureEvent(sessionId, event) {
    return _fetch(`${API_BASE}/api/recording/events?session_id=${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event)
    }).then(handle)
  },
  listRecordingSessions() {
    return _fetch(`${API_BASE}/api/recording/sessions`).then(handle)
  },
  getRecordingSession(sessionId) {
    return _fetch(`${API_BASE}/api/recording/sessions/${sessionId}`).then(handle)
  },
  saveRecordingSession(sessionId, name, description) {
    const params = new URLSearchParams({ name })
    if (description) params.set('description', description)
    return _fetch(`${API_BASE}/api/recording/sessions/${sessionId}/save?${params}`, { method: 'POST' }).then(handle)
  },
  listRecordedWorkflows() {
    return _fetch(`${API_BASE}/api/recording/workflows`).then(handle)
  },
  createRecordedWorkflow(payload) {
    return _fetch(`${API_BASE}/api/recording/workflows`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  getRecordedWorkflow(id) {
    return _fetch(`${API_BASE}/api/recording/workflows/${id}`).then(handle)
  },
  updateRecordedWorkflow(id, payload) {
    return _fetch(`${API_BASE}/api/recording/workflows/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  deleteRecordedWorkflow(id) {
    return _fetch(`${API_BASE}/api/recording/workflows/${id}`, { method: 'DELETE' }).then(handle)
  },
  getRecordedWorkflowSteps(workflowId) {
    return _fetch(`${API_BASE}/api/recording/workflows/${workflowId}/steps`).then(handle)
  },
  updateRecordedWorkflowStep(workflowId, stepId, payload) {
    return _fetch(`${API_BASE}/api/recording/workflows/${workflowId}/steps/${stepId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(handle)
  },
  duplicateRecordedWorkflow(workflowId) {
    return _fetch(`${API_BASE}/api/recording/workflows/${workflowId}/duplicate`, { method: 'POST' }).then(handle)
  },
  dryRunWorkflow(workflowId) {
    return _fetch(`${API_BASE}/api/recording/workflows/${workflowId}/dry-run`, { method: 'POST' }).then(handle)
  },
  replayWorkflow(workflowId) {
    return _fetch(`${API_BASE}/api/recording/workflows/${workflowId}/replay`, { method: 'POST' }).then(handle)
  },
  approveReplayStep(runId, stepLogId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/approve-step?step_log_id=${stepLogId}`, { method: 'POST' }).then(handle)
  },
  rejectReplayStep(runId, stepLogId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/reject-step?step_log_id=${stepLogId}`, { method: 'POST' }).then(handle)
  },
  pauseReplay(runId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/pause`, { method: 'POST' }).then(handle)
  },
  resumeReplay(runId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/resume`, { method: 'POST' }).then(handle)
  },
  emergencyStopReplay(runId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/emergency-stop`, { method: 'POST' }).then(handle)
  },
  listReplayRuns() {
    return _fetch(`${API_BASE}/api/recording/runs`).then(handle)
  },
  getReplayRun(runId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}`).then(handle)
  },
  getReplayRunSteps(runId) {
    return _fetch(`${API_BASE}/api/recording/runs/${runId}/steps`).then(handle)
  },

  // ── Phase 15: Screen Control ─────────────────────────────────────

  getScreenPolicies() {
    return _fetch(`${API_BASE}/api/screen/policies`).then(handle)
  },
  updateScreenPolicies(body) {
    return _fetch(`${API_BASE}/api/screen/policies`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handle)
  },
  getScreenStatus() {
    return _fetch(`${API_BASE}/api/screen/status`).then(handle)
  },
  startScreenSession() {
    return _fetch(`${API_BASE}/api/screen/start-session`, { method: 'POST' }).then(handle)
  },
  endScreenSession(sessionId, stoppedBy, reason) {
    let q = `session_id=${sessionId}`
    if (stoppedBy) q += `&stopped_by=${stoppedBy}`
    if (reason) q += `&reason=${reason}`
    return _fetch(`${API_BASE}/api/screen/end-session?${q}`, { method: 'POST' }).then(handle)
  },
  screenEmergencyStop(sessionId, stoppedBy) {
    let q = ''
    if (sessionId) q += `session_id=${sessionId}&`
    q += `stopped_by=${stoppedBy || 'user'}`
    return _fetch(`${API_BASE}/api/screen/emergency-stop?${q}`, { method: 'POST' }).then(handle)
  },
  readScreenContext() {
    return _fetch(`${API_BASE}/api/screen/read`, { method: 'POST' }).then(handle)
  },
  captureScreenshot() {
    return _fetch(`${API_BASE}/api/screen/capture`, { method: 'POST' }).then(handle)
  },
  ocrScreen() {
    return _fetch(`${API_BASE}/api/screen/ocr`, { method: 'POST' }).then(handle)
  },
  summarizeScreen() {
    return _fetch(`${API_BASE}/api/screen/summarize`, { method: 'POST' }).then(handle)
  },
  planScreenAction(params) {
    const q = new URLSearchParams(params).toString()
    return _fetch(`${API_BASE}/api/screen/plan-action?${q}`, { method: 'POST' }).then(handle)
  },
  listScreenActions(sessionId, limit) {
    let q = limit ? `limit=${limit}` : ''
    if (sessionId) q += `${q ? '&' : ''}session_id=${sessionId}`
    return _fetch(`${API_BASE}/api/screen/actions${q ? '?' + q : ''}`).then(handle)
  },
  getScreenAction(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}`).then(handle)
  },
  approveScreenAction(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/approve`, { method: 'POST' }).then(handle)
  },
  rejectScreenAction(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/reject`, { method: 'POST' }).then(handle)
  },
  executeScreenActionStep(actionId, approveFirst) {
    let q = `approve_first=${approveFirst !== false}`
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/execute-step?${q}`, { method: 'POST' }).then(handle)
  },
  cancelScreenAction(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/cancel`, { method: 'POST' }).then(handle)
  },
  listScreenActionSteps(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/steps`).then(handle)
  },
  listScreenSessions(limit) {
    return _fetch(`${API_BASE}/api/screen/sessions${limit ? '?limit=' + limit : ''}`).then(handle)
  },
  listScreenVoiceIntents() {
    return _fetch(`${API_BASE}/api/screen/voices`).then(handle)
  },
  dispatchScreenVoiceIntent(intent, sourceId) {
    return _fetch(`${API_BASE}/api/screen/voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, source_id: sourceId || '' }),
    }).then(handle)
  },
  getScreenCapabilities() {
    return _fetch(`${API_BASE}/api/screen/capabilities`).then(handle)
  },
  getScreenOcrStatus() {
    return _fetch(`${API_BASE}/api/screen/ocr/status`).then(handle)
  },
  getScreenLogs(params = {}) {
    const q = new URLSearchParams()
    if (params.session_id) q.set('session_id', params.session_id)
    if (params.limit) q.set('limit', String(params.limit))
    const qs = q.toString() ? `?${q}` : ''
    return _fetch(`${API_BASE}/api/screen/logs${qs}`).then(handle)
  },
  executeAllApprovedSteps(actionId) {
    return _fetch(`${API_BASE}/api/screen/actions/${actionId}/execute-all`, { method: 'POST' }).then(handle)
  },

  // ── Phase 16B: Safety + Permissions + Audit Export + Readiness + Backup ──

  getSafetyPolicies() {
    return _fetch(`${API_BASE}/api/safety/policies`).then(handle)
  },
  updateSafetyPolicies(body) {
    return _fetch(`${API_BASE}/api/safety/policies`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handle)
  },
  activateKillSwitch(reason) {
    return _fetch(`${API_BASE}/api/safety/kill-switch?reason=${encodeURIComponent(reason)}`, { method: 'POST' }).then(handle)
  },
  resumeAutomation() {
    return _fetch(`${API_BASE}/api/safety/resume-automation`, { method: 'POST' }).then(handle)
  },
  getAutomationStatus() {
    return _fetch(`${API_BASE}/api/safety/automation-status`).then(handle)
  },
  listPermissions() {
    return _fetch(`${API_BASE}/api/permissions`).then(handle)
  },
  getMyPermissions() {
    return _fetch(`${API_BASE}/api/permissions/me`).then(handle)
  },
  listRoles() {
    return _fetch(`${API_BASE}/api/permissions/roles`).then(handle)
  },
  listPermissionNames() {
    return _fetch(`${API_BASE}/api/permissions/permission-names`).then(handle)
  },
  updateRolePermissions(role, entries) {
    return _fetch(`${API_BASE}/api/permissions/${encodeURIComponent(role)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries }),
    }).then(handle)
  },
  createAuditExport(body) {
    return _fetch(`${API_BASE}/api/audit/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(handle)
  },
  listAuditExports() {
    return _fetch(`${API_BASE}/api/audit/exports`).then(handle)
  },
  getAuditExport(id) {
    return _fetch(`${API_BASE}/api/audit/exports/${id}`).then(handle)
  },
  downloadAuditExportUrl(id) {
    return `${API_BASE}/api/audit/exports/${id}/download`
  },
  getSystemReadiness() {
    return _fetch(`${API_BASE}/api/system/readiness`).then(handle)
  },
  getBackupStatus() {
    return _fetch(`${API_BASE}/api/backup/status`).then(handle)
  },
  runLocalBackup() {
    return _fetch(`${API_BASE}/api/backup/run-local`, { method: 'POST' }).then(handle)
  },
  testRestore() {
    return _fetch(`${API_BASE}/api/backup/test-restore`, { method: 'POST' }).then(handle)
  },

  // ── Phase 18: Demo Mode ──────────────────────────────────────────
  demoStatus() {
    return _fetch(`${API_BASE}/api/demo/status`, { method: 'GET' }).then(handle)
  },
  seedDemoData() {
    return _fetch(`${API_BASE}/api/demo/seed`, { method: 'POST' }).then(handle)
  },
  resetDemoData() {
    return _fetch(`${API_BASE}/api/demo/reset`, { method: 'POST' }).then(handle)
  },
  sampleFiles() {
    return _fetch(`${API_BASE}/api/demo/sample-files`).then(handle)
  },

  // ── Phase 18: Onboarding ─────────────────────────────────────────
  onboardingStatus() {
    return _fetch(`${API_BASE}/api/onboarding/status`).then(handle)
  },
  completeOnboardingStep(step) {
    return _fetch(`${API_BASE}/api/onboarding/complete-step`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ step }) }).then(handle)
  },
  dismissOnboarding() {
    return _fetch(`${API_BASE}/api/onboarding/dismiss`, { method: 'POST' }).then(handle)
  },
  checkSetup() {
    return _fetch(`${API_BASE}/api/onboarding/check-setup`).then(handle)
  },
  completeOnboarding(demoData = false) {
    return _fetch(`${API_BASE}/api/onboarding/complete`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ demo_data: demoData }) }).then(handle)
  },

  // ── Phase 18: About ──────────────────────────────────────────────
  about() {
    return _fetch(`${API_BASE}/api/about`).then(handle)
  },

  // ── Phase 18: Diagnostics ────────────────────────────────────────
  diagnostics() {
    return _fetch(`${API_BASE}/api/first-run/diagnostics`).then(handle)
  },

  // ── Phase 19: Pilot Readiness ─────────────────────────────────────
  demoWalkthroughStatus() { return _fetchJson(`${API_BASE}/api/demo/walkthrough`); },
  startDemoWalkthrough() { return _fetchJson(`${API_BASE}/api/demo/walkthrough/start`, 'POST'); },
  completeDemoWalkthroughStep(step) { return _fetchJson(`${API_BASE}/api/demo/walkthrough/complete-step`, 'POST', { step }); },
  skipDemoWalkthroughStep(step) { return _fetchJson(`${API_BASE}/api/demo/walkthrough/skip-step`, 'POST', { step }); },
  resetDemoWalkthrough() { return _fetchJson(`${API_BASE}/api/demo/walkthrough/reset`, 'POST'); },
  dismissDemoWalkthrough() { return _fetchJson(`${API_BASE}/api/demo/walkthrough/dismiss`, 'POST'); },

  createFeedback(body) { return _fetchJson(`${API_BASE}/api/feedback`, 'POST', body); },
  listFeedback(params = {}) { const q = new URLSearchParams(params).toString(); return _fetchJson(`${API_BASE}/api/feedback?${q}`); },
  getFeedback(id) { return _fetchJson(`${API_BASE}/api/feedback/${id}`); },
  updateFeedback(id, body) { return _fetchJson(`${API_BASE}/api/feedback/${id}`, 'PATCH', body); },

  createBugReport(body) { return _fetchJson(`${API_BASE}/api/bug-reports`, 'POST', body); },
  listBugReports(params = {}) { const q = new URLSearchParams(params).toString(); return _fetchJson(`${API_BASE}/api/bug-reports?${q}`); },
  getBugReport(id) { return _fetchJson(`${API_BASE}/api/bug-reports/${id}`); },
  downloadBugReportUrl(id) { return `${API_BASE}/api/bug-reports/${id}/download`; },

  recordUsageEvent(body) { return _fetchJson(`${API_BASE}/api/usage/events`, 'POST', body); },
  usageSummary(params = {}) { const q = new URLSearchParams(params).toString(); return _fetchJson(`${API_BASE}/api/usage/summary?${q}`); },
  listUsageEvents(params = {}) { const q = new URLSearchParams(params).toString(); return _fetchJson(`${API_BASE}/api/usage/events?${q}`); },

  pilotReadiness() { return _fetchJson(`${API_BASE}/api/pilot/readiness`); },
  completePilotReadinessStep(step) { return _fetchJson(`${API_BASE}/api/pilot/readiness/complete-step`, 'POST', { step }); },
  resetPilotReadiness() { return _fetchJson(`${API_BASE}/api/pilot/readiness/reset`, 'POST'); },

  // ── Phase 22.5: Unified Voice Assistant ──────────────────────────
  transcribeVoice(audioBlob) {
    const fd = new FormData()
    fd.append('file', audioBlob, 'voice_recording.webm')
    return _fetch(`${API_BASE}/api/voice/transcribe`, { 
      method: 'POST', 
      headers: authHeaders(),
      body: fd
    }).then(handle)
  },
  parseVoiceCommand(text) {
    return _fetch(`${API_BASE}/api/voice/parse-command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ raw_text: text })
    }).then(handle)
  },
  executeVoiceCommand(commandId) {
    return _fetch(`${API_BASE}/api/voice/execute-command?command_id=${commandId}`, {
      method: 'POST',
      headers: authHeaders()
    }).then(handle)
  },
  confirmVoiceCommand(commandId) {
    return _fetch(`${API_BASE}/api/voice/commands/${commandId}/confirm`, {
      method: 'POST',
      headers: authHeaders()
    }).then(handle)
  },
  getVoiceHistory(limit = 50) {
    return _fetch(`${API_BASE}/api/voice/history?limit=${limit}`, { headers: authHeaders() }).then(handle)
  },
  getAvailableCommands() {
    return _fetch(`${API_BASE}/api/voice/available-commands`, { headers: authHeaders() }).then(handle)
  },
  getSTTStatus() {
    return _fetch(`${API_BASE}/api/voice/stt-status`, { headers: authHeaders() }).then(handle)
  },

  // ── Phase 23: Accountant Agent ────────────────────────────────────
  agentStatus() {
    return _fetchJson(`${API_BASE}/api/agent/status`)
  },
  agentContext() {
    return _fetchJson(`${API_BASE}/api/agent/context`, 'POST')
  },
  planAgentTask(body) {
    return _fetchJson(`${API_BASE}/api/agent/plan-task`, 'POST', body)
  },
  approveAgentPlan(planId, body) {
    return _fetchJson(`${API_BASE}/api/agent/plans/${planId}/approve`, 'POST', body)
  },
  executeRunStep(runId, body) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${runId}/execute-step`, 'POST', body)
  },
  dryRunRun(runId) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${runId}/dry-run`, 'POST', {})
  },
  startLiveRun(runId) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${runId}/start-live`, 'POST', {})
  },
  stopRun(runId, body) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${runId}/stop`, 'POST', body || {})
  },
  listAgentPlans(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/plans?${q}`)
  },
  saveAgentWorkflow(body) {
    return _fetchJson(`${API_BASE}/api/agent/workflows/save`, 'POST', body)
  },
  listAgentWorkflows(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/workflows?${q}`)
  },
  repeatAgentWorkflow(id, body) {
    return _fetchJson(`${API_BASE}/api/agent/workflows/${id}/repeat`, 'POST', body)
  },
  repeatRecentAgentWorkflow(body) {
    return _fetchJson(`${API_BASE}/api/agent/workflows/repeat-recent`, 'POST', body)
  },

  // ── Phase 39: Background Tasks ─────────────────────────────────
  runTaskInBackground(body) {
    return _fetchJson(`${API_BASE}/api/agent/run-background`, 'POST', body)
  },
  getBackgroundTasks(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/background-tasks?${q}`)
  },
  cancelBackgroundTask(id) {
    return _fetchJson(`${API_BASE}/api/agent/background-tasks/${id}/cancel`, 'POST')
  },
  answerBackgroundTask(id, userAnswer) {
    return _fetchJson(`${API_BASE}/api/agent/background-tasks/${id}/answer`, 'POST', { user_answer: userAnswer })
  },
  llmStatus() {
    return _fetchJson(`${API_BASE}/api/agent/llm-status`)
  },
  listWatchers() {
    return _fetchJson(`${API_BASE}/api/watchers/`)
  },
  createWatcher(body) {
    return _fetchJson(`${API_BASE}/api/watchers/`, 'POST', body)
  },
  updateWatcher(id, body) {
    return _fetchJson(`${API_BASE}/api/watchers/${id}`, 'PATCH', body)
  },
  deleteWatcher(id) {
    return _fetchJson(`${API_BASE}/api/watchers/${id}`, 'DELETE')
  },
  runWatcherNow(id) {
    return _fetchJson(`${API_BASE}/api/watchers/${id}/run-now`, 'POST')
  },
  bankParseFeed(content, filename = 'feed.csv') {
    return _fetchJson(`${API_BASE}/api/agent/bank/parse`, 'POST', { content, filename })
  },
  bankReconcile(transactions) {
    return _fetchJson(`${API_BASE}/api/agent/bank/reconcile`, 'POST', { transactions })
  },
  listAgentWorkflowRuns(id, params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/workflows/${id}/runs?${q}`)
  },
  getAgentRunSteps(id) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${id}/steps`)
  },
  getAgentRunSummary(id) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${id}/summary`)
  },

  // ── Phase 42: Learning & Corrections ────────────────────────────
  createCorrection(body) {
    return _fetchJson(`${API_BASE}/api/agent/correct`, 'POST', body)
  },
  listCorrections() {
    return _fetchJson(`${API_BASE}/api/agent/corrections`)
  },
  deleteCorrection(id) {
    return _fetchJson(`${API_BASE}/api/agent/corrections/${id}`, 'DELETE')
  },
  verifyAgentRunExcel(id) {
    return _fetchJson(`${API_BASE}/api/agent/runs/${id}/verify-excel`, 'POST', {})
  },

  // ── Phase 23E: OpenCode-style Agent Modes & Recording ──────────────
  getAgentMode() {
    return _fetchJson(`${API_BASE}/api/agent/mode`)
  },
  setAgentMode(mode) {
    return _fetchJson(`${API_BASE}/api/agent/mode`, 'POST', { mode })
  },
  getCurrentTask() {
    return _fetchJson(`${API_BASE}/api/agent/current-task`)
  },
  getCurrentRun() {
    return _fetchJson(`${API_BASE}/api/agent/current-run`)
  },
  startRecording() {
    return _fetchJson(`${API_BASE}/api/agent/record/start`, 'POST', {})
  },
  stopRecording(body) {
    return _fetchJson(`${API_BASE}/api/agent/record/stop`, 'POST', body || {})
  },
  replayYesterday(body) {
    return _fetchJson(`${API_BASE}/api/agent/replay/yesterday`, 'POST', body || {})
  },
  emergencyStopAgent(body) {
    return _fetchJson(`${API_BASE}/api/agent/emergency-stop`, 'POST', body || {})
  },

  // ── Phase 33: Workflow Recorder MVP ───────────────────────────────
  recorderStart(body) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/start`, 'POST', body || {})
  },
  recorderStop(sessionId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/stop`, 'POST', { session_id: sessionId })
  },
  recorderCancel(sessionId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/cancel`, 'POST', { session_id: sessionId })
  },
  recorderCurrent() {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/current`)
  },
  recorderRecordEvent(sessionId, body) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/event?session_id=${sessionId}`, 'POST', body)
  },
  recorderListEvents(sessionId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/${sessionId}/events`)
  },
  recorderConvertToSkill(sessionId, body) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/${sessionId}/convert-to-skill`, 'POST', body || {})
  },
  recorderApproveDraft(draftId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/skill-drafts/${draftId}/approve`, 'POST', {})
  },
  recorderRejectDraft(draftId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/skill-drafts/${draftId}/reject`, 'POST', {})
  },
  recorderSaveAsSkill(draftId) {
    return _fetchJson(`${API_BASE}/api/workflow-recorder/skill-drafts/${draftId}/save-as-skill`, 'POST', {})
  },

  // ── Phase 23F: P&L Report Comparison ──────────────────────────────
  pnlCompareDemo() {
    return _fetchJson(`${API_BASE}/api/agent/reports/pnl/compare-demo`, 'POST', {})
  },
  pnlCompareUploaded(body) {
    return _fetchJson(`${API_BASE}/api/agent/reports/pnl/compare-uploaded`, 'POST', body)
  },
  listPnlRuns(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/reports/pnl/runs?${q}`)
  },
  getPnlRun(id) {
    return _fetchJson(`${API_BASE}/api/agent/reports/pnl/runs/${id}`)
  },

  // ── Phase 25: Folder Invoice Workflow ──────────────────────────────
  folderInvoiceScan(body) {
    return _fetchJson(`${API_BASE}/api/agent/folder-invoice/scan`, 'POST', body)
  },
  folderInvoiceCreateExcel(body) {
    return _fetchJson(`${API_BASE}/api/agent/folder-invoice/create-excel`, 'POST', body)
  },
  listFolderInvoiceRuns(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/agent/folder-invoice/runs?${q}`)
  },
  getFolderInvoiceRun(id) {
    return _fetchJson(`${API_BASE}/api/agent/folder-invoice/runs/${id}`)
  },

  // ── Phase 27: Windows Voice Layer ──────────────────────────────────
  voiceLayerStatus() {
    return _fetchJson(`${API_BASE}/api/voice-layer/status`)
  },
  getVoiceLayerSettings() {
    return _fetchJson(`${API_BASE}/api/voice-layer/settings`)
  },
  updateVoiceLayerSettings(payload) {
    return _fetchJson(`${API_BASE}/api/voice-layer/settings`, 'POST', payload)
  },
  dictateStart() {
    return _fetchJson(`${API_BASE}/api/voice-layer/dictate`, 'POST')
  },
  aiModeStart() {
    return _fetchJson(`${API_BASE}/api/voice-layer/ai-mode`, 'POST')
  },
  agentCommandStart() {
    return _fetchJson(`${API_BASE}/api/voice-layer/agent-command`, 'POST')
  },
  voiceLayerStop() {
    return _fetchJson(`${API_BASE}/api/voice-layer/stop`, 'POST')
  },
  voiceLayerTranscribe(formData) {
    return fetch(`${API_BASE}/api/voice-layer/transcribe`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    }).then(handle)
  },
  voiceLayerPaste(text, confirm = false) {
    return _fetch(`${API_BASE}/api/voice-layer/paste`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...authHeaders() },
      body: new URLSearchParams({ text, confirm: String(confirm) }),
    }).then(handle)
  },
  voiceLayerPasteConfirm(text) {
    return _fetch(`${API_BASE}/api/voice-layer/paste/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...authHeaders() },
      body: new URLSearchParams({ text }),
    }).then(handle)
  },
  getDictationHistory(params = {}) {
    const q = new URLSearchParams()
    if (params.limit) q.set('limit', String(params.limit))
    if (params.offset != null) q.set('offset', String(params.offset))
    if (params.mode) q.set('mode', params.mode)
    return _fetchJson(`${API_BASE}/api/voice-layer/history?${q}`)
  },
  deleteDictationEntry(id) {
    return _fetchJson(`${API_BASE}/api/voice-layer/history/${id}`, 'DELETE')
  },
  clearDictationHistory() {
    return _fetchJson(`${API_BASE}/api/voice-layer/history`, 'DELETE')
  },
  // ── Phase 28: Whisper auto-detect, model download, test transcription ──
  whisperDetect() {
    return _fetchJson(`${API_BASE}/api/voice-layer/whisper-detect`)
  },
  whisperDownloadModel(modelName) {
    const fd = new URLSearchParams()
    fd.append('model_name', modelName || 'ggml-base.en.bin')
    return _fetch(`${API_BASE}/api/voice-layer/whisper-download-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...authHeaders() },
      body: fd,
    }).then(handle)
  },
  testTranscribe() {
    return _fetchJson(`${API_BASE}/api/voice-layer/test-transcribe`, 'POST')
  },

  // ── Accounting Skills (Hermes-style skill memory) ──────────────
  createSkillFromWorkflow(body) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/from-workflow`, 'POST', body)
  },
  matchSkill(phrase) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/match?phrase=${encodeURIComponent(phrase)}`)
  },
  matchAgentSkill(body) {
    return _fetchJson(`${API_BASE}/api/agent/match-skill`, 'POST', body)
  },
  listSkills(status) {
    const params = status ? `?status=${encodeURIComponent(status)}` : ''
    return _fetchJson(`${API_BASE}/api/accounting-skills${params}`)
  },
  getSkill(id) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}`)
  },
  updateSkill(id, body) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}`, 'PATCH', body)
  },
  dryRunSkill(id) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/dry-run`, 'POST')
  },
  executeSkill(id, body = {}) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/execute`, 'POST', body)
  },
  completeSkillRun(runId, body = {}) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/runs/${runId}/complete`, 'POST', body)
  },
  getSkillVersions(id) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/versions`)
  },
  restoreSkillVersion(id, version) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/restore/${version}`, 'POST')
  },
  archiveSkill(id) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/archive`, 'POST')
  },
  listSkillRuns(id, limit = 50) {
    return _fetchJson(`${API_BASE}/api/accounting-skills/${id}/runs?limit=${limit}`)
  },

  // ── Phase 35: Desktop Update + License ───────────────────────────
  registerDevice(body) {
    return _fetchJson(`${API_BASE}/api/app/register-device`, 'POST', body)
  },
  checkUpdate(body) {
    return _fetchJson(`${API_BASE}/api/app/check-update`, 'POST', body)
  },
  getLatestRelease(params = {}) {
    const q = new URLSearchParams(params).toString()
    return _fetchJson(`${API_BASE}/api/app/releases/latest?${q}`)
  },
  getNotifications() {
    return _fetchJson(`${API_BASE}/api/app/notifications`)
  },
  markNotificationSeen(id) {
    return _fetchJson(`${API_BASE}/api/app/notifications/${id}/seen`, 'POST')
  },
  getLicense() {
    return _fetchJson(`${API_BASE}/api/billing/license`)
  },
  getPlans() {
    return _fetchJson(`${API_BASE}/api/billing/plans`)
  },
  startCheckout(body) {
    return _fetchJson(`${API_BASE}/api/billing/start-checkout`, 'POST', body)
  },
  manageBilling() {
    return _fetchJson(`${API_BASE}/api/billing/manage`, 'POST')
  },
}

export const STATUS_LABELS = {
  imported: 'Imported',
  extracting: 'Extracting',
  needs_review: 'Needs Review',
  ready_for_approval: 'Ready for Approval',
  approved: 'Approved',
  rejected: 'Rejected',
  duplicate: 'Duplicate',
  exported: 'Exported'
}

export const IMPORT_STATUS_LABELS = {
  candidate: 'Candidate',
  downloading: 'Downloading',
  imported: 'Imported',
  duplicate: 'Duplicate',
  skipped: 'Skipped',
  error: 'Error'
}

export const WORKFLOW_STATUS_LABELS = {
  pending: 'Pending',
  running: 'Running',
  awaiting_approval: 'Awaiting Approval',
  completed: 'Completed',
  failed: 'Failed',
  rejected: 'Rejected',
  cancelled: 'Cancelled'
}

export const WORKFLOW_LOG_STATUS_LABELS = {
  ok: 'OK',
  awaiting_approval: 'Awaiting Approval',
  skipped: 'Skipped',
  failed: 'Failed'
}

export const WORKFLOW_APPROVAL_STATUS_LABELS = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  cancelled: 'Cancelled'
}

export const BROWSER_STATUS_LABELS = {
  preview: 'Preview',
  awaiting_approval: 'Awaiting Approval',
  approved: 'Approved',
  rejected: 'Rejected',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled'
}

export const SCREEN_STATUS_LABELS = {
  planned: 'Planned',
  approved: 'Approved',
  rejected: 'Rejected',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  stopped: 'Stopped'
}

export const SCREEN_RISK_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High'
}

export const SCREEN_APPROVAL_LABELS = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  not_required: 'Not Required'
}

export const BROWSER_RISK_LABELS = {
  low: 'Low',
  medium: 'Medium',
  high: 'High'
}

// ── Phase 20 — Public landing & pilot waitlist ────────────────────────────

export async function submitWaitlist(body) {
  return handle(await fetch(`${API_BASE}/api/public/waitlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body)
  }))
}

export async function listAdminWaitlist(params = {}) {
  const q = new URLSearchParams()
  if (params.status) q.set('status', params.status)
  if (params.search) q.set('search', params.search)
  if (params.skip) q.set('skip', String(params.skip))
  if (params.limit) q.set('limit', String(params.limit))
  return handle(await fetch(`${API_BASE}/api/admin/waitlist?${q}`, {
    headers: { ...authHeaders() }
  }))
}

export async function updateAdminWaitlistStatus(id, body) {
  return handle(await fetch(`${API_BASE}/api/admin/waitlist/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body)
  }))
}

export async function adminWaitlistSummary(params = {}) {
  const q = new URLSearchParams()
  if (params.status) q.set('status', params.status)
  return handle(await fetch(`${API_BASE}/api/admin/waitlist/summary?${q}`, {
    headers: { ...authHeaders() }
  }))
}

export function adminWaitlistExportCsvUrl() {
  return `${API_BASE}/api/admin/waitlist/export.csv`
}

export async function recordPublicPageEvent(body) {
  return handle(await fetch(`${API_BASE}/api/public/page-event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }))
}

// ── Phase 21 — Performance, startup, cleanup, release ─────────────────

export async function getStartupMetrics() {
  return handle(await fetch(`${API_BASE}/api/system/startup-metrics`, {
    headers: { ...authHeaders() }
  }))
}

export async function getStorageUsage() {
  return handle(await fetch(`${API_BASE}/api/system/storage-usage`, {
    headers: { ...authHeaders() }
  }))
}

export async function getCleanupPreview() {
  return handle(await fetch(`${API_BASE}/api/system/cleanup-preview`, {
    headers: { ...authHeaders() }
  }))
}

export async function runCleanup(body) {
  return handle(await fetch(`${API_BASE}/api/system/cleanup-run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body)
  }))
}

export async function getReleaseChecklist() {
  return handle(await fetch(`${API_BASE}/api/system/release/checklist`, {
    headers: { ...authHeaders() }
  }))
}

export async function completeReleaseStep(body) {
  return handle(await fetch(`${API_BASE}/api/system/release/checklist/complete-step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body)
  }))
}

export async function resetReleaseChecklist() {
  return handle(await fetch(`${API_BASE}/api/system/release/checklist/reset`, {
    method: 'POST',
    headers: { ...authHeaders() }
  }))
}

// ── Phase 46B — Resource Monitor ────────────────────────────────────────

export async function getSystemResources() {
  return handle(await fetch(`${API_BASE}/api/system/resources`, {
    headers: { ...authHeaders() }
  }))
}

export async function optimizeClearMemory() {
  return handle(await fetch(`${API_BASE}/api/system/optimize/clear-memory`, {
    method: 'POST',
    headers: { ...authHeaders() }
  }))
}

export async function optimizeKillExcel() {
  return handle(await fetch(`${API_BASE}/api/system/optimize/kill-excel`, {
    method: 'POST',
    headers: { ...authHeaders() }
  }))
}

export function formatMoney(value, currency) {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)

  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2
    }).format(n)
  } catch (_) {
    return `${currency || ''} ${n.toFixed(2)}`.trim()
  }
}

export function formatDateTime(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString()
  } catch (_) {
    return String(value)
  }
}
