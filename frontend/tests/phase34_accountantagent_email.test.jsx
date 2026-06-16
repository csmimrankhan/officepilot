import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { normalizeEmailStepResult } from '../src/utils/normalizeEmailStepResult.js'

// ── normalizeEmailStepResult ────────────────────────────────────────

describe('normalizeEmailStepResult', () => {
  it('returns unknown for null input', () => {
    const result = normalizeEmailStepResult(null, '')
    expect(result.type).toBe('unknown')
    expect(result.cardType).toBeNull()
  })

  it('returns blocked_warning for blocked status', () => {
    const result = normalizeEmailStepResult(
      { status: 'blocked', message: 'No Gmail account connected', output: {} },
      'email_search'
    )
    expect(result.type).toBe('blocked')
    expect(result.cardType).toBe('blocked_warning')
    expect(result.reason).toContain('No Gmail account')
  })

  it('returns needs_connection for connection required', () => {
    const result = normalizeEmailStepResult(
      { output: { needs_connection: true, provider: 'gmail', authorization_url: 'https://accounts.google.com/o/oauth2/auth', status: 'needs_connection' } },
      'email_connect_gmail'
    )
    expect(result.type).toBe('needs_connection')
    expect(result.cardType).toBe('gmail_connect')
    expect(result.provider).toBe('gmail')
    expect(result.authorizationUrl).toContain('accounts.google.com')
  })

  it('returns connected for successful connection', () => {
    const result = normalizeEmailStepResult(
      { output: { connected: true, email: 'test@gmail.com', account_id: 42, status: 'connected' } },
      'email_connect_gmail'
    )
    expect(result.type).toBe('connected')
    expect(result.cardType).toBe('gmail_connected')
    expect(result.email).toBe('test@gmail.com')
    expect(result.accountId).toBe(42)
  })

  it('returns mock_connected for mock mode', () => {
    const result = normalizeEmailStepResult(
      { output: { connected: true, email: 'mock-user@gmail.com', status: 'mock', mode: 'mock' } },
      'email_connect_gmail'
    )
    expect(result.type).toBe('connected')
    expect(result.cardType).toBe('gmail_mock')
    expect(result.mode).toBe('mock')
  })

  it('returns search_results for email search output', () => {
    const messages = [{ message_id: 'msg-1', subject: 'Invoice' }]
    const result = normalizeEmailStepResult(
      { output: { email_search_results: true, messages, result_count: 1 } },
      'email_search'
    )
    expect(result.type).toBe('search_results')
    expect(result.cardType).toBe('email_search')
    expect(result.messages).toHaveLength(1)
    expect(result.resultCount).toBe(1)
  })

  it('returns preview for email preview output', () => {
    const result = normalizeEmailStepResult(
      { output: { email_preview: true, message_id: 'msg-1', from: 'vendor@co.com', subject: 'Invoice #42' } },
      'email_preview_messages'
    )
    expect(result.type).toBe('preview')
    expect(result.cardType).toBe('email_preview')
    expect(result.subject).toBe('Invoice #42')
  })

  it('returns download_success for attachment download output', () => {
    const downloads = [{ filename: 'invoice.pdf', filepath: '/tmp/invoice.pdf' }]
    const result = normalizeEmailStepResult(
      { output: { attachment_download_success: true, downloads, total_downloaded: 1, output_folder: '/tmp', has_spreadsheet: false } },
      'email_download_attachments'
    )
    expect(result.type).toBe('download_success')
    expect(result.cardType).toBe('email_download_result')
    expect(result.downloads).toHaveLength(1)
    expect(result.outputFolder).toBe('/tmp')
  })

  it('returns needs_folder for missing output folder', () => {
    const result = normalizeEmailStepResult(
      { output: { needs_input: true, field: 'output_folder', field_type: 'folder_picker', message: 'Output folder required' } },
      'email_download_attachments'
    )
    expect(result.type).toBe('needs_folder')
    expect(result.cardType).toBe('needs_folder_input')
    expect(result.field).toBe('output_folder')
  })

  it('returns file_saved for save attachment output', () => {
    const result = normalizeEmailStepResult(
      { output: { saved_path: '/tmp/invoice.pdf', filename: 'invoice.pdf' } },
      'email_save_attachment'
    )
    expect(result.type).toBe('file_saved')
    expect(result.cardType).toBe('email_file_saved')
    expect(result.savedPath).toBe('/tmp/invoice.pdf')
  })

  it('returns disconnected for disconnect output', () => {
    const result = normalizeEmailStepResult(
      { output: { disconnected: true, email: 'test@gmail.com' } },
      'email_disconnect_account'
    )
    expect(result.type).toBe('disconnected')
    expect(result.cardType).toBe('gmail_disconnected')
    expect(result.email).toBe('test@gmail.com')
  })

  it('returns needs_input for various missing fields', () => {
    const result = normalizeEmailStepResult(
      { output: { needs_input: true, field: 'message_id' } },
      'email_preview_messages'
    )
    expect(result.type).toBe('needs_message_id')
    expect(result.cardType).toBe('needs_input')

    const queryResult = normalizeEmailStepResult(
      { output: { needs_input: true, field: 'query' } },
      'email_search'
    )
    expect(queryResult.type).toBe('needs_query')

    const fpResult = normalizeEmailStepResult(
      { output: { needs_input: true, field: 'filepath' } },
      'email_save_attachment'
    )
    expect(fpResult.type).toBe('needs_filepath')
  })

  it('returns draft_created for draft output', () => {
    const result = normalizeEmailStepResult(
      { output: { draft_created: true, to: 'test@co.com', subject: 'Invoice' } },
      'email_create_draft'
    )
    expect(result.type).toBe('draft_created')
    expect(result.cardType).toBe('email_draft')
  })

  it('returns email_status for unrecognized email tool output', () => {
    const result = normalizeEmailStepResult(
      { status: 'ok', message: 'done', output: { email_id: 'msg-1' } },
      'email_open_message'
    )
    expect(result.type).toBe('email_status')
    expect(result.cardType).toBe('email_status')
  })
})

