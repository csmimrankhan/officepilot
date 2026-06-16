export function normalizeBrowserStepResult(stepResult, toolName) {
  if (!stepResult) return { type: 'unknown', cardType: null }
  const output = stepResult.output || {}
  const isBlocked = stepResult.status === 'blocked' || output.blocked === true

  const isBrowserTool = toolName && (
    toolName.startsWith('browser_') ||
    toolName === 'open_url' ||
    toolName === 'export_accounting_report'
  )

  if (isBlocked) {
    return {
      type: 'blocked',
      cardType: 'blocked_warning',
      blocked: true,
      reason: output.reason || stepResult.message || 'Blocked by safety policy',
      tool: toolName,
      output,
    }
  }

  const needsUserConfirmation = output.needs_user_confirmation === true
  const action = output.action || ''
  const isWaitForLogin = action === 'wait_for_login' || needsUserConfirmation
  const isGuidedExport = action === 'guided_export' || output.guided_mode === true
  const hasDownloadPath = !!(output.filepath || output.downloaded_file_path || output.output_path)

  if (isWaitForLogin) {
    return {
      type: 'wait_for_login',
      cardType: 'manual_login',
      website: output.current_url || output.url || '',
      status: output.status || 'waiting',
      prompt: output.prompt || '',
      currentUrl: output.current_url || '',
      pageTitle: output.page_title || '',
      screenshotPath: output.screenshot_path || '',
      output,
    }
  }

  if (isGuidedExport) {
    return {
      type: 'guided_export',
      cardType: 'guided_download',
      status: output.status || 'waiting_for_user',
      watchedFolder: output.watched_folder || '',
      waiting: output.status === 'waiting_for_user' || output.status === 'waiting',
      detectedFile: output.filepath || output.downloaded_file_path || '',
      outputPath: output.output_path || output.filepath || '',
      output,
    }
  }

  if (hasDownloadPath) {
    const filePath = output.filepath || output.downloaded_file_path || output.output_path || ''
    const filename = output.filename || (filePath ? filePath.split(/[/\\]/).pop() : '')
    return {
      type: 'downloaded',
      cardType: 'browser_result',
      filePath,
      filename,
      output,
    }
  }

  if (isBrowserTool) {
    return {
      type: 'browser_status',
      cardType: 'browser_automation',
      url: output.url || output.current_url || '',
      status: output.status || (stepResult.status === 'completed' ? 'completed' : 'active'),
      screenshotUrl: output.screenshot_url || output.screenshotUrl || output.screenshot_path || '',
      nextAction: output.next_action || output.action || '',
      riskLevel: output.risk_level || output.risk || '',
      output,
    }
  }

  return { type: 'unknown', cardType: null, output }
}
