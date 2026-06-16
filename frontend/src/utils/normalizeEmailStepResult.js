export function normalizeEmailStepResult(stepResult, toolName) {
  if (!stepResult) return { type: 'unknown', cardType: null }
  const output = stepResult.output || {}
  const isBlocked = stepResult.status === 'blocked' || output.blocked === true

  const isEmailTool = toolName && (
    toolName.startsWith('email_') ||
    toolName === 'email_connect_gmail' ||
    toolName === 'email_search' ||
    toolName === 'email_preview_messages' ||
    toolName === 'email_download_attachments' ||
    toolName === 'email_save_attachment' ||
    toolName === 'email_disconnect_account'
  )

  if (isBlocked && isEmailTool) {
    return {
      type: 'blocked',
      cardType: 'blocked_warning',
      blocked: true,
      reason: output.reason || stepResult.message || 'Blocked by safety policy',
      tool: toolName,
      output,
    }
  }

  if (output.needs_connection) {
    return {
      type: 'needs_connection',
      cardType: 'gmail_connect',
      provider: output.provider || 'gmail',
      authorizationUrl: output.authorization_url || '',
      status: output.status || 'needs_connection',
      output,
    }
  }

  if (output.connected === true) {
    return {
      type: 'connected',
      cardType: output.status === 'mock' ? 'gmail_mock' : 'gmail_connected',
      email: output.email || '',
      accountId: output.account_id || '',
      status: output.status || 'connected',
      mode: output.mode || (output.status === 'mock' ? 'mock' : 'live'),
      output,
    }
  }

  if (output.email_search_results) {
    return {
      type: 'search_results',
      cardType: 'email_search',
      messages: output.messages || [],
      resultCount: output.result_count || 0,
      query: output.query || '',
      requiresApproval: output.requires_approval || false,
      mode: output.mode || 'live',
      output,
    }
  }

  if (output.email_preview) {
    return {
      type: 'preview',
      cardType: 'email_preview',
      messageId: output.message_id || '',
      from: output.from || '',
      subject: output.subject || '',
      date: output.date || '',
      snippet: output.snippet || '',
      attachments: output.attachments || [],
      hasAttachments: output.has_attachments || false,
      mode: output.mode || 'live',
      output,
    }
  }

  if (output.attachment_download_success) {
    return {
      type: 'download_success',
      cardType: 'email_download_result',
      downloads: output.downloads || [],
      totalDownloaded: output.total_downloaded || 0,
      outputFolder: output.output_folder || '',
      hasSpreadsheet: output.has_spreadsheet || false,
      output,
    }
  }

  if (output.saved_path) {
    return {
      type: 'file_saved',
      cardType: 'email_file_saved',
      savedPath: output.saved_path || '',
      filename: output.filename || '',
      output,
    }
  }

  if (output.disconnected === true) {
    return {
      type: 'disconnected',
      cardType: 'gmail_disconnected',
      email: output.email || '',
      status: 'disconnected',
      output,
    }
  }

  if (output.needs_input) {
    const field = output.field || ''
    if (field === 'output_folder' || output.field_type === 'folder_picker') {
      return {
        type: 'needs_folder',
        cardType: 'needs_folder_input',
        field: 'output_folder',
        message: output.message || 'Output folder path is required',
        output,
      }
    }
    if (field === 'message_id') {
      return {
        type: 'needs_message_id',
        cardType: 'needs_input',
        field: 'message_id',
        message: output.message || 'Message ID is required for preview',
        output,
      }
    }
    if (field === 'query') {
      return {
        type: 'needs_query',
        cardType: 'needs_input',
        field: 'query',
        message: output.message || 'Search query is required',
        output,
      }
    }
    if (field === 'filepath') {
      return {
        type: 'needs_filepath',
        cardType: 'needs_input',
        field: 'filepath',
        message: output.message || 'File path is required',
        output,
      }
    }
    return {
      type: 'needs_input',
      cardType: 'needs_input',
      field: field,
      message: output.message || 'Input required',
      output,
    }
  }

  if (output.draft_created) {
    return {
      type: 'draft_created',
      cardType: 'email_draft',
      to: output.to || '',
      subject: output.subject || '',
      output,
    }
  }

  if (isEmailTool) {
    return {
      type: 'email_status',
      cardType: 'email_status',
      status: stepResult.status || 'completed',
      message: stepResult.message || '',
      output,
    }
  }

  return { type: 'unknown', cardType: null, output }
}