describe('GmailConnectCard integration', () => {
  let GmailConnectCard

  beforeEach(async () => {
    GmailConnectCard = (await import('../src/components/agent/GmailConnectCard.jsx')).default
  })

  it('renders disconnected state from needs_connection step state', () => {
    render(<GmailConnectCard status="disconnected" />)
    expect(screen.getByText(/Not connected/i)).toBeInTheDocument()
    expect(screen.getByText('Connect Gmail')).toBeInTheDocument()
  })

  it('renders connected state from connected step state', () => {
    render(<GmailConnectCard status="connected" email="user@gmail.com" />)
    expect(screen.getByText(/Connected:/i)).toBeInTheDocument()
    expect(screen.queryByText('Connect Gmail')).not.toBeInTheDocument()
  })

  it('renders mock state from mock step state', () => {
    render(<GmailConnectCard status="mock" email="mock-user@gmail.com" />)
    expect(screen.getByText(/Mock:/i)).toBeInTheDocument()
  })

  it('calls onConnect when button clicked', () => {
    const onConnect = vi.fn()
    render(<GmailConnectCard status="disconnected" onConnect={onConnect} />)
    fireEvent.click(screen.getByText('Connect Gmail'))
    expect(onConnect).toHaveBeenCalledOnce()
  })

  it('shows loading state during connection', () => {
    render(<GmailConnectCard status="disconnected" onConnect={() => {}} loading />)
    expect(screen.getByText('Connecting...')).toBeInTheDocument()
  })
})

// ── EmailSearchPreviewCard integration ──────────────────────────────

describe('EmailSearchPreviewCard integration', () => {
  let EmailSearchPreviewCard

  beforeEach(async () => {
    EmailSearchPreviewCard = (await import('../src/components/agent/EmailSearchPreviewCard.jsx')).default
  })

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
  ]

  it('renders with messages from search results state', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={1} />)
    expect(screen.getByText(/1 message/)).toBeInTheDocument()
    expect(screen.getByText('Invoice #1001')).toBeInTheDocument()
  })

  it('shows approve button when messages selected', () => {
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={1} selectedIds={['msg-1']} />)
    expect(screen.getByText(/Approve & Download/)).toBeInTheDocument()
  })

  it('calls onApproveDownload with selection', () => {
    const onApproveDownload = vi.fn()
    render(<EmailSearchPreviewCard messages={mockMessages} resultCount={1} selectedIds={['msg-1']} onApproveDownload={onApproveDownload} />)
    fireEvent.click(screen.getByText(/Approve & Download/))
    expect(onApproveDownload).toHaveBeenCalledWith(['msg-1'])
  })
})

