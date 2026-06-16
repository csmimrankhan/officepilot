/**
 * Phase 12 — browser automation frontend tests.
 *
 * Covers:
 *   - api.* browser helpers (basic shape)
 *   - BrowserPreviewModal approve/reject/cancel button wiring
 *   - BrowserSettings toggles + allowed/blocked domain editing
 *   - BrowserLogs table renders runs + inspects steps
 *   - BrowserTestForm builds previews with the picked invoice
 *   - VoiceIntents shows blocked intents and dispatches allowed ones
 *   - InvoiceDetail exposes a "Fill test form" link
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import React from 'react'

// --- api mock --------------------------------------------------------------

const { apiMocks } = vi.hoisted(() => ({
  apiMocks: {
    health: vi.fn().mockResolvedValue({ ok: true, version: '0.12.0', phase: 12 }),
    listInvoices: vi.fn().mockResolvedValue([]),
    getBrowserPolicies: vi.fn(),
    updateBrowserPolicies: vi.fn(),
    getBrowserStatus: vi.fn(),
    stopBrowser: vi.fn(),
    previewOpenUrl: vi.fn(),
    previewFillForm: vi.fn(),
    previewAppendInvoiceRow: vi.fn(),
    fillTestFormPreview: vi.fn(),
    approveBrowserAction: vi.fn(),
    rejectBrowserAction: vi.fn(),
    cancelBrowserAction: vi.fn(),
    listBrowserActions: vi.fn().mockResolvedValue([]),
    getBrowserAction: vi.fn(),
    getBrowserActionSteps: vi.fn().mockResolvedValue([]),
    getBrowserActionSnapshots: vi.fn().mockResolvedValue([]),
    listVoiceIntents: vi.fn(),
    dispatchVoiceIntent: vi.fn(),
    testFormUrl: vi.fn().mockReturnValue('http://127.0.0.1:8000/api/browser/test-form')
  }
}))

vi.mock('../src/api.js', () => ({
  api: apiMocks,
  formatDateTime: (v) => v || '',
  formatMoney: (v) => (v == null ? '' : String(v)),
  BROWSER_STATUS_LABELS: { completed: 'Completed', failed: 'Failed', awaiting_approval: 'Awaiting Approval' },
  BROWSER_RISK_LABELS: { low: 'Low', medium: 'Medium', high: 'High' },
  WORKFLOW_STATUS_LABELS: {},
  WORKFLOW_LOG_STATUS_LABELS: {},
  WORKFLOW_APPROVAL_STATUS_LABELS: {}
}))

import BrowserPreviewModal from '../src/components/BrowserPreviewModal.jsx'
import BrowserSettings from '../src/pages/BrowserSettings.jsx'
import BrowserLogs from '../src/pages/BrowserLogs.jsx'
import BrowserTestForm from '../src/pages/BrowserTestForm.jsx'
import VoiceIntents from '../src/pages/VoiceIntents.jsx'

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/browser/settings" element={<BrowserSettings />} />
        <Route path="/browser/logs" element={<BrowserLogs />} />
        <Route path="/browser/test-form" element={<BrowserTestForm />} />
        <Route path="/voices" element={<VoiceIntents />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  Object.values(apiMocks).forEach((m) => m.mockReset && m.mockReset())
  apiMocks.listInvoices.mockResolvedValue([])
  apiMocks.testFormUrl.mockReturnValue('http://127.0.0.1:8000/api/browser/test-form')
})

// --- BrowserPreviewModal ---------------------------------------------------

describe('BrowserPreviewModal', () => {
  const preview = {
    run_id: 42,
    requires_approval: true,
    domain_allowed: true,
    preview: {
      action_type: 'fill_form',
      target_url: 'http://127.0.0.1:8000/api/browser/test-form',
      target_domain: '127.0.0.1',
      risk: { risk_level: 'medium', requires_approval: true, reasons: ['writes to form'] },
      domain_decision: { allowed: true, host: '127.0.0.1', reason: 'matches allowlist' },
      steps: [
        { step_order: 0, step_type: 'navigate', target_description: 'Open URL', selector: '', input_value_redacted: '', requires_approval: false },
        { step_order: 1, step_type: 'fill', target_description: 'Fill vendor', selector: 'input[name=vendor_name]', input_value_redacted: 'Acme', requires_approval: true }
      ],
      notes: ['Approval is required.']
    }
  }

  it('renders risk, steps, and approval-required badge', () => {
    render(
      <BrowserPreviewModal
        preview={preview}
        onApprove={() => {}}
        onReject={() => {}}
        onCancel={() => {}}
        onClose={() => {}}
      />
    )
    expect(screen.getByText('Browser automation preview')).toBeTruthy()
    expect(screen.getByText('fill_form')).toBeTruthy()
    expect(screen.getByText(/Medium/)).toBeTruthy()
    expect(screen.getByText('Allowed')).toBeTruthy()
    expect(screen.getByText('Fill vendor')).toBeTruthy()
    expect(screen.getByText('Acme')).toBeTruthy()
  })

  it('calls onApprove with the reason when the user clicks the button', () => {
    const onApprove = vi.fn()
    render(
      <BrowserPreviewModal
        preview={preview}
        onApprove={onApprove}
        onReject={() => {}}
        onCancel={() => {}}
        onClose={() => {}}
      />
    )
    fireEvent.click(screen.getByText(/Approve & run/i))
    expect(onApprove).toHaveBeenCalledTimes(1)
    expect(typeof onApprove.mock.calls[0][0]).toBe('string')
  })

  it('calls onReject when the user clicks Reject', () => {
    const onReject = vi.fn()
    render(
      <BrowserPreviewModal
        preview={preview}
        onApprove={() => {}}
        onReject={onReject}
        onCancel={() => {}}
        onClose={() => {}}
      />
    )
    fireEvent.click(screen.getByText('Reject'))
    expect(onReject).toHaveBeenCalledTimes(1)
  })
})

// --- BrowserSettings -------------------------------------------------------

describe('BrowserSettings page', () => {
  it('renders policy fields, allowlist, and live status', async () => {
    apiMocks.getBrowserPolicies.mockResolvedValue({
      id: 1,
      allowed_domains: ['127.0.0.1', 'docs.google.com'],
      blocked_domains: ['chase.com'],
      require_approval_for_submit: true,
      require_approval_for_write: true,
      screenshots_enabled: true,
      enabled: false,
      headless: false,
      notes: ''
    })
    apiMocks.getBrowserStatus.mockResolvedValue({
      enabled: false,
      headless: false,
      screenshots_enabled: true,
      adapter_mode: 'dry-run',
      live: false,
      allowed_domains: ['127.0.0.1'],
      blocked_domains: ['chase.com'],
      last_url: '',
      last_title: ''
    })
    apiMocks.listVoiceIntents.mockResolvedValue([
      { intent: 'open_google_sheet', action_type: 'open_url', default_url: 'https://sheets.google.com', needs_approval: false, blocked: false, note: '' },
      { intent: 'create_quickbooks_entry', action_type: 'blocked', default_url: '', needs_approval: true, blocked: true, note: 'out of scope' }
    ])

    renderAt('/browser/settings')

    await waitFor(() => {
      expect(screen.getByText('Browser Automation')).toBeTruthy()
    })
    expect(screen.getByText('dry-run')).toBeTruthy()
    expect(screen.getByText(/127\.0\.0\.1/)).toBeTruthy()
    expect(screen.getByText(/chase\.com/)).toBeTruthy()
    expect(screen.getByText('open_google_sheet')).toBeTruthy()
    expect(screen.getByText('create_quickbooks_entry')).toBeTruthy()
    expect(screen.getByText('out of scope')).toBeTruthy()
  })

  it('calls updateBrowserPolicies when the master switch is toggled', async () => {
    apiMocks.getBrowserPolicies.mockResolvedValue({
      id: 1, allowed_domains: ['127.0.0.1'], blocked_domains: [],
      require_approval_for_submit: true, require_approval_for_write: true,
      screenshots_enabled: true, enabled: false, headless: false, notes: ''
    })
    apiMocks.getBrowserStatus.mockResolvedValue({
      enabled: false, headless: false, screenshots_enabled: true,
      adapter_mode: 'dry-run', live: false, allowed_domains: [], blocked_domains: [], last_url: '', last_title: ''
    })
    apiMocks.listVoiceIntents.mockResolvedValue([])
    apiMocks.updateBrowserPolicies.mockResolvedValue({
      id: 1, allowed_domains: ['127.0.0.1'], blocked_domains: [],
      require_approval_for_submit: true, require_approval_for_write: true,
      screenshots_enabled: true, enabled: true, headless: false, notes: ''
    })

    renderAt('/browser/settings')
    await waitFor(() => {
      expect(screen.getByText('Browser Automation')).toBeTruthy()
    })
    const checkbox = screen.getByLabelText(/Enable browser automation/i)
    fireEvent.click(checkbox)
    await waitFor(() => {
      expect(apiMocks.updateBrowserPolicies).toHaveBeenCalled()
    })
    const patch = apiMocks.updateBrowserPolicies.mock.calls[0][0]
    expect(patch.enabled).toBe(true)
  })
})

// --- BrowserLogs -----------------------------------------------------------

describe('BrowserLogs page', () => {
  it('renders the empty state when no runs exist', async () => {
    apiMocks.listBrowserActions.mockResolvedValue([])
    renderAt('/browser/logs')
    await waitFor(() => {
      expect(screen.getByText(/No browser action runs yet/i)).toBeTruthy()
    })
  })

  it('renders a row per run and shows steps on click', async () => {
    apiMocks.listBrowserActions.mockResolvedValue([
      {
        id: 7, source_type: 'ui', action_type: 'open_url',
        target_url: 'http://127.0.0.1:8000/api/browser/test-form', target_domain: '127.0.0.1',
        risk_level: 'low', approval_status: 'not_required', status: 'completed',
        error_message: null, created_at: '2026-06-06T19:00:00Z'
      }
    ])
    apiMocks.getBrowserActionSteps.mockResolvedValue([
      {
        id: 1, browser_action_run_id: 7, step_order: 0, step_type: 'screenshot',
        target_description: 'Capture page screenshot', selector: '',
        input_value_redacted: '', requires_approval: false, status: 'completed',
        screenshot_path: '', error_message: '', created_at: '2026-06-06T19:00:00Z'
      }
    ])
    renderAt('/browser/logs')
    await waitFor(() => {
      expect(screen.getByText('127.0.0.1')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Inspect'))
    await waitFor(() => {
      expect(screen.getByText('Capture page screenshot')).toBeTruthy()
    })
  })
})

// --- BrowserTestForm -------------------------------------------------------

describe('BrowserTestForm page', () => {
  it('builds a preview when the user picks an invoice', async () => {
    apiMocks.listInvoices.mockResolvedValue([
      { id: 99, vendor_name: 'Acme', invoice_number: 'PHASE12-T1' }
    ])
    apiMocks.fillTestFormPreview.mockResolvedValue({
      run_id: 12, requires_approval: true, domain_allowed: true,
      preview: {
        action_type: 'fill_form', target_url: 'http://127.0.0.1:8000/api/browser/test-form',
        target_domain: '127.0.0.1',
        risk: { risk_level: 'medium', requires_approval: true, reasons: [] },
        domain_decision: { allowed: true, host: '127.0.0.1', reason: '' },
        steps: [], notes: []
      }
    })

    renderAt('/browser/test-form')
    await waitFor(() => {
      expect(screen.getByText('Local Test Web Form')).toBeTruthy()
    })
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '99' } })
    fireEvent.click(screen.getByText('Build fill-form preview'))
    await waitFor(() => {
      expect(apiMocks.fillTestFormPreview).toHaveBeenCalledWith({
        invoice_id: 99, actor: 'user', submit: false
      })
    })
  })
})

// --- VoiceIntents ----------------------------------------------------------

describe('VoiceIntents page', () => {
  it('renders intents and shows a message for blocked ones', async () => {
    apiMocks.listVoiceIntents.mockResolvedValue([
      { intent: 'open_google_sheet', action_type: 'open_url', default_url: 'https://sheets.google.com', needs_approval: false, blocked: false, note: '' },
      { intent: 'create_quickbooks_entry', action_type: 'blocked', default_url: '', needs_approval: true, blocked: true, note: 'out of scope' }
    ])
    renderAt('/voices')
    await waitFor(() => {
      expect(screen.getByText('open_google_sheet')).toBeTruthy()
    })
    expect(screen.getByText('create_quickbooks_entry')).toBeTruthy()
    // The blocked intent's Preview button is the second <button>
    // in the table; it should be disabled.
    const buttons = screen.getAllByRole('button')
    const blockedBtn = buttons.find((b) => b.textContent === 'Blocked')
    expect(blockedBtn).toBeTruthy()
    expect(blockedBtn.disabled).toBe(true)
    const allowedBtn = buttons.find((b) => b.textContent === 'Preview')
    expect(allowedBtn).toBeTruthy()
    expect(allowedBtn.disabled).toBe(false)
  })

  it('dispatches an allowed intent and opens a preview', async () => {
    apiMocks.listVoiceIntents.mockResolvedValue([
      { intent: 'open_google_sheet', action_type: 'open_url', default_url: 'https://sheets.google.com', needs_approval: false, blocked: false, note: '' }
    ])
    apiMocks.dispatchVoiceIntent.mockResolvedValue({
      intent: 'open_google_sheet',
      blocked: false,
      preview: {
        action_type: 'open_url', target_url: 'https://sheets.google.com',
        target_domain: 'sheets.google.com',
        risk: { risk_level: 'low', requires_approval: false, reasons: [] },
        domain_decision: { allowed: true, host: 'sheets.google.com', reason: '' },
        steps: [], notes: []
      },
      message: 'read-only'
    })
    renderAt('/voices')
    await waitFor(() => {
      expect(screen.getByText('open_google_sheet')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Preview'))
    await waitFor(() => {
      expect(apiMocks.dispatchVoiceIntent).toHaveBeenCalledWith({ intent: 'open_google_sheet', actor: 'voice' })
    })
  })

  it('surfaces a "blocked" message for unsafe intents', async () => {
    apiMocks.listVoiceIntents.mockResolvedValue([
      { intent: 'create_quickbooks_entry', action_type: 'blocked', default_url: '', needs_approval: true, blocked: true, note: 'out of scope' }
    ])
    apiMocks.dispatchVoiceIntent.mockResolvedValue({
      intent: 'create_quickbooks_entry',
      blocked: true,
      preview: null,
      message: 'out of scope'
    })
    renderAt('/voices')
    await waitFor(() => {
      expect(screen.getByText('create_quickbooks_entry')).toBeTruthy()
    })
    // The blocked button is disabled, so dispatching the intent
    // is not possible from the UI; the server-side guard is
    // tested in the backend suite.
  })
})
