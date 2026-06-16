import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../../api.js'
import AgentChatWindow from './AgentChatWindow.jsx'
import AgentPlanCard from './AgentPlanCard.jsx'
import AgentApprovalCard from './AgentApprovalCard.jsx'
import AgentProgressTimeline from './AgentProgressTimeline.jsx'
import AgentResultCard from './AgentResultCard.jsx'
import AgentModeSwitcher from './AgentModeSwitcher.jsx'
import WorkflowMemoryQuickList from './WorkflowMemoryQuickList.jsx'

const PNL_TASK_TYPES = ['accounting_report_comparison']
const FOLDER_INVOICE_TASK_TYPES = ['local_folder_invoice_workflow']

const STYLES = `
.floating-agent-overlay {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 10000;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.floating-agent-toggle {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  border: none;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99,102,241,0.4);
  transition: transform 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.floating-agent-toggle:hover { transform: scale(1.08); }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.4); } 50% { box-shadow: 0 0 0 16px rgba(220,38,38,0); } }
.floating-agent-window {
  position: fixed;
  bottom: 84px;
  right: 20px;
  width: 440px;
  height: 620px;
  background: #1e1e2e;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #313244;
}
.floating-agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #181825;
  border-bottom: 1px solid #313244;
  cursor: grab;
  user-select: none;
}
.floating-agent-header:active { cursor: grabbing; }
.floating-agent-header h3 { margin: 0; font-size: 15px; color: #cdd6f4; font-weight: 600; }
.floating-agent-header-actions { display: flex; gap: 6px; }
.floating-agent-header-actions button {
  background: none; border: none; color: #6c7086; cursor: pointer; font-size: 16px; padding: 2px 6px;
  border-radius: 4px;
}
.floating-agent-header-actions button:hover { background: #313244; color: #cdd6f4; }
.floating-agent-header .status-dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; display: inline-block; }
.floating-agent-header .status-dot.connected { background: #a6e3a1; }
.floating-agent-header .status-dot.disconnected { background: #f38ba8; }
.floating-agent-mode-bar {
  display: flex; padding: 0; background: #11111b;
}
.floating-agent-body {
  flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 12px;
}
.floating-agent-body::-webkit-scrollbar { width: 4px; }
.floating-agent-body::-webkit-scrollbar-track { background: transparent; }
.floating-agent-body::-webkit-scrollbar-thumb { background: #45475a; border-radius: 4px; }
.floating-agent-input-area {
  padding: 12px; background: #181825; border-top: 1px solid #313244; display: flex; gap: 8px;
}
.floating-agent-input-area input {
  flex: 1; padding: 8px 12px; border: 1px solid #45475a; border-radius: 8px; background: #1e1e2e; color: #cdd6f4; font-size: 14px; outline: none;
}
.floating-agent-input-area input:focus { border-color: #6366f1; }
.floating-agent-input-area button {
  padding: 8px 14px; border: none; border-radius: 8px; background: #6366f1; color: #fff; cursor: pointer; font-size: 14px;
}
.floating-agent-input-area button:hover { background: #7c3aed; }
.floating-agent-input-area button:disabled { opacity: 0.5; cursor: default; }
.floating-agent-mode-indicator {
  padding: 4px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
  font-weight: 600;
}
.floating-agent-mode-indicator.plan { background: #313244; color: #89b4fa; }
.floating-agent-mode-indicator.work { background: #313244; color: #a6e3a1; }
.floating-agent-mode-indicator.record { background: #dc2626; color: #fff; }
.floating-agent-mode-indicator.replay { background: #313244; color: #f9e2af; }
.floating-agent-body textarea { box-sizing: border-box; outline: none; }
.floating-agent-body textarea:focus { border-color: #6366f1; }
`

