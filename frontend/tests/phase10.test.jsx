// Phase 10 — frontend tests for the version history, file
// snapshots, and restore-modal flows.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import VersionHistory from '../src/pages/VersionHistory.jsx'
import FileSnapshots from '../src/pages/FileSnapshots.jsx'
import RestoreActivity from '../src/pages/RestoreActivity.jsx'
import RestoreConfirmModal from '../src/components/RestoreConfirmModal.jsx'
import BeforeAfterDiff from '../src/components/BeforeAfterDiff.jsx'

const listVersionsMock = vi.fn()
const restoreVersionMock = vi.fn()
const listFileSnapshotsMock = vi.fn()
const listRestoreLogsMock = vi.fn()

vi.mock('../src/api.js', () => ({
  api: {
    base: 'http://localhost:8000',
    listVersions: (...args) => listVersionsMock(...args),
    restoreVersion: (...args) => restoreVersionMock(...args),
    listFileSnapshots: (...args) => listFileSnapshotsMock(...args),
    listRestoreLogs: (...args) => listRestoreLogsMock(...args),
  },
  formatDateTime: (v) => v || '',
}))

beforeEach(() => {
  listVersionsMock.mockReset()
  restoreVersionMock.mockReset()
  listFileSnapshotsMock.mockReset()
  listRestoreLogsMock.mockReset()
})

describe('VersionHistory page', () => {
  it('renders the version list for an invoice', async () => {
    listVersionsMock.mockResolvedValueOnce([
      {
        id: 2,
        version_number: 2,
        source_action: 'user.edit',
        created_by: 'user',
        created_at: '2026-06-06T10:00:00',
        change_summary: 'Edited vendor name',
        restored_from_version: null,
        snapshot: { vendor_name: 'ACME' },
      },
      {
        id: 1,
        version_number: 1,
        source_action: 'parser.extract',
        created_by: 'user',
        created_at: '2026-06-06T09:00:00',
        change_summary: 'Initial extraction',
        restored_from_version: null,
        snapshot: { vendor_name: 'Acme Inc.' },
      },
    ])
    render(
      <MemoryRouter initialEntries={['/versions/invoice/42']}>
        <Routes>
          <Route path="/versions/:entityType/:entityId" element={<VersionHistory />} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText(/Edited vendor name/)).toBeInTheDocument()
    })
    expect(screen.getByText(/Initial extraction/)).toBeInTheDocument()
    expect(screen.getByText('v2')).toBeInTheDocument()
    expect(screen.getByText('v1')).toBeInTheDocument()
  })

  it('opens the restore modal and submits a reason', async () => {
    listVersionsMock.mockResolvedValueOnce([
      {
        id: 1,
        version_number: 1,
        source_action: 'parser.extract',
        created_by: 'user',
        created_at: '2026-06-06T09:00:00',
        change_summary: 'Initial extraction',
        restored_from_version: null,
        snapshot: {},
      },
    ])
    restoreVersionMock.mockResolvedValueOnce({
      id: 2,
      version_number: 2,
      source_action: 'restore',
      created_by: 'user',
      created_at: '2026-06-06T11:00:00',
      change_summary: 'Restored from v1',
      restored_from_version: 1,
      snapshot: {},
    })
    render(
      <MemoryRouter initialEntries={['/versions/invoice/42']}>
        <Routes>
          <Route path="/versions/:entityType/:entityId" element={<VersionHistory />} />
        </Routes>
      </MemoryRouter>
    )
    await waitFor(() => screen.getByText('Restore this version'))
    const rowBtn = screen.getAllByText('Restore this version')[0]
    fireEvent.click(rowBtn)
    await waitFor(() => screen.getByText('Restore previous version'))
    fireEvent.change(
      screen.getByPlaceholderText(/wrong totals entered/),
      { target: { value: 'rollback per user request' } }
    )
    const modalBtns = screen.getAllByRole('button', { name: /Restore this version/ })
    // The modal's primary button is the second one (the row's
    // "Restore this version" link is a <button> too).
    fireEvent.click(modalBtns[modalBtns.length - 1])
    await waitFor(() => {
      expect(restoreVersionMock).toHaveBeenCalledWith(
        'invoice', '42', 1,
        { actor: 'user', reason: 'rollback per user request' }
      )
    })
  })
})

