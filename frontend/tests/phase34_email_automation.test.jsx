import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import GmailConnectCard from '../src/components/agent/GmailConnectCard.jsx'
import EmailSearchPreviewCard from '../src/components/agent/EmailSearchPreviewCard.jsx'
import AttachmentDownloadCard from '../src/components/agent/AttachmentDownloadCard.jsx'
import EmailDownloadResultCard from '../src/components/agent/EmailDownloadResultCard.jsx'

// ── GmailConnectCard ──────────────────────────────────────────────

describe('GmailConnectCard', () => {
  it('renders disconnect state when disconnected', () => {
    render(<GmailConnectCard status="disconnected" />)
    expect(screen.getByText(/Not connected/i)).toBeTruthy()
  })

  it('renders connect button when disconnected', () => {
    render(<GmailConnectCard status="disconnected" />)
    expect(screen.getByText('Connect Gmail')).toBeTruthy()
  })

  it('renders connected state', () => {
    render(<GmailConnectCard status="connected" email="test@gmail.com" />)
    expect(screen.getByText(/Connected:/i)).toBeTruthy()
  })

  it('renders read-only privacy note', () => {
    render(<GmailConnectCard status="disconnected" />)
    const notes = screen.getAllByText(/read-only/i)
    expect(notes.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/gmail.readonly/i)).toBeTruthy()
  })

  it('renders mock status', () => {
    render(<GmailConnectCard status="mock" email="mock-user@gmail.com" />)
    expect(screen.getByText(/Mock:/i)).toBeTruthy()
  })

  it('calls onConnect when connect button clicked', () => {
    const onConnect = vi.fn()
    render(<GmailConnectCard status="disconnected" onConnect={onConnect} />)
    fireEvent.click(screen.getByText('Connect Gmail'))
    expect(onConnect).toHaveBeenCalledOnce()
  })

  it('disables connect button when loading', () => {
    render(<GmailConnectCard status="disconnected" onConnect={() => {}} loading />)
    expect(screen.getByText('Connecting...')).toBeTruthy()
  })
})

// ── EmailSearchPreviewCard ────────────────────────────────────────

const mockMessages = [
  {
    message_id: 'msg-1',
    from: 'vendor@example.com',
    subject: 'Invoice #1001',
    date: '2024-02-15T10:00:00',
    snippet: 'Invoice attached',
    has_attachments: true,
    attachments: [{ filename: 'invoice_1001.pdf', size: 32768 }],
  },
  {
    message_id: 'msg-2',
    from: 'billing@company.com',
    subject: 'Receipt for subscription',
    date: '2024-02-14T14:00:00',
    snippet: 'Receipt attached',
    has_attachments: false,
    attachments: [],
  },
]

describe('EmailSearchPreviewCard', () => {
  it('renders messages', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} query="test" />)
    expect(screen.getByText(/2 message/)).toBeTruthy()
    expect(screen.getByText('Invoice #1001')).toBeTruthy()
    expect(screen.getByText('Receipt for subscription')).toBeTruthy()
  })

  it('renders from addresses', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} />)
    expect(screen.getByText('vendor@example.com')).toBeTruthy()
    expect(screen.getByText('billing@company.com')).toBeTruthy()
  })

  it('renders attachment badges', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} />)
    expect(screen.getByText(/1 att/)).toBeTruthy()
    expect(screen.getByText(/no att/)).toBeTruthy()
  })

  it('renders attachment details on expand', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} />)
    const msg = screen.getByText('Invoice #1001').closest('div[class*="email-preview-msg"]') || screen.getByText('Invoice #1001')
    fireEvent.click(msg)
    expect(screen.getByText('invoice_1001.pdf')).toBeTruthy()
  })

  it('shows approve button when messages selected', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} selectedIds={['msg-1']} />)
    expect(screen.getByText(/Approve & Download/)).toBeTruthy()
  })

  it('disables approve button when no messages selected', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={2} selectedIds={[]} />)
    const btn = screen.getByText(/Approve & Download/)
    expect(btn.disabled).toBe(true)
  })
})

// ── AttachmentDownloadCard ────────────────────────────────────────

const mockAttachments = [
  { filename: 'invoice_1001.pdf', size: 32768 },
  { filename: 'data.xlsx', size: 45056 },
]

describe('AttachmentDownloadCard', () => {
  it('renders attachment list', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} />)
    expect(screen.getByText('invoice_1001.pdf')).toBeTruthy()
    expect(screen.getByText('data.xlsx')).toBeTruthy()
  })

  it('renders approval warning', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} />)
    expect(screen.getByText(/approve to proceed/i)).toBeTruthy()
  })

  it('renders download button', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} />)
    expect(screen.getByText(/Approve & Download/)).toBeTruthy()
  })

  it('shows folder input always', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={() => {}} />)
    expect(screen.getByPlaceholderText(/Invoices/)).toBeTruthy()
  })

  it('calls onDownload when folder provided', () => {
    const onDownload = vi.fn()
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={onDownload} />)
    const input = screen.getByPlaceholderText(/Invoices/)
    fireEvent.change(input, { target: { value: '/tmp/invoices' } })
    fireEvent.click(screen.getByText(/Approve & Download/))
    expect(onDownload).toHaveBeenCalled()
  })

  it('renders cancel button', () => {
    const onCancel = vi.fn()
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={() => {}} onCancel={onCancel} />)
    expect(screen.getByText('Cancel')).toBeTruthy()
  })
})

// ── EmailDownloadResultCard ───────────────────────────────────────

const mockDownloads = [
  { filename: 'invoice_1001.pdf', size_bytes: 32768, mime_type: 'application/pdf' },
  { filename: 'data.xlsx', size_bytes: 45056, mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
]

describe('EmailDownloadResultCard', () => {
  it('renders saved files', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} outputFolder="/tmp/invoices" />)
    expect(screen.getByText('invoice_1001.pdf')).toBeTruthy()
    expect(screen.getByText('data.xlsx')).toBeTruthy()
  })

  it('shows Create Excel Summary button for spreadsheet downloads', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onCreateExcelSummary={() => {}} />)
    expect(screen.getByText('Create Excel Summary')).toBeTruthy()
  })

  it('shows spreadsheet hint', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onCreateExcelSummary={() => {}} />)
    expect(screen.getByText(/Spreadsheet attachments detected/)).toBeTruthy()
  })

  it('shows Open Folder button', () => {
    const onOpenFolder = vi.fn()
    render(<EmailDownloadResultCard downloads={mockDownloads} onOpenFolder={onOpenFolder} />)
    expect(screen.getByText('Open Folder')).toBeTruthy()
  })

  it('shows Save as Skill button', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onSaveAsSkill={() => {}} />)
    expect(screen.getByText('Save as Skill')).toBeTruthy()
  })

  it('shows Clear button', () => {
    const onClear = vi.fn()
    render(<EmailDownloadResultCard downloads={mockDownloads} onClear={onClear} />)
    expect(screen.getByText('Clear')).toBeTruthy()
  })

  it('returns null with no downloads', () => {
    const { container } = render(<EmailDownloadResultCard downloads={[]} />)
    expect(container.innerHTML).toBeFalsy()
  })
})
