import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import EmailIntegrations from '../src/pages/EmailIntegrations.jsx'
import ImportedEmails from '../src/pages/ImportedEmails.jsx'
import ImportedEmailDetail from '../src/pages/ImportedEmailDetail.jsx'
import SourceBadge from '../src/components/SourceBadge.jsx'

vi.mock('../src/api.js', () => {
  return {
    api: {
      base: 'http://test',
      gmailStatus: vi.fn(),
      gmailConnect: vi.fn(),
      gmailSync: vi.fn(),
      gmailDisconnect: vi.fn(),
      listEmailImports: vi.fn(),
      getEmailImport: vi.fn()
    },
    formatDateTime: (v) => (v ? new Date(v).toISOString() : ''),
    formatMoney: (v, c) => (v == null ? '' : `${c || '$'}${Number(v).toFixed(2)}`),
    IMPORT_STATUS_LABELS: {
      candidate: 'Candidate', imported: 'Imported', duplicate: 'Duplicate',
      skipped: 'Skipped', error: 'Error'
    }
  }
})

import { api } from '../src/api.js'

beforeEach(() => vi.clearAllMocks())

describe('SourceBadge', () => {
  it('shows Email for email source', () => {
    render(<SourceBadge source="email" emailImportId={12} />)
    expect(screen.getByText('Email')).toBeInTheDocument()
  })
  it('shows Upload for manual source', () => {
    render(<SourceBadge source="upload" />)
    expect(screen.getByText('Upload')).toBeInTheDocument()
  })
})

describe('EmailIntegrations', () => {
  it('renders not-configured state and disables connect button', async () => {
    api.gmailStatus.mockResolvedValueOnce({
      configured: false, connected: false, account: null, scopes: [],
      note: 'OAuth not configured.'
    })
    render(<MemoryRouter><EmailIntegrations /></MemoryRouter>)
    expect(await screen.findByText(/Not configured/)).toBeInTheDocument()
    expect(screen.getByText(/OAuth not configured/)).toBeInTheDocument()
    const btn = screen.getByText(/Connect Gmail/)
    expect(btn).toBeDisabled()
  })

  it('shows Sync + Disconnect when connected', async () => {
    api.gmailStatus.mockResolvedValueOnce({
      configured: true, connected: true,
      account: { id: 1, email: 'me@example.com', status: 'connected', connected_at: '2026-01-01T00:00:00Z' },
      scopes: ['https://www.googleapis.com/auth/gmail.readonly']
    })
    render(<MemoryRouter><EmailIntegrations /></MemoryRouter>)
    expect(await screen.findByText('Sync Invoice Emails')).toBeInTheDocument()
    expect(screen.getByText('Disconnect')).toBeInTheDocument()
    expect(screen.getByText('me@example.com')).toBeInTheDocument()
  })

  it('calls api.gmailSync when Sync is clicked', async () => {
    api.gmailStatus.mockResolvedValue({
      configured: true, connected: true,
      account: { id: 1, email: 'me@example.com', status: 'connected', connected_at: '2026-01-01T00:00:00Z' },
      scopes: ['https://www.googleapis.com/auth/gmail.readonly']
    })
    api.gmailSync.mockResolvedValueOnce({ candidates: 2, imported: 1, duplicates: 1, skipped: 0, errors: 0, invoice_ids: [42] })
    render(<MemoryRouter><EmailIntegrations /></MemoryRouter>)
    fireEvent.click(await screen.findByText('Sync Invoice Emails'))
    await waitFor(() => expect(api.gmailSync).toHaveBeenCalled())
    expect(await screen.findByText('Last sync report')).toBeInTheDocument()
  })
})

describe('ImportedEmails', () => {
  it('renders rows from the API', async () => {
    api.listEmailImports.mockResolvedValueOnce([
      { id: 1, subject: 'Invoice INV-1', sender: 'b@x.com', received_at: '2026-01-01T00:00:00Z', score: 0.7, status: 'imported', attachments: [{}] }
    ])
    render(<MemoryRouter><ImportedEmails /></MemoryRouter>)
    expect(await screen.findByText('Invoice INV-1')).toBeInTheDocument()
    expect(screen.getByText('b@x.com')).toBeInTheDocument()
    // "Imported" appears both in the status filter dropdown and in the row;
    // we use getAllByText to assert presence without ambiguity.
    expect(screen.getAllByText('Imported').length).toBeGreaterThan(0)
  })

  it('shows empty state when no imports', async () => {
    api.listEmailImports.mockResolvedValueOnce([])
    render(<MemoryRouter><ImportedEmails /></MemoryRouter>)
    expect(await screen.findByText(/No imported emails yet/)).toBeInTheDocument()
  })
})

describe('ImportedEmailDetail', () => {
  it('renders scoring breakdown and attachment list', async () => {
    api.getEmailImport.mockResolvedValueOnce({
      id: 9, provider_message_id: 'm-9', subject: 'Invoice INV-9',
      sender: 'a@b.com', received_at: '2026-01-01T00:00:00Z',
      score: 0.65, status: 'imported',
      snippet: 'see attached',
      score_breakdown: { matched: ['subject:invoice', 'filename:invoice'], reasons: ['matched'] },
      attachments: [
        { id: 1, filename: 'inv.pdf', mime_type: 'application/pdf', size: 100, status: 'imported', processed_invoice_id: 12 }
      ]
    })
    render(
      <MemoryRouter initialEntries={['/imported-emails/9']}>
        <Routes>
          <Route path="/imported-emails/:id" element={<ImportedEmailDetail />} />
        </Routes>
      </MemoryRouter>
    )
    expect(await screen.findByText('Email Import #9')).toBeInTheDocument()
    expect(screen.getByText('subject:invoice')).toBeInTheDocument()
    expect(screen.getByText('inv.pdf')).toBeInTheDocument()
    expect(screen.getByText('#12')).toBeInTheDocument()
  })
})