describe('FileSnapshots page', () => {
  it('shows a snapshot row with the right badge', async () => {
    listFileSnapshotsMock.mockResolvedValueOnce([
      {
        id: 7,
        file_type: 'excel_export',
        original_path: 'C:/data/exports/foo.xlsx',
        snapshot_path: 'C:/data/snapshots/x.xlsx',
        action_type: 'excel_export.pre_export',
        file_hash_before: 'abcdef1234567890',
        size_bytes: 4096,
        restore_status: 'restored',
        restore_count: 1,
        created_by: 'user',
        created_at: '2026-06-06T08:00:00',
        notes: '',
      },
    ])
    render(
      <MemoryRouter>
        <FileSnapshots />
      </MemoryRouter>
    )
    await waitFor(() => {
      // The full path is in a title attribute; the filename is the
      // tail of the path string.
      expect(
        screen.getByText('C:/data/exports/foo.xlsx')
      ).toBeInTheDocument()
    })
    expect(screen.getByText(/excel_export.pre_export/)).toBeInTheDocument()
    expect(screen.getByText(/restored \(1\)/)).toBeInTheDocument()
  })
})

describe('RestoreActivity page', () => {
  it('renders restore log rows', async () => {
    listRestoreLogsMock.mockResolvedValueOnce([
      {
        id: 5,
        entity_type: 'entity_version',
        entity_id: 3,
        target_id: '42',
        restored_from_version: 1,
        restored_to_version: 4,
        reason: 'wrong totals',
        restored_by: 'tester',
        restored_at: '2026-06-06T10:30:00',
      },
    ])
    render(
      <MemoryRouter>
        <RestoreActivity />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('v1 → v4')).toBeInTheDocument()
    })
    expect(screen.getByText('entity_version #3')).toBeInTheDocument()
    expect(screen.getByText('wrong totals')).toBeInTheDocument()
  })
})

describe('RestoreConfirmModal', () => {
  it('disables the submit button until a reason is typed', () => {
    render(
      <MemoryRouter>
        <RestoreConfirmModal
          entityType="invoice"
          entityId="42"
          version={{
            version_number: 1,
            created_at: '2026-06-06T09:00:00',
            created_by: 'user',
          }}
          onClose={() => {}}
          onConfirm={() => {}}
        />
      </MemoryRouter>
    )
    const btn = screen.getByRole('button', { name: /Restore this version/ })
    expect(btn).toBeDisabled()
    fireEvent.change(screen.getByPlaceholderText(/wrong totals/), {
      target: { value: 'test reason' },
    })
    expect(btn).toBeEnabled()
  })
})

describe('BeforeAfterDiff', () => {
  it('renders field-level changes', () => {
    render(
      <MemoryRouter>
        <BeforeAfterDiff
          fromVersion={1}
          toVersion={2}
          diffs={[
            { field: 'vendor_name', before: 'Acme', after: 'ACME Corp' },
            { field: 'total_amount', before: 100, after: 120 },
          ]}
        />
      </MemoryRouter>
    )
    expect(screen.getByText('vendor_name')).toBeInTheDocument()
    expect(screen.getByText('Acme')).toBeInTheDocument()
    expect(screen.getByText('ACME Corp')).toBeInTheDocument()
  })

  it('shows a "no changes" message when diffs is empty', () => {
    render(
      <MemoryRouter>
        <BeforeAfterDiff fromVersion={1} toVersion={2} diffs={[]} />
      </MemoryRouter>
    )
    expect(screen.getByText(/No field changes/)).toBeInTheDocument()
  })
})
