import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api, formatMoney, formatDateTime } from '../src/api.js'

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('builds the correct export URL', () => {
    const url = api.exportExcelUrl()
    expect(url).toMatch(/\/api\/invoices\/export\/excel\?actor=user$/)
  })

  it('builds the correct file URL for a given id', () => {
    expect(api.fileUrl(42)).toMatch(/\/api\/invoices\/42\/file\?inline=true$/)
  })

  it('uploadInvoice sends FormData and parses JSON', async () => {
    const fake = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1, status: 'pending' }), {
        status: 201, headers: { 'content-type': 'application/json' }
      })
    )
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.uploadInvoice(fake, 'alice')
    expect(res.id).toBe(1)
    const [calledUrl, calledInit] = fetchMock.mock.calls[0]
    expect(calledUrl).toMatch(/\/api\/invoices\/upload\?actor=alice/)
    expect(calledInit.method).toBe('POST')
    expect(calledInit.body).toBeInstanceOf(FormData)
  })

  it('rejects with a useful Error on non-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'boom' }), {
        status: 400, headers: { 'content-type': 'application/json' }
      })
    ))
    await expect(api.health()).rejects.toThrow(/boom/)
  })

  it('listInvoices encodes the status filter', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('[]', { status: 200, headers: { 'content-type': 'application/json' } })
    )
    vi.stubGlobal('fetch', fetchMock)
    await api.listInvoices({ status: 'pending', limit: 50, offset: 0 })
    const [url] = fetchMock.mock.calls[0]
    expect(url).toMatch(/status=pending/)
    expect(url).toMatch(/limit=50/)
  })
})

describe('formatMoney', () => {
  it('formats with USD by default', () => {
    expect(formatMoney(1234.5)).toMatch(/\$1,234\.50/)
  })
  it('uses provided currency', () => {
    expect(formatMoney(99, 'EUR')).toMatch(/€|EUR/)
  })
  it('handles nullish values gracefully', () => {
    expect(formatMoney(null)).toBe('')
    expect(formatMoney(undefined)).toBe('')
  })
})

describe('formatDateTime', () => {
  it('returns empty string for null', () => {
    expect(formatDateTime(null)).toBe('')
  })
  it('returns a string for an ISO date', () => {
    expect(typeof formatDateTime('2026-05-12T00:00:00Z')).toBe('string')
  })
})

// ------------------------------------------------------------- Phase 5: parser

describe('parser benchmark api', () => {
  it('listParserEngines calls the engines endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ engines: [{ name: 'existing' }] }), {
        status: 200, headers: { 'content-type': 'application/json' }
      })
    )
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.listParserEngines()
    expect(res.engines[0].name).toBe('existing')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/parser\/engines$/)
  })

  it('runParserBenchmark JSON includes engines query', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ engines: ['existing'], runs: [], summary: {} }), {
        status: 200, headers: { 'content-type': 'application/json' }
      })
    )
    vi.stubGlobal('fetch', fetchMock)
    await api.runParserBenchmark({ engines: ['existing', 'ocr'] })
    const [url] = fetchMock.mock.calls[0]
    expect(url).toMatch(/engines=existing%2Cocr/)
  })

  it('runParserBenchmark CSV returns plain text', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('engine,fixture\nfoo,bar', {
        status: 200, headers: { 'content-type': 'text/csv' }
      })
    )
    vi.stubGlobal('fetch', fetchMock)
    const text = await api.runParserBenchmark({ engines: ['existing'], format: 'csv' })
    expect(typeof text).toBe('string')
    expect(text).toMatch(/engine,fixture/)
  })
})

// ------------------------------------------------------------- Phase 6: workflows

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' }
  })
}

