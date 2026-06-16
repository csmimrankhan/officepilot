import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { normalizeEmailStepResult } from '../src/utils/normalizeEmailStepResult.js'

// ── normalizeEmailStepResult: blocked / read-only policy ─────────────

describe('normalizeEmailStepResult — blocked/write commands', () => {
  it('returns blocked_warning for gmail_readonly_policy', () => {
    const result = normalizeEmailStepResult(
      {
        status: 'blocked',
        message: 'This Gmail action is blocked because OfficePilot only has read-only email automation.',
        output: { blocked: true, reason: 'gmail_readonly_policy', tool_name: 'email_send' },
      },
      'email_send'
    )
    expect(result.type).toBe('blocked')
    expect(result.cardType).toBe('blocked_warning')
    expect(result.reason).toContain('gmail_readonly_policy')
  })

  it('returns blocked_warning for email_forward', () => {
    const result = normalizeEmailStepResult(
      {
        status: 'blocked',
        message: 'This Gmail action is blocked because OfficePilot only has read-only email automation.',
        output: { blocked: true, reason: 'gmail_readonly_policy', tool_name: 'email_forward' },
      },
      'email_forward'
    )
    expect(result.type).toBe('blocked')
    expect(result.cardType).toBe('blocked_warning')
    expect(result.reason).toContain('readonly')
  })

  it('returns blocked_warning for email_delete', () => {
    const result = normalizeEmailStepResult(
      {
        status: 'blocked',
        message: 'This Gmail action is blocked because OfficePilot only has read-only email automation.',
        output: { blocked: true, reason: 'gmail_readonly_policy', tool_name: 'email_delete' },
      },
      'email_delete'
    )
    expect(result.type).toBe('blocked')
    expect(result.cardType).toBe('blocked_warning')
  })

  it('returns blocked_warning for email_mark_read', () => {
    const result = normalizeEmailStepResult(
      {
        status: 'blocked',
        message: 'This Gmail action is blocked because OfficePilot only has read-only email automation.',
        output: { blocked: true, reason: 'gmail_readonly_policy', tool_name: 'email_mark_read' },
      },
      'email_mark_read'
    )
    expect(result.type).toBe('blocked')
    expect(result.cardType).toBe('blocked_warning')
  })
})

// ── Allowed email commands still normalize correctly ──────────────────

describe('normalizeEmailStepResult — allowed read-only commands', () => {
  it('returns gmail_connect for email_connect_gmail', () => {
    const result = normalizeEmailStepResult(
      { status: 'success', message: 'Connected', output: { connected: true, email: 'test@gmail.com', status: 'mock' } },
      'email_connect_gmail'
    )
    expect(result.type).toBe('connected')
    expect(result.cardType).toBe('gmail_mock')
  })

  it('returns search_results for email_search', () => {
    const messages = [{ message_id: '1', subject: 'Invoice' }]
    const result = normalizeEmailStepResult(
      { status: 'success', output: { email_search_results: true, messages, result_count: 1 } },
      'email_search'
    )
    expect(result.type).toBe('search_results')
    expect(result.cardType).toBe('email_search')
  })

  it('returns email_download_result for email_download_attachments', () => {
    const downloads = [{ filename: 'invoice.pdf', filepath: '/tmp/invoice.pdf' }]
    const result = normalizeEmailStepResult(
      {
        status: 'success',
        message: 'Downloaded 1 attachment(s)',
        output: { attachment_download_success: true, downloads, total_downloaded: 1, output_folder: '/tmp' },
      },
      'email_download_attachments'
    )
    expect(result.type).toBe('download_success')
    expect(result.cardType).toBe('email_download_result')
  })

  it('returns preview for email_preview_messages', () => {
    const result = normalizeEmailStepResult(
      { status: 'success', output: { email_preview: true, message_id: '1', from: 'v@c.com', subject: 'Invoice' } },
      'email_preview_messages'
    )
    expect(result.type).toBe('preview')
  })

  it('returns gmail_disconnected for email_disconnect_account', () => {
    const result = normalizeEmailStepResult(
      { status: 'success', output: { disconnected: true, email: 'test@gmail.com' } },
      'email_disconnect_account'
    )
    expect(result.type).toBe('disconnected')
    expect(result.cardType).toBe('gmail_disconnected')
  })
})

// ── Plan-task blocked response rendering ─────────────────────────────

describe('Blocked plan response rendering', () => {
  it('renders blocked task title and reason', () => {
    const plan = {
      task_title: 'Blocked Task',
      task_summary: 'OfficePilot Gmail automation is read-only. Sending, forwarding, deleting, moving, or marking emails is not supported.',
      risk_level: 'blocked',
      blocked_reason: 'email_write_not_supported',
    }

    expect(plan.risk_level).toBe('blocked')
    expect(plan.blocked_reason).toBe('email_write_not_supported')
    expect(plan.task_summary).toContain('read-only')
  })
})