export default function TrayFloatingAgent() {
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState('plan')
  const [providerStatus, setProviderStatus] = useState(null)
  const [messages, setMessages] = useState([])
  const [currentPlan, setCurrentPlan] = useState(null)
  const [currentRun, setCurrentRun] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(false)
  const [showManualUpload, setShowManualUpload] = useState(false)
  const [folderInvoicePath, setFolderInvoicePath] = useState('')
  const [folderScanResults, setFolderScanResults] = useState([])
  const [showFolderForm, setShowFolderForm] = useState(false)
  const [manualCurrent, setManualCurrent] = useState('')
  const [manualPrevious, setManualPrevious] = useState('')
  const [position, setPosition] = useState({ x: 20, y: 84 })
  const [dragging, setDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const recordingTimerRef = useRef(null)
  const windowRef = useRef(null)
  const headerRef = useRef(null)
  const inputRef = useRef(null)

  const loadInitialData = useCallback(async () => {
    try {
      const [status, modeData, wfList] = await Promise.all([
        api.agentStatus().catch(() => ({ provider: 'unknown', status: 'disconnected' })),
        api.getAgentMode().catch(() => ({ mode: 'plan' })),
        api.listAgentWorkflows().catch(() => ({ workflows: [] })),
      ])
      setProviderStatus(status)
      setMode(modeData.mode || 'plan')
      setWorkflows(wfList.workflows || [])
    } catch { /* silent */ }
  }, [])

  useEffect(() => {
    const h = window.innerHeight
    setPosition({ x: 20, y: h - 620 - 20 })
  }, [])

  useEffect(() => {
    if (isOpen) loadInitialData()
  }, [isOpen, loadInitialData])

  useEffect(() => {
    if (!isOpen) {
      setCurrentPlan(null)
      setCurrentRun(null)
      setShowManualUpload(false)
      setManualCurrent('')
      setManualPrevious('')
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen || !inputRef.current) return
    inputRef.current.focus()
  }, [isOpen])

  const addMessage = (text, role = 'agent') => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), role, text, timestamp: new Date().toISOString() }])
  }

  const handleSendCommand = async (cmd) => {
    const command = cmd || inputRef.current?.value
    if (!command || !command.trim()) return
    setInputValue('')
    addMessage(command, 'user')
    setLoading(true)

    try {
      let planResult
      if (command.toLowerCase().includes('repeat yesterday')) {
        planResult = await api.replayYesterday({ mode: 'dry_run' })
        if (planResult.found && planResult.single_match) {
          addMessage(`Found yesterday's workflow: "${planResult.workflow_name}". Starting dry-run with ${planResult.steps.length} steps.`)
          setCurrentRun({ run_id: planResult.run_id, mode: 'dry_run', status: 'running', steps: planResult.steps })
        } else if (planResult.found && !planResult.single_match) {
          addMessage(`Found ${planResult.workflows.length} workflows from yesterday. Please choose one.`)
        } else {
          addMessage(planResult.message || "No workflow found from yesterday.")
        }
      } else if (command.toLowerCase().includes('emergency stop') || command.toLowerCase().includes('stop everything')) {
        const result = await api.emergencyStopAgent({ reason: 'User command' })
        addMessage(`Emergency stop executed. ${result.stopped_count} run(s) stopped.`)
        setCurrentRun(null)
      } else {
        planResult = await api.planAgentTask({ command })
        setCurrentPlan(planResult)
        const plan = planResult.plan || {}
        const riskLabel = plan.risk_level || 'low'
        const voiceReply = planResult.voice_reply_text || `Plan ready. Risk level: ${riskLabel}.`
        addMessage(voiceReply)
        if (plan.blocked_reason) {
          addMessage(`Blocked: ${plan.blocked_reason}`)
        }
      }
    } catch (err) {
      addMessage(`Error: ${err.message || 'Something went wrong.'}`)
    } finally {
      setLoading(false)
    }
  }

  const setInputValue = (val) => {
    if (inputRef.current) inputRef.current.value = val
  }

  const handleModeChange = async (newMode) => {
    setMode(newMode)
    try {
      await api.setAgentMode(newMode)
      addMessage(`Switched to ${newMode} mode.`)
      if (newMode === 'record') {
        await api.startRecording()
        setRecordingSeconds(0)
        recordingTimerRef.current = setInterval(() => setRecordingSeconds(s => s + 1), 1000)
        addMessage('Recording started. Perform your workflow steps. The recording indicator at the top shows status.')
      } else if (newMode === 'plan') {
        addMessage('Plan mode: I will read and plan but not make any changes.')
      } else if (newMode === 'work') {
        addMessage('Work mode: Ready to execute approved steps.')
      } else if (newMode === 'replay') {
        addMessage('Replay mode: Select a workflow to replay.')
        const wfList = await api.listAgentWorkflows().catch(() => ({ workflows: [] }))
        setWorkflows(wfList.workflows || [])
      }
    } catch (err) {
      addMessage(`Error switching mode: ${err.message}`)
    }
  }

  const formatTrayRecordingTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  const handleApprove = async (planId, mode) => {
    try {
      const result = await api.approveAgentPlan(planId, { mode })
      addMessage(`Plan approved (${result.mode}). ${result.steps.length} steps ready.`)
      setCurrentRun({ run_id: result.run_id, mode: result.mode, status: result.status, steps: result.steps })
    } catch (err) {
      addMessage(`Error approving plan: ${err.message}`)
    }
  }

  const handleReject = (planId) => {
    addMessage('Plan rejected. You can modify and try again.')
    setCurrentPlan(null)
  }

  const handleDryRun = async (runId) => {
    try {
      const result = await api.dryRunRun(runId)
      addMessage(`Dry-run completed: ${result.step_count} steps simulated.`)
      setCurrentRun(prev => ({ ...prev, status: 'completed', mode: 'dry_run' }))
      const summary = await api.getAgentRunSummary(runId).catch(() => null)
      if (summary) setCurrentRun(prev => ({ ...prev, summary }))
    } catch (err) {
      addMessage(`Error in dry-run: ${err.message}`)
    }
  }

  const handleStartLive = async (runId) => {
    try {
      const result = await api.startLiveRun(runId)
      addMessage('Live execution started.')
      setCurrentRun(prev => ({ ...prev, mode: 'live', status: 'running' }))
    } catch (err) {
      addMessage(`Error starting live: ${err.message}`)
    }
  }

  const handleEmergencyStop = async () => {
    try {
      const result = await api.emergencyStopAgent({ reason: 'User emergency stop' })
      addMessage(`Emergency stop executed. ${result.stopped_count} run(s) stopped.`)
      setCurrentRun(null)
    } catch (err) {
      addMessage(`Error: ${err.message}`)
    }
  }

  const handleSaveWorkflow = async (planId, name) => {
    try {
      const result = await api.saveAgentWorkflow({ plan_id: planId, workflow_name: name })
      addMessage(`Workflow saved as "${result.workflow_name}". Trigger phrases: ${(result.trigger_phrases || []).join(', ') || 'none'}.`)
      const wfList = await api.listAgentWorkflows().catch(() => ({ workflows: [] }))
      setWorkflows(wfList.workflows || [])
    } catch (err) {
      addMessage(`Error saving workflow: ${err.message}`)
    }
  }

  const handleRepeatWorkflow = async (workflowId) => {
    try {
      const result = await api.repeatAgentWorkflow(workflowId, { mode: 'dry_run' })
      addMessage(`Repeating "${result.workflow_name}" in dry-run mode.`)
      setCurrentRun({ run_id: result.run_id, mode: 'dry_run', status: 'running', steps: result.steps })
    } catch (err) {
      addMessage(`Error repeating workflow: ${err.message}`)
    }
  }

  const handlePnlDemo = async () => {
    setLoading(true)
    try {
      const result = await api.pnlCompareDemo()
      addMessage('Demo P&L comparison completed.')
      setCurrentRun(prev => ({ ...prev, summary: {
        status: 'completed',
        summary_english: result.result.summary_english,
        summary_roman_urdu: result.result.summary_roman_urdu,
        excel_file_path: result.result.excel_file_path,
        pnl_comparison: {
          current_net_income: result.result.current?.net_income,
          previous_net_income: result.result.previous?.net_income,
          net_income_difference: result.result.comparison?.net_income_difference,
          net_income_percentage_change: result.result.comparison?.net_income_percentage_change,
        },
      }}))
    } catch (err) {
      addMessage(`Demo error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleManualUpload = async () => {
    setLoading(true)
    try {
      let currentData = manualCurrent
      let previousData = manualPrevious
      try { currentData = JSON.parse(manualCurrent) } catch {}
      try { previousData = JSON.parse(manualPrevious) } catch {}
      const result = await api.pnlCompareUploaded({
        current_month_file: currentData,
        previous_month_file: previousData,
      })
      addMessage('P&L comparison completed from uploaded data.')
      setCurrentRun(prev => ({ ...prev, summary: {
        status: 'completed',
        summary_english: result.result.summary_english,
        summary_roman_urdu: result.result.summary_roman_urdu,
        excel_file_path: result.result.excel_file_path,
        pnl_comparison: {
          current_net_income: result.result.current?.net_income,
          previous_net_income: result.result.previous?.net_income,
          net_income_difference: result.result.comparison?.net_income_difference,
          net_income_percentage_change: result.result.comparison?.net_income_percentage_change,
        },
      }}))
      setShowManualUpload(false)
    } catch (err) {
      addMessage(`Upload error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleFolderScan = async () => {
    setLoading(true)
    try {
      const result = await api.folderInvoiceScan({ folder_path: folderInvoicePath, date_filter: 'today' })
      setFolderScanResults(result.files || [])
      addMessage(`Scanned folder: found ${result.count} invoice files.`)
    } catch (err) {
      addMessage(`Scan error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleFolderCreateExcel = async () => {
    setLoading(true)
    try {
      const result = await api.folderInvoiceCreateExcel({ invoices: folderScanResults })
      setCurrentRun(prev => ({ ...prev, summary: {
        status: 'completed',
        summary_english: result.summary_english,
        summary_roman_urdu: result.summary_roman_urdu,
        excel_file_path: result.filepath,
        invoice_count: result.invoice_count,
        total_amount: result.total_amount,
      }}))
      setShowFolderForm(false)
      addMessage(`Daily invoices Excel created: ${result.filepath}`)
    } catch (err) {
      addMessage(`Excel error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenFile = (filePath) => {
    addMessage(`Opening file: ${filePath}`)
  }

  const handleMouseDown = (e) => {
    if (e.target.closest('.floating-agent-header-actions')) return
    setDragging(true)
    setDragOffset({ x: e.clientX - position.x, y: e.clientY - position.y })
  }

  useEffect(() => {
    if (!dragging) return
    const handleMouseMove = (e) => {
      setPosition({ x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y })
    }
    const handleMouseUp = () => setDragging(false)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [dragging, dragOffset])

  return (
    <>
      <style>{STYLES}</style>
      <div className="floating-agent-overlay">
        <button
          className="floating-agent-toggle"
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? 'Close Accountant Agent' : 'Open Accountant Agent (Alt+A)'}
        >
          {isOpen ? '✕' : '🤖'}
        </button>

        {isOpen && (
          <div className="floating-agent-window" ref={windowRef} style={{ bottom: `${position.y}px`, right: `${position.x}px`, position: 'fixed' }}>
            <div className="floating-agent-header" ref={headerRef} onMouseDown={handleMouseDown}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={`status-dot ${providerStatus?.status === 'mock' || providerStatus?.status === 'connected' ? 'connected' : 'disconnected'}`} />
                <h3>Accountant Agent</h3>
                {mode === 'record' && (
                  <span style={{
                    display: 'flex', alignItems: 'center', gap: '4px',
                    padding: '2px 8px', borderRadius: '10px',
                    background: '#dc2626', color: '#fff', fontSize: '11px', fontWeight: 600,
                  }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff', display: 'inline-block', animation: 'pulse 1s infinite' }} />
                    REC {formatTrayRecordingTime(recordingSeconds)}
                  </span>
                )}
              </div>
              <div className="floating-agent-header-actions">
                {mode === 'record' && (
                  <button onClick={async () => {
                    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
                    try {
                      const result = await api.stopRecording({ workflow_name: 'Recorded Workflow' })
                      addMessage(`Recording stopped. ${result.workflow_draft ? 'Workflow draft saved.' : 'No draft created.'}`)
                      setRecordingSeconds(0)
                      setMode('plan')
                      await api.setAgentMode('plan')
                    } catch (err) {
                      addMessage(`Error stopping: ${err.message}`)
                    }
                  }} title="Stop Recording" style={{ color: '#fca5a5', fontSize: '13px' }}>⏹ Stop</button>
                )}
                <button onClick={handleEmergencyStop} title="Emergency Stop">⛔</button>
                <button onClick={() => setIsOpen(false)} title="Close">—</button>
              </div>
            </div>

            <div className={`floating-agent-mode-indicator ${mode}`}>
              Mode: {mode.toUpperCase()}
            </div>

            <AgentModeSwitcher currentMode={mode} onModeChange={handleModeChange} />

            <div className="floating-agent-body">
              <AgentChatWindow messages={messages} />

              {currentPlan && currentPlan.plan_id && (
                <AgentPlanCard plan={currentPlan} />
              )}

              {currentPlan && currentPlan.plan_id && !currentPlan.plan?.blocked_reason && !currentPlan.plan?.clarification_needed && (
                <>
                  <AgentApprovalCard
                    planId={currentPlan.plan_id}
                    onApprove={handleApprove}
                    onReject={() => handleReject(currentPlan.plan_id)}
                    loading={loading}
                  />
                  {PNL_TASK_TYPES.includes(currentPlan.task_type) && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <button className="btn btn--sm btn--outline" onClick={() => setShowManualUpload(true)} style={{ flex: 1 }}>
                        Upload reports manually
                      </button>
                      <button className="btn btn--sm btn--outline" onClick={handlePnlDemo} style={{ flex: 1 }}>
                        Run demo comparison
                      </button>
                    </div>
                  )}
                  {FOLDER_INVOICE_TASK_TYPES.includes(currentPlan.task_type) && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <button className="btn btn--sm btn--outline" onClick={() => setShowFolderForm(true)} style={{ flex: 1 }}>
                        Scan Folder
                      </button>
                    </div>
                  )}
                </>
              )}

              {currentRun && currentRun.run_id && (
                <AgentProgressTimeline
                  run={currentRun}
                  onDryRun={handleDryRun}
                  onStartLive={handleStartLive}
                  onEmergencyStop={handleEmergencyStop}
                  loading={loading}
                />
              )}

              {currentRun?.summary && (
                <AgentResultCard summary={currentRun.summary} onOpenFile={handleOpenFile} />
              )}

              {showManualUpload && PNL_TASK_TYPES.includes(currentPlan?.task_type) && (
                <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
                  <p style={{ color: '#f9e2af', fontSize: '13px', margin: '0 0 8px' }}>
                    Could not export automatically. Paste JSON data below:
                  </p>
                  <textarea
                    placeholder='Current month JSON: { "rows": [...], "total_income": ..., "total_expenses": ..., "net_income": ... }'
                    value={manualCurrent}
                    onChange={(e) => setManualCurrent(e.target.value)}
                    rows={3}
                    style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #45475a', background: '#1e1e2e', color: '#cdd6f4', fontSize: '12px', marginBottom: '6px', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                  <textarea
                    placeholder='Previous month JSON: { "rows": [...], "total_income": ..., "total_expenses": ..., "net_income": ... }'
                    value={manualPrevious}
                    onChange={(e) => setManualPrevious(e.target.value)}
                    rows={3}
                    style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #45475a', background: '#1e1e2e', color: '#cdd6f4', fontSize: '12px', marginBottom: '6px', resize: 'vertical', fontFamily: 'monospace' }}
                  />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn--sm btn--primary" onClick={handleManualUpload} disabled={loading || !manualCurrent || !manualPrevious}>
                      Compare
                    </button>
                    <button className="btn btn--sm btn--outline" onClick={() => setShowManualUpload(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {showFolderForm && FOLDER_INVOICE_TASK_TYPES.includes(currentPlan?.task_type) && (
                <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
                  <p style={{ color: '#f9e2af', fontSize: '13px', margin: '0 0 8px' }}>
                    Enter folder path to scan for invoices:
                  </p>
                  <input
                    placeholder='e.g. C:\Users\...\Desktop\Invoices'
                    value={folderInvoicePath}
                    onChange={(e) => setFolderInvoicePath(e.target.value)}
                    style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid #45475a', background: '#1e1e2e', color: '#cdd6f4', fontSize: '12px', marginBottom: '6px' }}
                  />
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn--sm btn--primary" onClick={handleFolderScan} disabled={loading || !folderInvoicePath}>
                      Scan
                    </button>
                    <button className="btn btn--sm btn--outline" onClick={() => setShowFolderForm(false)}>
                      Cancel
                    </button>
                  </div>
                  {folderScanResults.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <p style={{ color: '#a6e3a1', fontSize: '12px', margin: '0 0 4px' }}>Found {folderScanResults.length} file(s):</p>
                      <ul style={{ fontSize: '11px', color: '#bac2de', margin: '0', paddingLeft: '16px' }}>
                        {folderScanResults.slice(0, 5).map((f, i) => (
                          <li key={i}>{f.filename}</li>
                        ))}
                        {folderScanResults.length > 5 && <li>...and {folderScanResults.length - 5} more</li>}
                      </ul>
                      <button className="btn btn--sm btn--primary" onClick={handleFolderCreateExcel} disabled={loading} style={{ marginTop: '8px' }}>
                        Create Daily Invoices Excel
                      </button>
                    </div>
                  )}
                </div>
              )}

              {currentPlan && currentPlan.plan_id && currentRun?.status === 'completed' && currentPlan.plan?.can_save_workflow && (
                <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
                  <p style={{ color: '#a6e3a1', fontSize: '13px', margin: '0 0 8px' }}>Save this as a repeatable workflow?</p>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input id="floating-wf-name" placeholder="Workflow name" style={{ flex: 1, padding: '6px 10px', borderRadius: '6px', border: '1px solid #45475a', background: '#1e1e2e', color: '#cdd6f4', fontSize: '13px' }} />
                    <button className="btn btn--sm btn--primary" onClick={() => {
                      const name = document.getElementById('floating-wf-name')?.value || 'Saved Workflow'
                      handleSaveWorkflow(currentPlan.plan_id, name)
                    }}>Save</button>
                  </div>
                </div>
              )}

              {mode === 'replay' && workflows.length > 0 && !currentRun && (
                <WorkflowMemoryQuickList workflows={workflows} onRepeat={handleRepeatWorkflow} />
              )}
            </div>

            <div className="floating-agent-input-area">
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask your Accountant Agent..."
                onKeyDown={(e) => { if (e.key === 'Enter') handleSendCommand(e.target.value) }}
                disabled={loading}
              />
              <button onClick={() => handleSendCommand()} disabled={loading}>
                {loading ? '...' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