describe('workflow api', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('listWorkflowGraphs calls the graphs endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ graphs: [{ name: 'invoice_upload_processing', description: 'x' }] })
    )
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.listWorkflowGraphs()
    expect(res.graphs[0].name).toBe('invoice_upload_processing')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/workflows\/graphs$/)
  })

  it('startWorkflow POSTs name + body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 7, status: 'running' }))
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.startWorkflow('invoice_upload_processing', { actor: 'alice' }, 'alice')
    expect(res.id).toBe(7)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/workflows\/run\/invoice_upload_processing$/)
    expect(init.method).toBe('POST')
    const body = JSON.parse(init.body)
    expect(body.input.actor).toBe('alice')
    expect(body.actor).toBe('alice')
  })

  it('listWorkflowRuns encodes filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ runs: [] }))
    vi.stubGlobal('fetch', fetchMock)
    await api.listWorkflowRuns({ workflow_name: 'invoice_upload_processing', status: 'awaiting_approval', limit: 25 })
    const [url] = fetchMock.mock.calls[0]
    expect(url).toMatch(/workflow_name=invoice_upload_processing/)
    expect(url).toMatch(/status=awaiting_approval/)
    expect(url).toMatch(/limit=25/)
  })

  it('getWorkflowRun hits the run detail endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, status: 'completed', logs: [], approvals: [] }))
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.getWorkflowRun(1)
    expect(res.id).toBe(1)
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/workflows\/runs\/1$/)
  })

  it('approveWorkflowRun POSTs actor + note', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, status: 'completed' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.approveWorkflowRun(1, 'alice', 'looks good')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/workflows\/runs\/1\/approve$/)
    expect(JSON.parse(init.body)).toEqual({ actor: 'alice', note: 'looks good' })
  })

  it('rejectWorkflowRun POSTs actor + note', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, status: 'rejected' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.rejectWorkflowRun(1, 'alice', 'wrong totals')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/workflows\/runs\/1\/reject$/)
  })

  it('cancelWorkflowRun POSTs actor + note', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, status: 'cancelled' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.cancelWorkflowRun(1, 'alice', 'stop')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/workflows\/runs\/1\/cancel$/)
  })

  it('retryWorkflowRun accepts an optional fromNode', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, status: 'running' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.retryWorkflowRun(1, 'alice', 'parse_invoice')
    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({ actor: 'alice', from_node: 'parse_invoice' })
  })
})

// ------------------------------------------------------------- Phase 7: local shell

describe('local shell api', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('localStatus calls /api/local/status', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      app: 'officepilot-ai', version: '0.7.0', phase: 7, pid: 42, uptime_human: '5s',
      url: 'http://127.0.0.1:8000', data_dir: 'C:/data', storage_root: 'C:/storage',
      database: { status: 'ok' }, env: 'development', parser_engine: 'existing',
      ocr_enabled: true, gmail_configured: false, gmail_allow_real: true,
      host: '127.0.0.1', port: 8000, platform: 'win32'
    }))
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.getLocalStatus()
    expect(res.phase).toBe(7)
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/local\/status$/)
  })

  it('localSettings returns the settings + mutable allow-list', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      settings: { ocr_enabled: true, max_upload_mb: 20 },
      mutable: ['ocr_enabled', 'max_upload_mb']
    }))
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.localSettings()
    expect(res.mutable).toContain('ocr_enabled')
  })

  it('patchLocalSettings sends a PATCH with the patch object', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ applied: { ocr_enabled: false }, rejected: {} }))
    vi.stubGlobal('fetch', fetchMock)
    await api.patchLocalSettings({ ocr_enabled: false })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/local\/settings$/)
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ patch: { ocr_enabled: false } })
  })

  it('localStorage returns the storage summary', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      data_dir: 'C:/data', storage_root: 'C:/storage',
      protected_total_human: '10 KB', cache_total_human: '0 B',
      dirs: []
    }))
    vi.stubGlobal('fetch', fetchMock)
    const res = await api.localStorage()
    expect(res.dirs).toEqual([])
  })

  it('exportAudit POSTs with a limit query', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ rows_exported: 5, path: 'x.csv', limit: 5 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.exportAudit(5)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/limit=5/)
    expect(init.method).toBe('POST')
  })

  it('clearLocalCache appends confirm=true to the URL', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ cleared: true, removed_files: 3, removed_bytes: 100 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.clearLocalCache(true)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/confirm=true/)
    expect(init.method).toBe('POST')
  })

  it('clearLocalCache(false) sends confirm=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ cleared: false, message: 'pass confirm=true' }))
    vi.stubGlobal('fetch', fetchMock)
    await api.clearLocalCache(false)
    expect(fetchMock.mock.calls[0][0]).toMatch(/confirm=false/)
  })

  it('localStatus exists and calls getLocalStatus endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ state: 'online' }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.localStatus()
    expect(result.state).toBe('online')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/local\/status/)
  })

  it('getLocalStatus also works', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ state: 'offline' }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.getLocalStatus()
    expect(result.state).toBe('offline')
  })

  it('getAdminSystemHealth exists and calls correct endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'healthy' }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.getAdminSystemHealth()
    expect(result.status).toBe('healthy')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/admin\/system-health/)
  })

  it('getAdminAIStatus exists and calls correct endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ provider: 'mock', status: 'connected' }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.getAdminAIStatus()
    expect(result.status).toBe('connected')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/admin\/ai-status/)
  })
})
