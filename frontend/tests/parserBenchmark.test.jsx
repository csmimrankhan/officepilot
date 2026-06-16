import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ParserBenchmark from '../src/pages/ParserBenchmark.jsx'

vi.mock('../src/api.js', () => ({
  api: {
    listParserEngines: vi.fn(),
    runParserBenchmark: vi.fn()
  }
}))

import { api } from '../src/api.js'

const fakeEngines = {
  engines: [
    { name: 'existing', class: 'ExistingParserEngine', description: 'Phase 1-3 pipeline' },
    { name: 'docling', class: 'DoclingParserEngine', description: 'Docling' },
    { name: 'ocr', class: 'OCRParserEngine', description: 'OCR-first' },
    { name: 'hybrid', class: 'HybridParserEngine', description: 'Reconciles all' }
  ]
}

const fakeReport = {
  engines: ['existing', 'hybrid'],
  summary: {
    existing: {
      engine: 'existing', runs: 3, avg_runtime_ms: 50.0, ocr_used_pct: 0,
      line_item_count_accuracy: 1.0, total_warnings: 0,
      field_accuracy: {
        vendor_name: { accuracy: 1.0, avg_score: 1.0 },
        invoice_number: { accuracy: 1.0, avg_score: 1.0 },
        invoice_date: { accuracy: 1.0, avg_score: 1.0 },
        due_date: { accuracy: 1.0, avg_score: 1.0 },
        currency: { accuracy: 1.0, avg_score: 1.0 },
        subtotal: { accuracy: 1.0, avg_score: 1.0 },
        tax: { accuracy: 1.0, avg_score: 1.0 },
        total_amount: { accuracy: 1.0, avg_score: 1.0 }
      }
    },
    hybrid: {
      engine: 'hybrid', runs: 3, avg_runtime_ms: 80.0, ocr_used_pct: 0,
      line_item_count_accuracy: 1.0, total_warnings: 1,
      field_accuracy: {
        vendor_name: { accuracy: 1.0, avg_score: 1.0 },
        invoice_number: { accuracy: 1.0, avg_score: 1.0 },
        invoice_date: { accuracy: 1.0, avg_score: 1.0 },
        due_date: { accuracy: 1.0, avg_score: 1.0 },
        currency: { accuracy: 1.0, avg_score: 1.0 },
        subtotal: { accuracy: 1.0, avg_score: 1.0 },
        tax: { accuracy: 1.0, avg_score: 1.0 },
        total_amount: { accuracy: 1.0, avg_score: 1.0 }
      }
    }
  },
  runs: [
    {
      name: 'alpha_office_supplies', file: 'alpha_office_supplies.pdf',
      parser_engine: 'existing', runtime_ms: 60, used_ocr: false,
      text_source: 'pymupdf',
      confidence: { vendor_name: 0.9, total_amount: 0.95 },
      warnings: [], notes: [],
      line_item_count: 3, line_item_count_match: true,
      fields: {
        vendor_name: { expected: 'Alpha Office Supplies', actual: 'Alpha Office Supplies', match: true, score: 1.0, note: 'exact' },
        invoice_number: { expected: 'GOLDEN-2026-0001', actual: 'GOLDEN-2026-0001', match: true, score: 1.0, note: 'exact' },
        invoice_date: { expected: '2026-05-12', actual: '2026-05-12', match: true, score: 1.0, note: 'exact' },
        due_date: { expected: '2026-06-11', actual: '2026-06-11', match: true, score: 1.0, note: 'exact' },
        currency: { expected: 'USD', actual: 'USD', match: true, score: 1.0, note: 'exact' },
        subtotal: { expected: 430.5, actual: 430.5, match: true, score: 1.0, note: 'exact' },
        tax: { expected: 30.14, actual: 30.14, match: true, score: 1.0, note: 'exact' },
        total_amount: { expected: 460.64, actual: 460.64, match: true, score: 1.0, note: 'exact' }
      }
    }
  ]
}

describe('ParserBenchmark page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    api.listParserEngines.mockResolvedValue(fakeEngines)
    api.runParserBenchmark.mockResolvedValue(fakeReport)
  })

  it('loads engine list on mount and shows checkboxes', async () => {
    render(<MemoryRouter><ParserBenchmark /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByLabelText(/existing/)).toBeInTheDocument()
      expect(screen.getByLabelText(/docling/)).toBeInTheDocument()
      expect(screen.getByLabelText(/ocr/)).toBeInTheDocument()
      expect(screen.getByLabelText(/hybrid/)).toBeInTheDocument()
    })
  })

  it('runs the benchmark when the button is clicked', async () => {
    render(<MemoryRouter><ParserBenchmark /></MemoryRouter>)
    await waitFor(() => screen.getByText(/Run benchmark/))
    fireEvent.click(screen.getByText(/Run benchmark/))
    await waitFor(() => {
      expect(api.runParserBenchmark).toHaveBeenCalled()
    })
    // Summary table should appear with at least one engine row.
    await waitFor(() => {
      expect(screen.getByText(/Per-engine summary/)).toBeInTheDocument()
    })
  })

  it('toggles engine selection', async () => {
    render(<MemoryRouter><ParserBenchmark /></MemoryRouter>)
    await waitFor(() => screen.getByLabelText(/docling/))
    const box = screen.getByLabelText(/docling/)
    fireEvent.click(box) // uncheck
    fireEvent.click(screen.getByText(/Run benchmark/))
    await waitFor(() => {
      const lastCall = api.runParserBenchmark.mock.calls.at(-1)
      expect(lastCall[0].engines).not.toContain('docling')
    })
  })
})