// ── AttachmentDownloadCard integration ──────────────────────────────

describe('AttachmentDownloadCard integration', () => {
  let AttachmentDownloadCard

  beforeEach(async () => {
    AttachmentDownloadCard = (await import('../src/components/agent/AttachmentDownloadCard.jsx')).default
  })

  const mockAttachments = [
    { filename: 'invoice_1001.pdf', size: 32768 },
    { filename: 'data.xlsx', size: 45056 },
  ]

  it('renders attachments list from awaiting_folder state', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} />)
    expect(screen.getByText('invoice_1001.pdf')).toBeInTheDocument()
    expect(screen.getByText('data.xlsx')).toBeInTheDocument()
  })

  it('shows folder input always', () => {
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={() => {}} />)
    expect(screen.getByPlaceholderText(/Invoices/)).toBeInTheDocument()
  })

  it('calls onDownload with messageIds and folder path', () => {
    const onDownload = vi.fn()
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={onDownload} />)
    const input = screen.getByPlaceholderText(/Invoices/)
    fireEvent.change(input, { target: { value: '/tmp/invoices' } })
    fireEvent.click(screen.getByText(/Approve & Download/))
    expect(onDownload).toHaveBeenCalledWith(['msg-1'], '/tmp/invoices')
  })

  it('renders cancel button', () => {
    const onCancel = vi.fn()
    render(<AttachmentDownloadCard attachments={mockAttachments} messageIds={['msg-1']} onDownload={() => {}} onCancel={onCancel} />)
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })
})

// ── EmailDownloadResultCard integration ────────────────────────────

describe('EmailDownloadResultCard integration', () => {
  let EmailDownloadResultCard

  beforeEach(async () => {
    EmailDownloadResultCard = (await import('../src/components/agent/EmailDownloadResultCard.jsx')).default
  })

  const mockDownloads = [
    { filename: 'invoice_1001.pdf', size_bytes: 32768, mime_type: 'application/pdf' },
    { filename: 'data.xlsx', size_bytes: 45056, mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
  ]

  it('renders downloaded files from download_success state', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} outputFolder="/tmp/invoices" />)
    expect(screen.getByText('invoice_1001.pdf')).toBeInTheDocument()
    expect(screen.getByText('data.xlsx')).toBeInTheDocument()
  })

  it('shows Create Excel Summary button when passed as prop', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onCreateExcelSummary={() => {}} />)
    expect(screen.getByText('Create Excel Summary')).toBeInTheDocument()
  })

  it('shows Save as Skill button when passed as prop', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onSaveAsSkill={() => {}} />)
    expect(screen.getByText('Save as Skill')).toBeInTheDocument()
  })

  it('shows Open Folder button when passed as prop', () => {
    render(<EmailDownloadResultCard downloads={mockDownloads} onOpenFolder={() => {}} />)
    expect(screen.getByText('Open Folder')).toBeInTheDocument()
  })

  it('calls onCreateExcelSummary when button clicked', () => {
    const onCreateExcelSummary = vi.fn()
    render(<EmailDownloadResultCard downloads={mockDownloads} onCreateExcelSummary={onCreateExcelSummary} />)
    fireEvent.click(screen.getByText('Create Excel Summary'))
    expect(onCreateExcelSummary).toHaveBeenCalledOnce()
  })

  it('calls onClear when Clear button clicked', () => {
    const onClear = vi.fn()
    render(<EmailDownloadResultCard downloads={mockDownloads} onClear={onClear} />)
    fireEvent.click(screen.getByText('Clear'))
    expect(onClear).toHaveBeenCalledOnce()
  })

  it('returns null with empty downloads', () => {
    const { container } = render(<EmailDownloadResultCard downloads={[]} />)
    expect(container.innerHTML).toBeFalsy()
  })
})
