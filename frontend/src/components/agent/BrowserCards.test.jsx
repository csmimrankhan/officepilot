import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BrowserAutomationCard from './BrowserAutomationCard.jsx'
import ManualLoginCard from './ManualLoginCard.jsx'
import GuidedDownloadCard from './GuidedDownloadCard.jsx'
import BrowserResultCard from './BrowserResultCard.jsx'

// ── BrowserAutomationCard ────────────────────────────────────────────────

describe('BrowserAutomationCard', () => {
  it('renders null when no url and no status', () => {
    const { container } = render(<BrowserAutomationCard />)
    expect(container.innerHTML).toBe('')
  })

  it('renders URL and status', () => {
    render(<BrowserAutomationCard url="https://example.com" status="waiting_login" />)
    expect(screen.getByText('https://example.com')).toBeTruthy()
    expect(screen.getByText('waiting login')).toBeTruthy()
  })

  it('renders risk level badge', () => {
    render(<BrowserAutomationCard url="https://example.com" riskLevel="medium" />)
    expect(screen.getByText('medium')).toBeTruthy()
  })

  it('shows screenshot toggle when screenshotUrl provided', () => {
    render(<BrowserAutomationCard url="https://example.com" screenshotUrl="/snap/1.png" />)
    expect(screen.getByText('Show Screenshot')).toBeTruthy()
    fireEvent.click(screen.getByText('Show Screenshot'))
    expect(screen.getByText('Hide Screenshot')).toBeTruthy()
  })

  it('shows Take Screenshot button when onScreenshot provided', () => {
    const onScreenshot = vi.fn()
    render(<BrowserAutomationCard url="https://example.com" onScreenshot={onScreenshot} />)
    expect(screen.getByText('Take Screenshot')).toBeTruthy()
    fireEvent.click(screen.getByText('Take Screenshot'))
    expect(onScreenshot).toHaveBeenCalled()
  })

  it('renders next action text', () => {
    render(<BrowserAutomationCard url="https://example.com" nextAction="Log in manually" />)
    expect(screen.getByText(/Next: Log in manually/)).toBeTruthy()
  })
})

// ── ManualLoginCard ───────────────────────────────────────────────────────

describe('ManualLoginCard', () => {
  const defaultProps = {
    website: 'https://example.com',
    onLoggedIn: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders website and safety note', () => {
    render(<ManualLoginCard {...defaultProps} />)
    expect(screen.getByText('https://example.com')).toBeTruthy()
    expect(screen.getByText(/does not store or type your password/i)).toBeTruthy()
  })

  it('renders "I am logged in" button', () => {
    render(<ManualLoginCard {...defaultProps} />)
    expect(screen.getByText("✓ I am logged in")).toBeTruthy()
  })

  it('renders Cancel button', () => {
    render(<ManualLoginCard {...defaultProps} />)
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('calls onLoggedIn when button clicked', () => {
    const onLoggedIn = vi.fn()
    render(<ManualLoginCard {...defaultProps} onLoggedIn={onLoggedIn} />)
    fireEvent.click(screen.getByText("✓ I am logged in"))
    expect(onLoggedIn).toHaveBeenCalled()
  })

  it('calls onCancel when Cancel clicked', () => {
    const onCancel = vi.fn()
    render(<ManualLoginCard {...defaultProps} onCancel={onCancel} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('disables buttons when loading', () => {
    render(<ManualLoginCard {...defaultProps} loading={true} />)
    expect(screen.getByText('...')).toBeTruthy()
  })

  it('shows status text', () => {
    render(<ManualLoginCard {...defaultProps} status="waiting_login" />)
    expect(screen.getByText('waiting login')).toBeTruthy()
  })

  it('renders title', () => {
    render(<ManualLoginCard {...defaultProps} />)
    expect(screen.getByText(/Manual Login Required/)).toBeTruthy()
  })
})

// ── GuidedDownloadCard ────────────────────────────────────────────────────

describe('GuidedDownloadCard', () => {
  it('renders waiting state with spinner', () => {
    render(<GuidedDownloadCard watchedFolder="C:\\Downloads" waiting={true} />)
    expect(screen.getByText(/Waiting for exported file/)).toBeTruthy()
    expect(screen.getByText(/Downloads/)).toBeTruthy()
  })

  it('renders detected file state', () => {
    render(<GuidedDownloadCard detectedFile="report.xlsx" />)
    expect(screen.getByText(/File detected/)).toBeTruthy()
    expect(screen.getByText('report.xlsx')).toBeTruthy()
  })

  it('shows output path when detected', () => {
    render(<GuidedDownloadCard detectedFile="report.xlsx" outputPath="C:\\output\\report.xlsx" />)
    expect(screen.getAllByText(/output/).length).toBeGreaterThanOrEqual(1)
  })

  it('shows Continue button when file detected and onContinue provided', () => {
    const onContinue = vi.fn()
    render(<GuidedDownloadCard detectedFile="report.xlsx" onContinue={onContinue} />)
    expect(screen.getByText('Continue')).toBeTruthy()
    fireEvent.click(screen.getByText('Continue'))
    expect(onContinue).toHaveBeenCalled()
  })

  it('shows Cancel button when onCancel provided', () => {
    render(<GuidedDownloadCard waiting={true} onCancel={vi.fn()} />)
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('shows Skip button when file detected and Cancel clicked', () => {
    render(<GuidedDownloadCard detectedFile="report.xlsx" onCancel={vi.fn()} />)
    expect(screen.getByText('Skip')).toBeTruthy()
  })

  it('renders title', () => {
    render(<GuidedDownloadCard waiting={true} />)
    expect(screen.getByText(/Guided Download/)).toBeTruthy()
  })
})

// ── BrowserResultCard ─────────────────────────────────────────────────────

describe('BrowserResultCard', () => {
  it('renders null when no file info', () => {
    const { container } = render(<BrowserResultCard />)
    expect(container.innerHTML).toBe('')
  })

  it('renders file path and name', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" filename="report.xlsx" />)
    expect(screen.getByText(/Report Downloaded/)).toBeTruthy()
    expect(screen.getByText('report.xlsx')).toBeTruthy()
    expect(screen.getByText(/output/)).toBeTruthy()
  })

  it('shows Open File button when onOpenFile provided', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" onOpenFile={vi.fn()} />)
    expect(screen.getByText('Open File')).toBeTruthy()
  })

  it('shows Create Excel Summary button for Excel files', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" onCreateExcelSummary={vi.fn()} />)
    expect(screen.getByText('Create Excel Summary')).toBeTruthy()
  })

  it('shows Create Excel Summary button for CSV files', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.csv" onCreateExcelSummary={vi.fn()} />)
    expect(screen.getByText('Create Excel Summary')).toBeTruthy()
  })

  it('hides Create Excel Summary for non-Excel/CSV files', () => {
    const { queryByText } = render(
      <BrowserResultCard filePath="C:\\output\\report.pdf" onCreateExcelSummary={vi.fn()} />
    )
    expect(queryByText('Create Excel Summary')).toBeNull()
  })

  it('shows Save as Skill button when onSaveAsSkill provided', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" onSaveAsSkill={vi.fn()} />)
    expect(screen.getByText('Save as Skill')).toBeTruthy()
  })

  it('shows excel summary hint for Excel files', () => {
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" />)
    expect(screen.getByText(/auto-detect columns/)).toBeTruthy()
  })

  it('calls onOpenFile when button clicked', () => {
    const onOpenFile = vi.fn()
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" onOpenFile={onOpenFile} />)
    fireEvent.click(screen.getByText('Open File'))
    expect(onOpenFile).toHaveBeenCalled()
  })

  it('calls onCreateExcelSummary when button clicked', () => {
    const onCreateExcelSummary = vi.fn()
    render(<BrowserResultCard filePath="C:\\output\\report.xlsx" onCreateExcelSummary={onCreateExcelSummary} />)
    fireEvent.click(screen.getByText('Create Excel Summary'))
    expect(onCreateExcelSummary).toHaveBeenCalled()
  })
})
