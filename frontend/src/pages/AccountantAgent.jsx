import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import LoadingState from '../components/ui/LoadingState.jsx'
import SkillMatchCard from '../components/agent/SkillMatchCard.jsx'
import FilePickerCard from '../components/agent/FilePickerCard.jsx'
import FileSelectionCard from '../components/agent/FileSelectionCard.jsx'
import BrowserAutomationCard from '../components/agent/BrowserAutomationCard.jsx'
import ManualLoginCard from '../components/agent/ManualLoginCard.jsx'
import GuidedDownloadCard from '../components/agent/GuidedDownloadCard.jsx'
import BrowserResultCard from '../components/agent/BrowserResultCard.jsx'
import { normalizeBrowserStepResult } from '../utils/normalizeBrowserStepResult.js'
import { normalizeEmailStepResult } from '../utils/normalizeEmailStepResult.js'
import { useRecording } from '../hooks/useRecording.js'
import WorkflowRecordingOverlay from '../components/agent/WorkflowRecordingOverlay.jsx'
import RecordedWorkflowPreview from '../components/agent/RecordedWorkflowPreview.jsx'
import SkillDraftReview from '../components/agent/SkillDraftReview.jsx'
import GmailConnectCard from '../components/agent/GmailConnectCard.jsx'
import EmailSearchPreviewCard from '../components/agent/EmailSearchPreviewCard.jsx'
import AttachmentDownloadCard from '../components/agent/AttachmentDownloadCard.jsx'
import EmailDownloadResultCard from '../components/agent/EmailDownloadResultCard.jsx'

const SUGGESTED_COMMANDS = [
  'Read this screen',
  'Record this workflow',
  "Repeat yesterday's workflow",
  'Create an Excel summary',
  'Show workflow memory',
]

const AUTOMATION_CARDS = [
  {
    label: 'Create Excel Summary',
    desc: 'Turn an Excel or CSV file into a clean summary report.',
    command: 'Create an Excel summary',
  },
  {
    label: 'Download Invoice Attachments',
    desc: 'Find invoice emails and download attachments safely.',
    command: 'Download invoice attachments',
  },
  {
    label: 'Export Monthly Report',
    desc: 'Guide a browser export from your accounting portal.',
    command: 'Export monthly profit and loss',
  },
  {
    label: 'Record Workflow',
    desc: 'Record a repeated task and save it as a reusable skill.',
    command: 'Record this workflow',
  },
  {
    label: 'Repeat Last Workflow',
    desc: 'Run a saved workflow again with approval.',
    command: "Repeat yesterday's workflow",
  },
  {
    label: 'Read Current Screen',
    desc: 'Understand the active screen before taking action.',
    command: 'Read this screen',
  },
]

const HERO_DEMO_COMMAND = 'email sa aj ki invoice download karo aur Excel ma save karo aur total batao'

const MORE_ACTIONS = [
  { label: 'Workflow Memory', navigate: '/app/workflow-memory' },
  { label: 'Voice Commands', navigate: '/voice' },
  { label: 'Start Guided Demo', command: HERO_DEMO_COMMAND },
  { label: 'Settings', navigate: '/app/settings' },
]

const DEMO_WORKFLOW_NAME = 'Daily Invoice Process'
const DEMO_TRIGGER_PHRASES = [
  'daily invoice process',
  'aaj ki invoice process',
  'invoice process workflow',
  'today invoice workflow',
  'kal wala workflow repeat karo',
  'invoice download karo',
  'daily invoice autopilot',
]

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function AccountantAgent() {
  const location = useLocation()
  const navigate = useNavigate()
  const initialState = location.state?.command || ''
  const [command, setCommand] = useState(initialState)
  const commandInputRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [planning, setPlanning] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [error, setError] = useState(null)
  const [agentStatus, setAgentStatus] = useState(null)
  const [context, setContext] = useState(null)
  const [plan, setPlan] = useState(null)
  const [planId, setPlanId] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [showSaveForm, setShowSaveForm] = useState(false)
  const [workflowName, setWorkflowName] = useState(DEMO_WORKFLOW_NAME)
  const [workflowDesc, setWorkflowDesc] = useState('Automated daily invoice process: download, extract, calculate total, and save to Excel.')
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)
  const [repeatResult, setRepeatResult] = useState(null)
  const [repeatMode, setRepeatMode] = useState('dry_run')
  const [repeatLoading, setRepeatLoading] = useState(false)

  const [detectedLanguage, setDetectedLanguage] = useState(null)
  const [voiceReply, setVoiceReply] = useState(null)
  const [suggestedActions, setSuggestedActions] = useState([])
  const [matchedWorkflow, setMatchedWorkflow] = useState(null)
  const [skillMatch, setSkillMatch] = useState(null)

  const [runId, setRunId] = useState(null)
  const [runMode, setRunMode] = useState(null)
  const [runStatus, setRunStatus] = useState(null)
  const [runSteps, setRunSteps] = useState([])
  const [currentStepIndex, setCurrentStepIndex] = useState(-1)
  const [runResults, setRunResults] = useState([])
  const [stepExecuting, setStepExecuting] = useState(false)
  const [dryRunActive, setDryRunActive] = useState(false)
  const [runSummary, setRunSummary] = useState(null)
  const [excelVerify, setExcelVerify] = useState(null)
  const [verifyLoading, setVerifyLoading] = useState(false)

  const [needsFileInput, setNeedsFileInput] = useState(null)
  const [needsFileMessage, setNeedsFileMessage] = useState('')
  const [needsFileAcceptedTypes, setNeedsFileAcceptedTypes] = useState(null)
  const pendingFileInputRef = useRef('')

  const [planTitle, setPlanTitle] = useState('')
  const [needsFileSelection, setNeedsFileSelection] = useState(null)
  const [needsFileSelectionFiles, setNeedsFileSelectionFiles] = useState([])
  const [needsFileSelectionMessage, setNeedsFileSelectionMessage] = useState('')

  const [browserStepConfirmation, setBrowserStepConfirmation] = useState(null)
  const [guidedExportStepId, setGuidedExportStepId] = useState(null)
  const [browserLoading, setBrowserLoading] = useState(false)

  // ── Workflow Recording ─────────────────────────────────────────
  const recorder = useRecording()
  const [wfShowOverlay, setWfShowOverlay] = useState(false)
  const [wfShowPreview, setWfShowPreview] = useState(false)
  const [wfShowDraft, setWfShowDraft] = useState(false)
  const [wfConvertLoading, setWfConvertLoading] = useState(false)
  const [wfSaveLoading, setWfSaveLoading] = useState(false)

  // ── Email Automation (Phase 34) ──────────────────────────────────
  const [emailStepState, setEmailStepState] = useState(null)
  const [emailMessages, setEmailMessages] = useState([])
  const [emailSelectedIds, setEmailSelectedIds] = useState([])
  const [emailDownloads, setEmailDownloads] = useState([])
  const [emailDownloadFolder, setEmailDownloadFolder] = useState('')
  const [emailLoading, setEmailLoading] = useState(false)
  const [emailGmailConnected, setEmailGmailConnected] = useState(false)
  const [emailGmailAccount, setEmailGmailAccount] = useState(null)
  const [emailPendingStepLogId, setEmailPendingStepLogId] = useState(null)

  const [messages, setMessages] = useState([])
  const [currentStep, setCurrentStep] = useState(initialState ? 1 : 0)
  const [actionMsg, setActionMsg] = useState('')
  const chatEndRef = useRef(null)

  // ── Voice helpers ──────────────────────────────────────────────
  const STOP_COMMANDS = [
    'stop', 'done', 'finish', 'finished',
    "that's it", 'thats it',
    'submit', 'send it',
    'bas', 'ruk jao', 'band karo', 'ho gaya', 'khatam',
    'done karo',
  ]

  function normalizeTranscript(text) {
    return text
      .replace(/\s+/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .trim()
  }

  function dedupeTranscript(text) {
    const trimmed = text.trim()
    const lower = trimmed.toLowerCase()
    const words = lower.split(/\s+/)
    if (words.length >= 4) {
      const half = Math.floor(words.length / 2)
      if (words.slice(0, half).join(' ') === words.slice(half).join(' ')) {
        return trimmed.split(/\s+/).slice(0, half).join(' ')
      }
    }
    const match = trimmed.match(/^(.+?)([A-Z].*)$/)
    if (match) {
      const first = match[1].toLowerCase().trim()
      const second = match[2].toLowerCase().trim()
      if (first === second) {
        return match[1].trim()
      }
    }
    return text
  }

  function extractStopCommand(text) {
    const trimmed = text.trim()
    const lower = trimmed.toLowerCase()
    for (const cmd of STOP_COMMANDS) {
      if (lower.endsWith(cmd)) {
        const prefix = trimmed.slice(0, -cmd.length).trim()
        return { shouldStop: true, cleanedText: normalizeTranscript(prefix) }
      }
    }
    return { shouldStop: false, cleanedText: text }
  }

  // ── Recording state ──────────────────────────────────────────────
  const [recording, setRecording] = useState('idle') // idle | recording | transcribing | permission_denied
  const [recordingTime, setRecordingTime] = useState(0)
  const [autoStopMessage, setAutoStopMessage] = useState('')
  const recognitionRef = useRef(null)
  const timerRef = useRef(null)
  const finalTranscriptRef = useRef('')
  const autoStoppedRef = useRef(false)
  const recordingRef = useRef('idle')

  useEffect(() => {
    recordingRef.current = recording
  }, [recording])

  const startRecording = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setRecording('permission_denied')
      return
    }
    finalTranscriptRef.current = ''
    autoStoppedRef.current = false
    setAutoStopMessage('')
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'
    recognitionRef.current = recognition

    recognition.onresult = (event) => {
      let interimTranscript = ''
      let newFinal = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const text = result[0].transcript
        if (result.isFinal) {
          newFinal += ' ' + text
        } else {
          interimTranscript += text
        }
      }
      if (newFinal) {
        finalTranscriptRef.current += ' ' + newFinal
        finalTranscriptRef.current = finalTranscriptRef.current.trim()
      }
      let displayText = finalTranscriptRef.current
      if (interimTranscript) {
        displayText += ' ' + interimTranscript
      }
      displayText = normalizeTranscript(displayText)
      displayText = dedupeTranscript(displayText)
      setCommand(displayText)

      if (newFinal) {
        const { shouldStop, cleanedText } = extractStopCommand(finalTranscriptRef.current)
        if (shouldStop) {
          autoStoppedRef.current = true
          finalTranscriptRef.current = cleanedText
          setCommand(cleanedText)
          setAutoStopMessage(cleanedText ? 'Stopped. Review and send your command.' : 'Recording stopped.')
          setRecording('idle')
          stopRecordingTimer()
          try { recognition.stop() } catch {}
        }
      }
    }
    recognition.onerror = () => {
      setRecording('permission_denied')
      stopRecordingTimer()
    }
    recognition.onend = () => {
      if (!autoStoppedRef.current && recordingRef.current === 'recording') {
        setRecording('transcribing')
        setTimeout(() => setRecording('idle'), 800)
      }
      autoStoppedRef.current = false
      stopRecordingTimer()
    }
    try {
      recognition.start()
      setRecording('recording')
      setRecordingTime(0)
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1)
      }, 1000)
    } catch {
      setRecording('permission_denied')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch {}
      recognitionRef.current = null
    }
    setRecording('transcribing')
    stopRecordingTimer()
    setTimeout(() => setRecording('idle'), 800)
  }, [])

  const stopRecordingTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const toggleRecording = useCallback(() => {
    if (recording === 'recording') {
      stopRecording()
    } else {
      setAutoStopMessage('')
      startRecording()
    }
  }, [recording, startRecording, stopRecording])

  const formatRecordingTime = (seconds) => {
    const m = String(Math.floor(seconds / 60)).padStart(2, '0')
    const s = String(seconds % 60).padStart(2, '0')
    return `${m}:${s}`
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop() } catch {}
      }
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      try { chatEndRef.current?.scrollIntoView?.({ behavior: 'smooth' }) } catch {}
    }, 50)
  }, [])

  const clearRun = () => {
    setRunId(null); setRunMode(null); setRunStatus(null)
    setRunSteps([]); setCurrentStepIndex(-1)
    setRunResults([]); setDryRunActive(false); setStepExecuting(false)
    setRunSummary(null); setExcelVerify(null); setPlanTitle('')
    setNeedsFileInput(null); setNeedsFileMessage(''); setNeedsFileAcceptedTypes(null); pendingFileInputRef.current = ''
    setNeedsFileSelection(null); setNeedsFileSelectionFiles([]); setNeedsFileSelectionMessage('')
    setBrowserStepConfirmation(null); setGuidedExportStepId(null); setBrowserLoading(false)
  }

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const [status, ctx, wfs] = await Promise.all([
        api.agentStatus().catch(() => ({ provider: 'mock', status: 'unknown' })),
        api.agentContext().catch(() => ({ context: {} })),
        api.listAgentWorkflows().catch(() => ({ workflows: [] })),
      ])
      setAgentStatus(status); setContext(ctx.context || {}); setWorkflows(wfs.workflows || [])
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  // Listen for New Task events from Sidebar
  useEffect(() => {
    function handleNewTask() {
      setCommand('')
      setPlan(null)
      setPlanId(null)
      setRunId(null)
      setRunSteps([])
      setRunResults([])
      setMessages([])
      setCurrentStep(0)
      setError(null)
      setShowSaveForm(false)
      setSaveResult(null)
      setRepeatResult(null)
      setSkillMatch(null)
      setActionMsg('')
      setTimeout(() => {
        if (commandInputRef.current) {
          commandInputRef.current.focus()
        }
      }, 100)
    }
    window.addEventListener('officepilot:new-task', handleNewTask)
    return () => window.removeEventListener('officepilot:new-task', handleNewTask)
  }, [])

  // Recover recording overlay on page refresh
  useEffect(() => {
    (async () => {
      try {
        const cur = await recorder.checkCurrentSession()
        if (cur && cur.status === 'recording') {
          setWfShowOverlay(true)
        }
      } catch {
        // not recording — noop
      }
    })()
  }, [])

  // ── Workflow Recording Handlers ────────────────────────────────
  const handleWorkflowStartRecording = useCallback(async () => {
    try {
      setPlanning(true)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Starting workflow recording...', time: formatTime() }])
      await recorder.startRecording('', 'voice')
      setWfShowOverlay(true)
      setWfShowPreview(false)
      setWfShowDraft(false)
      scrollToBottom()
    } catch (err) {
      setError(err.message)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error starting recording: ${err.message}`, time: formatTime(), isError: true }])
    } finally {
      setPlanning(false)
    }
  }, [recorder])

  const handleWorkflowStopRecording = useCallback(async () => {
    let sid = recorder.session?.session_id
    if (!sid) {
      const cur = await recorder.checkCurrentSession()
      sid = cur?.session_id
    }
    if (!sid) return
    try {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Stopping recording...', time: formatTime() }])
      await recorder.stopRecording(sid)
      setWfShowOverlay(false)
      setWfShowPreview(true)
      scrollToBottom()
    } catch (err) {
      setError(err.message)
    }
  }, [recorder])

  const handleWfStopRecording = useCallback(async () => {
    if (!recorder.session?.session_id) return
    try {
      await recorder.stopRecording(recorder.session.session_id)
      setWfShowOverlay(false)
      setWfShowPreview(true)
      scrollToBottom()
    } catch (err) {
      setError(err.message)
    }
  }, [recorder])

  const handleWfCancelRecording = useCallback(async () => {
    if (!recorder.session?.session_id) return
    try {
      await recorder.cancelRecording(recorder.session.session_id)
      setWfShowOverlay(false)
      setWfShowPreview(false)
      setWfShowDraft(false)
    } catch (err) {
      setError(err.message)
    }
  }, [recorder])

  const handleWfConvertToSkill = useCallback(async () => {
    if (!recorder.session?.session_id) return
    setWfConvertLoading(true)
    try {
      const title = recorder.session?.title || 'Recorded Workflow'
      await recorder.convertToSkill(recorder.session.session_id, title, 'Converted from recorded workflow')
      setWfShowPreview(false)
      setWfShowDraft(true)
      scrollToBottom()
    } catch (err) {
      setError(err.message)
    } finally {
      setWfConvertLoading(false)
    }
  }, [recorder])

  const handleWfSaveSkill = useCallback(async () => {
    if (!recorder.draft?.id) return
    setWfSaveLoading(true)
    try {
      await recorder.saveAsSkill(recorder.draft.id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `✅ Skill "${recorder.draft.name}" saved! You can now trigger it by saying: "${(recorder.draft.trigger_phrases || []).join('", "')}"`,
        time: formatTime(),
      }])
      setWfShowDraft(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setWfSaveLoading(false)
    }
  }, [recorder])

  const handleWfRejectDraft = useCallback(async () => {
    if (!recorder.draft?.id) return
    try {
      await recorder.rejectDraft(recorder.draft.id)
      setWfShowDraft(false)
      setMessages(prev => [...prev, {
        role: 'assistant', content: '❌ Skill draft rejected.', time: formatTime(),
      }])
    } catch (err) {
      setError(err.message)
    }
  }, [recorder])

  // ── Email Automation Handlers ────────────────────────────────────
  const handleEmailStepOutput = useCallback((stepOutput) => {
    if (stepOutput.email_search_results) {
      setEmailMessages(stepOutput.messages || [])
      setEmailStepState('search_results')
      setEmailSelectedIds((stepOutput.messages || []).map(m => m.message_id))
      if (stepOutput.mode === 'mock') {
        setEmailGmailConnected(true)
        setEmailGmailAccount({ email: 'mock-user@gmail.com', status: 'mock' })
      }
      return
    }
    if (stepOutput.needs_connection) {
      setEmailStepState('needs_connection')
      return
    }
    if (stepOutput.attachment_download_success) {
      setEmailDownloads(stepOutput.downloads || [])
      setEmailDownloadFolder(stepOutput.output_folder || '')
      setEmailStepState('download_success')
      return
    }
    if (stepOutput.needs_input?.field === 'output_folder' || stepOutput.needs_input?.field_type === 'folder_picker') {
      setEmailStepState('needs_folder')
      return
    }
  }, [])

  const handleEmailConnectGmail = useCallback(async () => {
    setEmailLoading(true)
    try {
      const accounts = await api.emailListAccounts()
      if (accounts && accounts.length > 0) {
        const acct = accounts[0]
        setEmailGmailConnected(true)
        setEmailGmailAccount({ email: acct.email || 'connected', status: 'connected', id: acct.id })
        setEmailStepState(null)
        return
      }
      const res = await api.emailSearch({ provider: 'gmail', query: 'has:attachment newer_than:30d invoice', max_results: 1 })
      if (res.messages && res.messages.length > 0) {
        setEmailGmailConnected(true)
        setEmailGmailAccount({ email: 'connected', status: 'connected' })
        setEmailStepState(null)
      } else {
        setEmailGmailConnected(true)
        setEmailGmailAccount({ email: 'mock-user@gmail.com', status: 'mock' })
        setEmailStepState(null)
      }
    } catch {
      setEmailGmailConnected(true)
      setEmailGmailAccount({ email: 'mock-user@gmail.com', status: 'mock' })
      setEmailStepState(null)
    } finally {
      setEmailLoading(false)
    }
  }, [])

  const handleEmailApproveDownload = useCallback(async (selectedIds) => {
    if (!selectedIds || selectedIds.length === 0) {
      setError('Please select at least one message')
      return
    }
    setEmailLoading(true)
    setEmailSelectedIds(selectedIds)
    setEmailStepState('awaiting_folder')
    setEmailLoading(false)
  }, [])

  const handleEmailDownloadWithFolder = useCallback(async (messageIds, folder) => {
    setEmailLoading(true)
    try {
      if (runId && emailPendingStepLogId) {
        const result = await api.executeRunStep(runId, {
          step_log_id: emailPendingStepLogId,
          output_folder: folder,
          download_folder: folder,
          message_ids: messageIds,
        })
        const stepOutput = result.result?.output || {}
        if (stepOutput.attachment_download_success) {
          setEmailDownloads(stepOutput.downloads || [])
          setEmailDownloadFolder(stepOutput.output_folder || folder)
          setEmailStepState('download_success')
          setEmailPendingStepLogId(null)
          const idx = runSteps.findIndex(s => s.step_log_id === emailPendingStepLogId)
          if (idx >= 0) {
            const updated = [...runSteps]
            updated[idx] = { ...updated[idx], status: result.step_status }
            setRunSteps(updated)
            setCurrentStepIndex(idx)
          }
          setRunResults(prev => [...prev, result])
          if (result.message) {
            setMessages(prev => [...prev, { role: 'assistant', content: result.message, time: formatTime() }])
          }
        }
      } else {
        const res = await api.emailBatchDownload({
          provider: 'gmail',
          message_ids: messageIds,
          output_folder: folder,
        })
        setEmailDownloads(res.downloads || [])
        setEmailDownloadFolder(res.output_folder || folder)
        setEmailStepState('download_success')
        if (res.total_downloaded > 0) {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `Downloaded ${res.total_downloaded} attachment(s) to ${res.output_folder || folder}`,
            time: formatTime(),
          }])
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setEmailLoading(false)
    }
  }, [runId, emailPendingStepLogId, runSteps])

  const handleEmailClear = useCallback(() => {
    setEmailStepState(null)
    setEmailMessages([])
    setEmailSelectedIds([])
    setEmailDownloads([])
    setEmailDownloadFolder('')
    setEmailPendingStepLogId(null)
  }, [])

  const handleCreateExcelSummaryFromAttachment = useCallback(() => {
    const spreadsheetFile = emailDownloads.find(
      d => (d.mime_type || '').includes('spreadsheet') || (d.filename || '').match(/\.(xlsx|xls|csv)$/i)
    )
    if (spreadsheetFile?.filepath) {
      handleCreateExcelSummaryFromFile(spreadsheetFile.filepath)
    }
  }, [emailDownloads])

  const handleEmailOpenFolder = useCallback(() => {
    if (emailDownloadFolder) {
      handleOpenFile(emailDownloadFolder)
    }
  }, [emailDownloadFolder])

  const NAVIGATION_COMMANDS = {
    'open voice command center': '/voice',
    'voice commands': '/voice',
    'voice command center': '/voice',
    'show workflow memory': '/app/workflow-memory',
    'workflow memory': '/app/workflow-memory',
    'open workflow memory': '/app/workflow-memory',
    'settings': '/app/settings',
    'open settings': '/app/settings',
  }

  const handlePlanTask = async (forceNewPlan = false) => {
    if (!command.trim()) return
    const cmdLower = command.trim().toLowerCase()
    const navRoute = NAVIGATION_COMMANDS[cmdLower]
    if (navRoute) {
      navigate(navRoute)
      return
    }
    setAutoStopMessage('')
    const userMsg = { role: 'user', content: command.trim(), time: formatTime() }
    setMessages(prev => [...prev, userMsg])
    setPlanning(true); setError(null); setPlan(null); setPlanId(null)
    setSkillMatch(null)
    clearRun(); setRunSummary(null); setSaveResult(null); setCurrentStep(1); setExcelVerify(null)
    try {
      const body = { command: command.trim() }
      if (forceNewPlan) body.force_new_plan = true
      const result = await api.planAgentTask(body)

      if (result.type === 'navigation') {
        if (result.route) {
          navigate(result.route)
        }
        return
      }

      if (result.type === 'skill_match') {
        setSkillMatch(result.matched_skill)
        setVoiceReply(result.voice_reply_text || '')
        setSuggestedActions(result.suggested_next_actions || [])
        setCurrentStep(2)
      } else {
        setPlan(result.plan); setPlanId(result.plan_id)
        setPlanTitle(result.plan?.task_title || '')
        setDetectedLanguage(result.detected_language || null)
        setVoiceReply(result.voice_reply_text || null)
        setSuggestedActions(result.suggested_next_actions || [])
        if (result.matched_workflow_id) setMatchedWorkflow({ id: result.matched_workflow_id, name: result.matched_workflow_name })
        setCurrentStep(2)

        // Workflow recording commands
        if (result.plan?.task_type === 'start_recording') {
          setPlan(null); setPlanId(null)
          handleWorkflowStartRecording()
          return
        }
        if (result.plan?.task_type === 'stop_recording') {
          setPlan(null); setPlanId(null)
          handleWorkflowStopRecording()
          return
        }
      }
    } catch (err) {
      setError(err.message)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}`, time: formatTime(), isError: true }])
    }
    finally { setPlanning(false); setCommand(''); scrollToBottom() }
  }

  const handleApprovePlan = async (mode = 'dry_run') => {
    if (!planId) return
    setExecuting(true); setError(null); setExcelVerify(null)
    try {
      const result = await api.approveAgentPlan(planId, { mode })
      setRunId(result.run_id); setRunMode(result.mode); setRunStatus(result.status)
      setRunSteps(result.steps || []); setCurrentStepIndex(-1); setRunResults([])
      setPlan({ ...plan, requires_approval: false })
      if (mode === 'dry_run') setCurrentStep(3)
      else setCurrentStep(4)
    } catch (err) { setError(err.message) }
    finally { setExecuting(false) }
  }

  const handleExecuteNextStep = async () => {
    if (!runId) return
    setStepExecuting(true); setError(null)
    try {
      const pending = runSteps.find(s => s.status === 'pending')
      if (!pending) { setError('No pending steps'); setStepExecuting(false); return }
      const stepLogId = needsFileInput || pending.step_log_id
      const body = { step_log_id: stepLogId }
      if (pendingFileInputRef.current) {
        body.file_path = pendingFileInputRef.current
      }
      const result = await api.executeRunStep(runId, body)
      const idx = runSteps.findIndex(s => s.step_log_id === result.step_log_id)
      const stepOutput = result.result?.output || {}

      if (stepOutput.needs_input && result.step_status === 'pending') {
        if (stepOutput.field === 'output_folder' || stepOutput.field_type === 'folder_picker') {
          setEmailPendingStepLogId(result.step_log_id)
          setEmailStepState('needs_folder')
          setStepExecuting(false)
          return
        }
        if (pendingFileInputRef.current) {
          const retryBody = { step_log_id: result.step_log_id, file_path: pendingFileInputRef.current }
          pendingFileInputRef.current = ''
          const retryResult = await api.executeRunStep(runId, retryBody)
          const retryIdx = runSteps.findIndex(s => s.step_log_id === retryResult.step_log_id)
          const retryUpdated = [...runSteps]
          if (retryIdx >= 0) retryUpdated[retryIdx] = { ...retryUpdated[retryIdx], status: retryResult.step_status }
          setRunSteps(retryUpdated); setCurrentStepIndex(retryIdx)
          setRunResults(prev => [...prev, retryResult])
          if (retryResult.step_status === 'completed' && !retryResult.next_step) {
            setRunStatus('completed'); setCurrentStep(5)
          }
          setStepExecuting(false)
          return
        }
        setNeedsFileInput(result.step_log_id)
        setNeedsFileMessage(stepOutput.message || 'Choose the Excel file to summarize')
        setNeedsFileAcceptedTypes(stepOutput.accepted_types || null)
        pendingFileInputRef.current = ''
        setStepExecuting(false)
        return
      }

      // File selection from file_find_in_downloads
      if (stepOutput.status === 'needs_file_selection' && stepOutput.files && stepOutput.files.length > 0) {
        setNeedsFileSelection(result.step_log_id)
        setNeedsFileSelectionFiles(stepOutput.files)
        setNeedsFileSelectionMessage(stepOutput.message || 'Multiple files found. Select one:')
        setStepExecuting(false)
        return
      }

      // Auto-select single file from file_find_in_downloads
      if (stepOutput.status === 'selected_file' && stepOutput.selected_file_path) {
        pendingFileInputRef.current = stepOutput.selected_file_path
      }

      // needs_file_picker — show FilePickerCard
      if (stepOutput.status === 'needs_file_picker') {
        setNeedsFileInput(result.step_log_id)
        setNeedsFileMessage(stepOutput.message || 'No matching files found. Please select a file manually:')
        setNeedsFileAcceptedTypes(['.xlsx', '.xls', '.csv'])
        setStepExecuting(false)
        return
      }

      setNeedsFileInput(null); setNeedsFileMessage(''); setNeedsFileAcceptedTypes(null); pendingFileInputRef.current = ''
      setNeedsFileSelection(null); setNeedsFileSelectionFiles([]); setNeedsFileSelectionMessage('')
      const updatedSteps = [...runSteps]
      if (idx >= 0) updatedSteps[idx] = { ...updatedSteps[idx], status: result.step_status }
      setRunSteps(updatedSteps); setCurrentStepIndex(idx)
      setRunResults(prev => [...prev, result])

      const toolName = result.tool || ''
      const norm = normalizeBrowserStepResult(result.result, toolName)
      if (norm.cardType === 'manual_login') {
        setBrowserStepConfirmation(result.step_log_id)
      }
      if (norm.cardType === 'guided_download') {
        setGuidedExportStepId(result.step_log_id)
      }

      // Email automation (Phase 34) — detect step output
      if (stepOutput.email_search_results) {
        handleEmailStepOutput(stepOutput)
      }
      if (stepOutput.needs_connection) {
        handleEmailStepOutput(stepOutput)
      }
      if (stepOutput.attachment_download_success) {
        handleEmailStepOutput(stepOutput)
      }

      if (result.step_status === 'completed' && !result.next_step) {
        setRunStatus('completed')
        setCurrentStep(5)
      }
    } catch (err) { setError(err.message) }
    finally { setStepExecuting(false) }
  }

  const handleDryRunAll = async () => {
    if (!runId) return
    setDryRunActive(true); setError(null)
    try {
      const result = await api.dryRunRun(runId)
      const updatedSteps = runSteps.map(s => ({ ...s, status: 'completed' }))
      setRunSteps(updatedSteps); setRunResults(result.results || []); setRunStatus('completed')
      setCurrentStep(5)
    } catch (err) { setError(err.message) }
    finally { setDryRunActive(false) }
  }

  const handleStartLive = async () => {
    if (!runId) return
    setExecuting(true); setError(null)
    try {
      const result = await api.startLiveRun(runId)
      setRunMode('live'); setRunStatus('running'); setCurrentStep(4)
    } catch (err) { setError(err.message) }
    finally { setExecuting(false) }
  }

  const handleEmergencyStop = async () => {
    if (runId) {
      try {
        await api.stopRun(runId, { reason: 'User clicked Emergency Stop' })
        setRunStatus('stopped')
        setRunSteps(runSteps.map(s => s.status === 'pending' ? { ...s, status: 'cancelled' } : s))
      } catch (err) { setError(err.message) }
    } else { clearRun(); setPlan(null); setPlanId(null); setCommand('') }
  }

  const handleSaveWorkflow = async () => {
    if (!planId || !workflowName.trim()) return
    setSaving(true); setError(null)
    try {
      const result = await api.saveAgentWorkflow({
        plan_id: planId,
        workflow_name: workflowName.trim(),
        workflow_description: workflowDesc.trim() || undefined,
        trigger_phrases: DEMO_TRIGGER_PHRASES,
      })
      setSaveResult(result); setShowSaveForm(false); setCurrentStep(6)
      await load()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleLoadSummary = async () => {
    if (!runId) return
    try {
      const summary = await api.getAgentRunSummary(runId)
      setRunSummary(summary)
    } catch (err) { /* ignore */ }
  }

  const handleSaveSkill = async () => {
    if (!planId) return
    setSaving(true); setError(null)
    try {
      const result = await api.createSkillFromWorkflow({
        plan_id: planId,
        name: `${workflowName.trim()} Skill`,
        description: workflowDesc.trim(),
      })
      setSaveResult({ ...saveResult, skill_name: result.name, skill_id: result.skill_id })
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleVerifyExcel = async () => {
    if (!runId) return
    try {
      const result = await api.verifyAgentRunExcel(runId)
      setExcelVerify(result)
    } catch (err) { setError(err.message) }
    finally { setVerifyLoading(false) }
  }

  const handleFileSelected = (filePath) => {
    pendingFileInputRef.current = filePath
    setStepExecuting(true)
    handleExecuteNextStep()
  }

  const handleFilePickerCancel = () => {
    setNeedsFileInput(null); setNeedsFileMessage(''); setNeedsFileAcceptedTypes(null); pendingFileInputRef.current = ''
    setNeedsFileSelection(null); setNeedsFileSelectionFiles([]); setNeedsFileSelectionMessage('')
  }

  const handleBrowserUserConfirmed = async (stepLogId) => {
    setBrowserLoading(true)
    try {
      setBrowserStepConfirmation(null)
      const body = { step_log_id: stepLogId, user_confirmed: true, manual_login_complete: true }
      const result = await api.executeRunStep(runId, body)
      const idx = runSteps.findIndex(s => s.step_log_id === result.step_log_id)
      const updatedSteps = [...runSteps]
      if (idx >= 0) updatedSteps[idx] = { ...updatedSteps[idx], status: result.step_status }
      setRunSteps(updatedSteps); setCurrentStepIndex(idx)
      setRunResults(prev => [...prev, result])
      if (result.step_status === 'completed' && !result.next_step) {
        setRunStatus('completed'); setCurrentStep(5)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBrowserLoading(false)
    }
  }

  const handleGuidedExportContinue = async (stepLogId) => {
    setBrowserLoading(true)
    try {
      setGuidedExportStepId(null)
      const body = { step_log_id: stepLogId, guided_export_complete: true }
      const result = await api.executeRunStep(runId, body)
      const idx = runSteps.findIndex(s => s.step_log_id === result.step_log_id)
      const updatedSteps = [...runSteps]
      if (idx >= 0) updatedSteps[idx] = { ...updatedSteps[idx], status: result.step_status }
      setRunSteps(updatedSteps); setCurrentStepIndex(idx)
      setRunResults(prev => [...prev, result])
      if (result.step_status === 'completed' && !result.next_step) {
        setRunStatus('completed'); setCurrentStep(5)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBrowserLoading(false)
    }
  }

  const handleBrowserCancel = () => {
    setBrowserStepConfirmation(null)
    setGuidedExportStepId(null)
    handleEmergencyStop()
  }

  const handleOpenFile = (filePath) => {
    if (window.__TAURI__ && window.__TAURI__.shell) {
      window.__TAURI__.shell.open(filePath).catch(err => {
        setError(`Failed to open file: ${err.message}`)
      })
    } else {
      setError(`File saved at: ${filePath}. Use your file explorer to open it.`)
    }
  }

  const handleCreateExcelSummaryFromFile = async (filePath) => {
    setStepExecuting(true)
    try {
      pendingFileInputRef.current = filePath
      const planResult = await api.planAgentTask({ command: 'create excel summary of the downloaded file' })
      if (!planResult.plan || !planResult.plan_id) {
        setError('Could not create Excel summary plan')
        return
      }
      setCommand('')
      setPlan(planResult.plan)
      setPlanId(planResult.plan_id)
      setDetectedLanguage(planResult.detected_language || null)
      setVoiceReply(null)
      setSkillMatch(null)

      const approveResult = await api.approveAgentPlan(planResult.plan_id, { mode: 'dry_run' })
      setRunId(approveResult.run_id)
      setRunMode(approveResult.mode)
      setRunStatus(approveResult.status)
      setRunSteps(approveResult.steps || [])
      setCurrentStepIndex(-1)
      setRunResults([])
      scrollToBottom()
    } catch (err) {
      setError(err.message)
    } finally {
      setStepExecuting(false)
    }
  }

  const handleSaveAsSkillFromBrowser = async () => {
    if (!planId) return
    setBrowserLoading(true)
    try {
      const result = await api.createSkillFromWorkflow({
        plan_id: planId,
        name: `${workflowName.trim()} Skill`,
        description: workflowDesc.trim(),
      })
      setSaveResult({ ...saveResult, skill_name: result.name, skill_id: result.skill_id })
    } catch (err) {
      setError(err.message)
    } finally {
      setBrowserLoading(false)
    }
  }

  useEffect(() => {
    if (runStatus === 'completed') handleLoadSummary()
  }, [runStatus])

  const handleRepeatWorkflow = async (workflowId) => {
    setRepeatLoading(true); setError(null); setRepeatResult(null)
    try {
      const result = await api.repeatAgentWorkflow(workflowId, { mode: repeatMode })
      setRepeatResult(result); setShowRepeatForm(false)
    } catch (err) { setError(err.message) }
    finally { setRepeatLoading(false) }
  }

  const handleRepeatRecent = async () => {
    setRepeatLoading(true); setError(null); setRepeatResult(null)
    try {
      const result = await api.repeatRecentAgentWorkflow({ mode: repeatMode })
      setRepeatResult(result)
    } catch (err) { setError(err.message) }
    finally { setRepeatLoading(false) }
  }

  if (loading) return <LoadingState text="Loading Accountant Agent..." />

  const pendingSteps = runSteps.filter(s => s.status === 'pending')
  const completedSteps = runSteps.filter(s => s.status !== 'pending' && s.status !== 'cancelled')

  const handleSuggestion = (cmd) => {
    setCommand(cmd)
  }

  return (
    <div className="agent-chat-layout agent-chat-page">
      {/* Emergency Stop (always visible) */}
      <div style={{ position: 'sticky', top: 0, zIndex: 10, display: 'flex', justifyContent: 'flex-end', padding: '4px 16px', background: 'var(--bg, #f8fafc)' }}>
        <button className="btn btn--danger btn--sm" style={{ fontSize: '11px', padding: '2px 10px' }} onClick={handleEmergencyStop} disabled={context?.kill_switch_active}>
          Emergency Stop
        </button>
      </div>

      {/* Workflow Recording Overlay */}
      {wfShowOverlay && recorder.session && recorder.session.status === 'recording' && (
        <WorkflowRecordingOverlay
          sessionId={recorder.session.session_id}
          title={recorder.session.title}
          startedAt={recorder.session.started_at}
          eventCount={recorder.events.length}
          onStop={handleWfStopRecording}
          onCancel={handleWfCancelRecording}
        />
      )}

      {/* Chat Messages */}
      <div className="agent-chat-messages">
        {/* Welcome Screen */}
        {messages.length === 0 && !plan && !runId && !skillMatch && (
          <div className="agent-welcome">
            <div className="agent-welcome-header">
              <div className="agent-welcome-avatar">A</div>
              <h2>What would you like OfficePilot to do?</h2>
              <p className="agent-welcome-sub">Create reports, download invoice attachments, summarize spreadsheets, or record repeat workflows.</p>
            </div>

            <div className="agent-automation-section">
              <div className="agent-section-title">Popular automations</div>
              <div className="agent-card-grid">
                {AUTOMATION_CARDS.map(card => (
                  <button
                    key={card.command}
                    className="agent-automation-card"
                    onClick={() => { setCommand(card.command); setPlan(null); setPlanId(null); clearRun(); setRunSummary(null); setCurrentStep(0); setMessages([]) }}
                  >
                    <div className="agent-card-label">{card.label}</div>
                    <div className="agent-card-desc">{card.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="agent-more-section">
              <div className="agent-section-title">More actions</div>
              <div className="agent-more-row">
                {MORE_ACTIONS.map(action => {
                  if (action.navigate) {
                    return (
                      <button key={action.label} className="agent-more-btn" onClick={() => navigate(action.navigate)}>
                        {action.label}
                      </button>
                    )
                  }
                  return (
                    <button
                      key={action.label}
                      className="agent-more-btn"
                      onClick={() => { setCommand(action.command); setPlan(null); setPlanId(null); clearRun(); setRunSummary(null); setCurrentStep(0); setMessages([]) }}
                    >
                      {action.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* Message List */}
        {messages.map((msg, i) => (
          <div key={i} className={`agent-chat-msg agent-chat-msg--${msg.role}`}>
            <div className="agent-chat-msg-avatar">
              {msg.role === 'user' ? 'U' : 'A'}
            </div>
            <div className={`agent-chat-msg-bubble ${msg.isError ? 'agent-chat-msg--error' : ''}`}>
              <div className="agent-chat-msg-text">{msg.content}</div>
              <div className="agent-chat-msg-time">{msg.time}</div>
            </div>
          </div>
        ))}

        {/* Planning indicator */}
        {planning && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <div className="agent-thinking-dots"><span>.</span><span>.</span><span>.</span></div>
              <div className="agent-chat-msg-time">thinking...</div>
            </div>
          </div>
        )}

        {/* Bot Response: Skill Match */}
        {skillMatch && !planning && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <SkillMatchCard
                matchedSkill={skillMatch}
                voiceReply={voiceReply}
                onDryRun={(result) => {
                  setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `✅ Dry-run completed for skill "${skillMatch.name}". ${skillMatch.steps?.length || 0} steps verified.`,
                    time: formatTime(),
                  }])
                }}
                onCreateNewPlan={() => {
                  setSkillMatch(null)
                  const originalCmd = messages.filter(m => m.role === 'user').pop()?.content || command
                  setCommand(originalCmd)
                  handlePlanTask(true)
                }}
                onCancel={() => {
                  setSkillMatch(null)
                  setVoiceReply(null)
                }}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {/* Bot Response: Plan */}
        {plan && !planning && !skillMatch && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble agent-chat-msg--plan">
              <div className="agent-plan-header">
                <span className="agent-plan-title">{plan.task_title || 'Task Plan'}</span>
                <span className={`badge badge--${plan.risk_level === 'blocked' ? 'danger' : plan.risk_level === 'high' ? 'danger' : plan.risk_level === 'medium' ? 'warning' : 'success'}`}>
                  {plan.risk_level}
                </span>
                {detectedLanguage && detectedLanguage !== 'en' && (
                  <span className="badge badge--info">{detectedLanguage === 'urdu' ? 'اردو' : 'Roman Urdu'}</span>
                )}
              </div>
              {plan.task_summary && <p className="agent-plan-summary-text">{plan.task_summary}</p>}
              {plan.platform_detected && <p className="agent-plan-platform">Platform: {plan.platform_detected}</p>}
              {plan.can_save_workflow && <p className="agent-plan-saveable">✓ Can be saved as a reusable workflow</p>}

              {voiceReply && (
                <div className="agent-voice-reply">
                  <span className="voice-reply-icon">🗣</span>
                  <span>{voiceReply}</span>
                </div>
              )}

              {matchedWorkflow && (
                <div className="matched-workflow-card">
                  <strong>Matched Workflow:</strong> "{matchedWorkflow.name}"
                  <div className="agent-actions" style={{ marginTop: '8px' }}>
                    <button className="btn btn--sm btn--primary" onClick={() => { setCommand(`repeat ${matchedWorkflow.name} workflow`); handlePlanTask() }} disabled={planning}>
                      Repeat this Workflow
                    </button>
                  </div>
                </div>
              )}

              {plan.risk_level === 'blocked' && plan.blocked_reason && (
                <div className="alert error"><strong>Blocked:</strong> {plan.blocked_reason}</div>
              )}
              {plan.clarification_needed && (
                <div className="alert info"><strong>Clarification Needed:</strong> {plan.clarification_question}</div>
              )}

              {/* Steps */}
              {!plan.blocked_reason && !plan.clarification_needed && (plan.steps || []).length > 0 && !runId && (
                <>
                  <div className="agent-plan-steps">
                    {(plan.steps || []).map((step, i) => (
                      <div key={i} className="agent-plan-step">
                        <div className="agent-plan-step-num">{step.step_order}</div>
                        <div className="agent-plan-step-body">
                          <div className="agent-plan-step-header">
                            <span className={`agent-plan-step-type agent-plan-step-type--${step.risk_level === 'high' ? 'high' : step.risk_level === 'medium' ? 'medium' : 'low'}`}>
                              {step.step_type}
                            </span>
                            {step.requires_approval && <span className="badge badge--warning" style={{ fontSize: '10px' }}>Approval</span>}
                          </div>
                          <div className="agent-plan-step-text">{step.instruction}</div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="agent-plan-actions">
                    {plan.requires_approval !== false && (
                      <>
                        <button className="btn btn--primary" onClick={() => handleApprovePlan('dry_run')} disabled={executing || context?.kill_switch_active}>
                          {executing ? 'Approving...' : 'Approve & Dry-Run'}
                        </button>
                        <button className="btn btn--warning" onClick={() => handleApprovePlan('live')} disabled={executing || context?.kill_switch_active}>
                          Approve & Execute
                        </button>
                      </>
                    )}
                    <button className="btn btn--danger" onClick={handleEmergencyStop} disabled={context?.kill_switch_active}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {/* Run Execution Timeline (inline in chat) */}
        {runId && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <div className="agent-run-header">
                <span style={{ fontWeight: 600 }}>Run #{runId}</span>
                <span className={`badge badge--${runMode === 'live' ? 'warning' : 'info'}`}>{runMode === 'live' ? 'Live' : 'Dry-Run'}</span>
                <span className={`badge badge--${runStatus === 'completed' ? 'success' : runStatus === 'stopped' ? 'danger' : 'info'}`}>{runStatus}</span>
                <span className="agent-step-count">{completedSteps.length}/{runSteps.length} steps</span>
              </div>

              <div className="agent-run-timeline">
                {runSteps.map((step, i) => {
                  const result = runResults.find(r => r.step_log_id === step.step_log_id)
                  const isCurrent = i === currentStepIndex
                  const stepRes = result?.result || {}
                  const isDone = step.status !== 'pending' && step.status !== 'cancelled'
                  return (
                    <div key={step.step_log_id} className={`agent-timeline-step ${isDone ? 'agent-timeline-done' : ''} ${isCurrent ? 'agent-timeline-current' : ''}`}>
                      <div className="agent-timeline-marker">
                        {step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : step.status === 'cancelled' ? '—' : '○'}
                      </div>
                      <div className="agent-timeline-content">
                        <div className="agent-step-header">
                          <span className={`badge badge--${step.status === 'completed' ? 'success' : step.status === 'failed' ? 'danger' : step.status === 'blocked' ? 'danger' : step.status === 'cancelled' ? 'secondary' : 'info'}`}>
                            {step.step_type || (step.action_preview?.tool || 'step')} {step.step_order}
                          </span>
                        </div>
                        {step.action_preview?.instruction && <p className="agent-step-instruction">{step.action_preview.instruction}</p>}
                        {stepRes.message && (
                          <div className={`agent-step-result ${result?.step_status === 'completed' ? 'text-success' : 'text-danger'}`}>
                            {result?.step_status === 'completed' ? '✓' : '✗'} {stepRes.message}
                          </div>
                        )}
                        {stepRes.output?.filepath && <div className="agent-step-result text-success">📁 {stepRes.output.filepath}</div>}
                        {stepRes.output?.total !== undefined && <div className="agent-step-result text-success">💰 Total: {stepRes.output.total}</div>}
                        {needsFileInput === step.step_log_id && (
                          <div style={{ marginTop: 8 }}>
                            <FilePickerCard
                              message={needsFileMessage}
                              acceptedTypes={needsFileAcceptedTypes}
                              onFileSelected={handleFileSelected}
                              onCancel={handleFilePickerCancel}
                            />
                          </div>
                        )}

                        {needsFileSelection === step.step_log_id && needsFileSelectionFiles.length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            <FileSelectionCard
                              files={needsFileSelectionFiles}
                              message={needsFileSelectionMessage}
                              onFileSelected={(path) => handleFileSelected(path)}
                              onCancel={() => { setNeedsFileSelection(null); setNeedsFileSelectionFiles([]); setNeedsFileSelectionMessage('') }}
                            />
                          </div>
                        )}

                        {/* Browser cards */}
                        {(() => {
                          if (!result) return null
                          const stepTool = result.tool || step.step_type || step.action_preview?.tool || ''
                          const norm = normalizeBrowserStepResult(result.result, stepTool)
                          if (!norm.cardType) return null

                          if (norm.cardType === 'manual_login' && browserStepConfirmation === step.step_log_id) {
                            return (
                              <div style={{ marginTop: 8 }}>
                                <ManualLoginCard
                                  website={norm.website}
                                  status={norm.status}
                                  onLoggedIn={() => handleBrowserUserConfirmed(step.step_log_id)}
                                  onCancel={handleBrowserCancel}
                                  loading={browserLoading}
                                />
                              </div>
                            )
                          }

                          if (norm.cardType === 'guided_download' && guidedExportStepId === step.step_log_id) {
                            return (
                              <div style={{ marginTop: 8 }}>
                                <GuidedDownloadCard
                                  watchedFolder={norm.watchedFolder}
                                  waiting={norm.waiting}
                                  detectedFile={norm.detectedFile}
                                  outputPath={norm.outputPath}
                                  onContinue={norm.detectedFile ? () => handleGuidedExportContinue(step.step_log_id) : undefined}
                                  onCancel={handleBrowserCancel}
                                  loading={browserLoading}
                                />
                              </div>
                            )
                          }

                          if (norm.cardType === 'browser_result' && isDone) {
                            return (
                              <div style={{ marginTop: 8 }}>
                                <BrowserResultCard
                                  filePath={norm.filePath}
                                  filename={norm.filename}
                                  onOpenFile={norm.filePath ? () => handleOpenFile(norm.filePath) : undefined}
                                  onCreateExcelSummary={norm.filePath?.match(/\.(xlsx|xls|csv)$/i) ? () => handleCreateExcelSummaryFromFile(norm.filePath) : undefined}
                                  onSaveAsSkill={saveResult?.skill_name ? undefined : handleSaveAsSkillFromBrowser}
                                  loading={browserLoading}
                                />
                              </div>
                            )
                          }

                          if (norm.cardType === 'browser_automation' && !norm.blocked && isDone) {
                            return (
                              <div style={{ marginTop: 8 }}>
                                <BrowserAutomationCard
                                  url={norm.url}
                                  status={norm.status}
                                  nextAction={norm.nextAction}
                                  riskLevel={norm.riskLevel}
                                />
                              </div>
                            )
                          }

                          if (norm.cardType === 'blocked_warning') {
                            return (
                              <div className="alert error" style={{ marginTop: 8 }}>
                                <strong>Blocked:</strong> {norm.reason}
                              </div>
                            )
                          }

                          return null
                        })()}

                          {/* Email cards inline in timeline */}
                          {(() => {
                            if (!result) return null
                            const stepTool = result.tool || step.step_type || step.action_preview?.tool || ''
                            const emailNorm = normalizeEmailStepResult(result.result, stepTool)
                            if (!emailNorm.cardType) return null

                            if (emailNorm.cardType === 'gmail_connect' || emailNorm.cardType === 'gmail_mock' || emailNorm.cardType === 'gmail_connected') {
                              return (
                                <div style={{ marginTop: 8 }}>
                                  <GmailConnectCard
                                    status={emailNorm.status || 'disconnected'}
                                    email={emailNorm.email}
                                    accountId={emailNorm.accountId}
                                    onConnect={handleEmailConnectGmail}
                                    loading={emailLoading}
                                  />
                                </div>
                              )
                            }

                            if (emailNorm.cardType === 'email_search' && isDone) {
                              return (
                                <div style={{ marginTop: 8 }}>
                                  <EmailSearchPreviewCard
                                    messages={emailNorm.messages}
                                    resultCount={emailNorm.resultCount}
                                    query={emailNorm.query}
                                    selectedIds={emailNorm.messages.map(m => m.message_id)}
                                    onSelectionChange={setEmailSelectedIds}
                                    onApproveDownload={handleEmailApproveDownload}
                                    loading={emailLoading}
                                  />
                                </div>
                              )
                            }

                            if (emailNorm.cardType === 'needs_folder_input' && isDone) {
                              return (
                                <div style={{ marginTop: 8 }}>
                                  <AttachmentDownloadCard
                                    attachments={emailNorm.output?.downloads || []}
                                    messageIds={emailSelectedIds}
                                    onDownload={handleEmailDownloadWithFolder}
                                    onCancel={handleEmailClear}
                                    loading={emailLoading}
                                  />
                                </div>
                              )
                            }

                            if (emailNorm.cardType === 'email_download_result' && isDone) {
                              return (
                                <div style={{ marginTop: 8 }}>
                                  <EmailDownloadResultCard
                                    downloads={emailNorm.downloads}
                                    outputFolder={emailNorm.outputFolder}
                                    onCreateExcelSummary={handleCreateExcelSummaryFromAttachment}
                                    onSaveAsSkill={handleSaveAsSkillFromBrowser}
                                    onOpenFolder={handleEmailOpenFolder}
                                    onClear={handleEmailClear}
                                    loading={emailLoading}
                                  />
                                </div>
                              )
                            }

                            if (emailNorm.cardType === 'blocked_warning') {
                              return (
                                <div className="alert error" style={{ marginTop: 8 }}>
                                  <strong>Blocked:</strong> {emailNorm.reason}
                                </div>
                              )
                            }

                            return null
                          })()}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Run Actions */}
              <div className="agent-actions">
                {runStatus !== 'stopped' && runStatus !== 'completed' && runStatus !== 'failed' && (
                  <>
                    {runMode === 'dry_run' && (
                      <button className="btn btn--primary" onClick={handleDryRunAll} disabled={dryRunActive || context?.kill_switch_active}>
                        {dryRunActive ? 'Running...' : 'Run All Steps'}
                      </button>
                    )}
                    {pendingSteps.length > 0 && runMode !== 'dry_run' && (
                      <button className="btn btn--primary" onClick={handleExecuteNextStep} disabled={stepExecuting || context?.kill_switch_active}>
                        {stepExecuting ? 'Executing...' : `Execute Step ${pendingSteps[0].step_order}`}
                      </button>
                    )}
                    {runMode === 'dry_run' && runStatus !== 'completed' && (
                      <button className="btn btn--warning" onClick={handleStartLive} disabled={executing || context?.kill_switch_active}>
                        Switch to Live
                      </button>
                    )}
                  </>
                )}
                <button className="btn btn--danger" onClick={handleEmergencyStop} disabled={context?.kill_switch_active}>
                  {runStatus === 'stopped' ? 'Stopped' : 'Stop'}
                </button>
              </div>

              {/* Run Summary */}
              {runStatus === 'completed' && (
                <div className="agent-run-result-section">
                  <div className="alert success" style={{ fontSize: '0.9rem' }}>
                    <strong>✓ Run completed.</strong> {completedSteps.length} steps done in {runMode} mode.
                  </div>
                  {runSummary && (
                    <div className="agent-run-summary-detailed">
                      <div className="summary-lang">
                        {runSummary.summary_roman_urdu && <div className="summary-ru">{runSummary.summary_roman_urdu}</div>}
                        <div className="summary-en">{runSummary.summary_english}</div>
                      </div>
                      {runSummary.excel_file_path && (
                        <div className="summary-excel-path">
                          <span>📁 {runSummary.excel_file_path}</span>
                          <button className="btn btn--sm btn--secondary" onClick={handleVerifyExcel} disabled={verifyLoading}>
                            {verifyLoading ? 'Verifying...' : 'Verify Excel'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  {excelVerify && (
                    <div className={`alert ${excelVerify.file_exists ? 'success' : 'error'}`} style={{ marginTop: 8, fontSize: '0.85rem' }}>
                      {excelVerify.file_exists
                        ? `✅ Excel verified: ${excelVerify.excel_file_path} (${excelVerify.rows_written} rows, total ${excelVerify.expected_total})`
                        : `❌ Excel file not found`}
                    </div>
                  )}

                  {/* Save workflow CTA */}
                  {runMode !== 'dry_run' && !saveResult && (
                    <div className="agent-save-cta">
                      {!showSaveForm ? (
                        <div className="save-cta-prompt">
                          <p className="save-cta-text">Save this workflow?</p>
                          <button className="btn btn--primary" onClick={() => { setShowSaveForm(true); setWorkflowName(planTitle || DEMO_WORKFLOW_NAME) }}>
                            Save as "{planTitle || DEMO_WORKFLOW_NAME}"
                          </button>
                        </div>
                      ) : (
                        <div className="agent-save-form save-form-enhanced">
                          <div className="save-form-field">
                            <label>Workflow Name</label>
                            <input type="text" value={workflowName} onChange={(e) => setWorkflowName(e.target.value)} />
                          </div>
                          <div className="save-form-field">
                            <label>Description</label>
                            <input type="text" value={workflowDesc} onChange={(e) => setWorkflowDesc(e.target.value)} />
                          </div>
                          <button className="btn btn--primary" onClick={handleSaveWorkflow} disabled={saving || !workflowName.trim()}>
                            {saving ? 'Saving...' : 'Save Workflow'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  {saveResult && (
                    <div className="alert success" style={{ marginTop: 8 }}>
                      ✅ Saved as "{saveResult.workflow_name}"
                      {!saveResult.skill_name && (
                        <button className="btn btn--primary" style={{ marginLeft: 12 }} onClick={handleSaveSkill} disabled={saving}>
                          {saving ? 'Saving...' : '⚡ Save as Skill'}
                        </button>
                      )}
                      {saveResult.skill_name && (
                        <span style={{ marginLeft: 12 }}>⚡ Skill "{saveResult.skill_name}" created!</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {runStatus === 'stopped' && (
                <div className="alert error" style={{ marginTop: 8 }}>
                  <strong>Stopped.</strong> {completedSteps.length} steps done, {pendingSteps.length} cancelled.
                </div>
              )}
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {/* Recorded Workflow Preview */}
        {wfShowPreview && recorder.events && recorder.events.length > 0 && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <RecordedWorkflowPreview
                events={recorder.events}
                onDeleteEvent={(idx) => recorder.deleteEvent(recorder.session?.session_id, idx)}
                onConvertToSkill={handleWfConvertToSkill}
                loading={wfConvertLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {/* Skill Draft Review */}
        {wfShowDraft && recorder.draft && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <SkillDraftReview
                draft={recorder.draft}
                onSaveSkill={handleWfSaveSkill}
                onRejectDraft={handleWfRejectDraft}
                loading={wfSaveLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {/* ── Email Automation Cards (Phase 34) ── */}
        {emailStepState === 'needs_connection' && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <GmailConnectCard
                status="disconnected"
                onConnect={handleEmailConnectGmail}
                loading={emailLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {emailStepState === 'search_results' && emailMessages.length > 0 && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <EmailSearchPreviewCard
                messages={emailMessages}
                resultCount={emailMessages.length}
                query="has:attachment invoice OR receipt OR bill"
                selectedIds={emailSelectedIds}
                onSelectionChange={setEmailSelectedIds}
                onApproveDownload={handleEmailApproveDownload}
                loading={emailLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {(emailStepState === 'awaiting_folder' || emailStepState === 'needs_folder') && emailSelectedIds.length > 0 && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <AttachmentDownloadCard
                attachments={emailMessages
                  .filter(m => emailSelectedIds.includes(m.message_id))
                  .flatMap(m => m.attachments || [])}
                messageIds={emailSelectedIds}
                onDownload={handleEmailDownloadWithFolder}
                onCancel={handleEmailClear}
                loading={emailLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        {emailStepState === 'download_success' && emailDownloads.length > 0 && (
          <div className="agent-chat-msg agent-chat-msg--assistant">
            <div className="agent-chat-msg-avatar">A</div>
            <div className="agent-chat-msg-bubble">
              <EmailDownloadResultCard
                downloads={emailDownloads}
                outputFolder={emailDownloadFolder}
                onCreateExcelSummary={handleCreateExcelSummaryFromAttachment}
                onSaveAsSkill={handleSaveAsSkillFromBrowser}
                onOpenFolder={handleEmailOpenFolder}
                onClear={handleEmailClear}
                loading={emailLoading}
              />
            </div>
            <div className="agent-chat-msg-time" style={{ padding: '0 12px', textAlign: 'right' }}>{formatTime()}</div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Command Bar */}
      <div className="agent-chat-bar">
        <div className="agent-command-shell">
          <button
            className={`agent-command-btn agent-command-mic ${recording === 'recording' ? 'recording' : ''}`}
            onClick={toggleRecording}
            disabled={recording === 'transcribing' || planning || context?.kill_switch_active}
            title={recording === 'recording' ? 'Stop recording' : 'Voice command'}
          >
            {recording === 'idle' && '🎙️'}
            {recording === 'recording' && '⏺'}
            {recording === 'transcribing' && '⏳'}
            {recording === 'permission_denied' && '🔇'}
          </button>
          <div className="agent-command-input-wrap">
            {recording === 'recording' && (
              <div className="agent-recording-status">
                <span className="agent-recording-dot" />
                <span className="agent-recording-text">Listening…</span>
                <span className="agent-recording-timer">{formatRecordingTime(recordingTime)}</span>
                <button className="agent-recording-stop" onClick={stopRecording}>Stop</button>
              </div>
            )}
            {recording === 'transcribing' && (
              <div className="agent-recording-status">
                <span className="agent-recording-text">Transcribing…</span>
              </div>
            )}
            <input
              ref={commandInputRef}
              type="text"
              className={`agent-command-input ${recording !== 'idle' ? 'agent-command-input--hidden' : ''}`}
              placeholder="Tell OfficePilot what you want to automate..."
              value={command}
              onChange={(e) => { setCommand(e.target.value); setAutoStopMessage('') }}
              onKeyDown={(e) => { if (e.key === 'Enter') handlePlanTask() }}
              disabled={planning || recording !== 'idle' || context?.kill_switch_active}
            />
            {autoStopMessage && recording === 'idle' && (
              <div className="agent-auto-stop-msg">{autoStopMessage}</div>
            )}
          </div>
          <button className="agent-command-btn agent-command-send" onClick={handlePlanTask} disabled={!command.trim() || planning || recording !== 'idle' || context?.kill_switch_active}>
            {planning ? '...' : '→'}
          </button>
        </div>
        {recording === 'permission_denied' && (
          <div className="agent-mic-permission-warning">
            Microphone permission denied. You can still type your command.
          </div>
        )}
      </div>

      <style>{`
        .agent-chat-layout { display: flex; flex-direction: column; height: calc(100vh - var(--topbar-height, 52px) - 24px); }
        .agent-chat-messages { flex: 1; overflow-y: auto; padding: 16px 0; display: flex; flex-direction: column; gap: 8px; }
        .agent-chat-msg { display: flex; gap: 10px; padding: 0 16px; max-width: 800px; margin: 0 auto; width: 100%; }
        .agent-chat-msg--user { flex-direction: row-reverse; }
        .agent-chat-msg-avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; }
        .agent-chat-msg--user .agent-chat-msg-avatar { background: var(--primary, #2563eb); color: #fff; }
        .agent-chat-msg--assistant .agent-chat-msg-avatar { background: #10b981; color: #fff; }

        .agent-chat-msg-bubble { max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 0.9rem; line-height: 1.5; color: var(--text, #1e293b); box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .agent-chat-msg--user .agent-chat-msg-bubble { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; border-bottom-right-radius: 4px; }
        .agent-chat-msg--assistant .agent-chat-msg-bubble { background: var(--bg-card, #fff); border: 1px solid var(--border, #e2e8f0); border-bottom-left-radius: 4px; }
        .agent-chat-msg--error .agent-chat-msg-bubble { background: #fef2f2; border-color: #fecaca; color: #dc2626; }
        .agent-chat-msg-time { font-size: 10px; color: var(--text-muted, #94a3b8); margin-top: 4px; }
        .agent-chat-msg--plan { width: 100%; max-width: 100%; }

        .agent-chat-msg--assistant .agent-chat-msg--plan { border: none; background: transparent; padding: 0; }

        .agent-plan-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
        .agent-plan-title { font-weight: 600; font-size: 1rem; }
        .agent-plan-summary-text { margin: 4px 0; font-size: 0.9rem; }
        .agent-plan-platform { font-size: 0.82rem; color: var(--text-muted, #64748b); }
        .agent-plan-saveable { font-size: 0.82rem; color: #16a34a; }
        .agent-plan-steps { display: flex; flex-direction: column; gap: 6px; margin: 12px 0; }
        .agent-plan-step { display: flex; gap: 10px; align-items: flex-start; }
        .agent-plan-step-num { width: 24px; height: 24px; border-radius: 50%; background: var(--primary, #2563eb); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
        .agent-plan-step-body { flex: 1; }
        .agent-plan-step-header { display: flex; gap: 6px; align-items: center; margin-bottom: 2px; }
        .agent-plan-step-type { font-size: 11px; padding: 1px 8px; border-radius: 10px; font-weight: 600; text-transform: uppercase; }
        .agent-plan-step-type--low { background: #dbeafe; color: #1d4ed8; }
        .agent-plan-step-type--medium { background: #fef3c7; color: #b45309; }
        .agent-plan-step-type--high { background: #fee2e2; color: #dc2626; }
        .agent-plan-step-text { font-size: 0.85rem; color: var(--text-secondary, #475569); }
        .agent-plan-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }

        /* Welcome */
        .agent-welcome { text-align: center; padding: 40px 16px 24px; max-width: 720px; margin: 0 auto; }
        .agent-welcome-avatar { width: 52px; height: 52px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; margin: 0 auto 12px; box-shadow: 0 4px 12px rgba(16,185,129,0.25); }
        .agent-welcome-header h2 { margin: 0 0 6px; font-size: 1.35rem; font-weight: 600; }
        .agent-welcome-sub { margin: 0 0 24px; color: var(--text-muted, #64748b); font-size: 0.9rem; }

        .agent-section-title { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-muted, #94a3b8); text-align: left; margin-bottom: 10px; }

        .agent-automation-section { margin-bottom: 20px; }
        .agent-card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }

        .agent-automation-card { display: flex; flex-direction: column; align-items: flex-start; text-align: left; padding: 14px; border: 1px solid var(--border, #e2e8f0); border-radius: 10px; background: var(--bg-card, #fff); cursor: pointer; transition: all 0.2s; font-family: inherit; width: 100; }
        .agent-automation-card:hover { border-color: var(--primary, #2563eb); box-shadow: 0 2px 10px rgba(37,99,235,0.1); transform: translateY(-2px); }
        .agent-card-label { font-size: 0.88rem; font-weight: 600; color: var(--text, #1e293b); margin-bottom: 4px; }
        .agent-card-desc { font-size: 0.76rem; color: var(--text-muted, #64748b); line-height: 1.4; }

        .agent-more-section { margin-bottom: 4px; }
        .agent-more-row { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
        .agent-more-btn { padding: 6px 14px; border: 1px solid var(--border, #e2e8f0); border-radius: 8px; background: var(--bg-card, #fff); cursor: pointer; font-size: 0.8rem; color: var(--text-secondary, #475569); font-family: inherit; transition: all 0.15s; }
        .agent-more-btn:hover { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); background: #f0f4ff; }

        /* Thinking dots */
        .agent-thinking-dots { display: flex; gap: 2px; font-size: 1.5rem; line-height: 1; }
        .agent-thinking-dots span { animation: blink 1.4s infinite; }
        .agent-thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .agent-thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes blink { 0%, 80%, 100% { opacity: 0; } 40% { opacity: 1; } }

        /* === Command Bar — ChatGPT-style === */
        .agent-chat-bar { padding: 8px 16px 12px; border-top: 1px solid var(--border, #e2e8f0); background: var(--bg, #f8fafc); flex-shrink: 0; }
        .agent-command-shell { display: flex; align-items: center; gap: 4px; max-width: 800px; margin: 0 auto; background: #fff; border: 2px solid var(--border, #e2e8f0); border-radius: 24px; padding: 4px 6px; transition: border-color 0.2s, box-shadow 0.2s; }
        .agent-command-shell:focus-within { border-color: var(--primary, #2563eb); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
        .agent-command-input-wrap { flex: 1; display: flex; align-items: center; min-height: 40px; position: relative; }
        .agent-command-input { width: 100%; padding: 8px 10px; border: none; font-size: 0.95rem; background: transparent; outline: none; color: var(--text, #1e293b); }
        .agent-command-input--hidden { display: none; }
        .agent-auto-stop-msg { position: absolute; bottom: -18px; left: 10px; font-size: 0.75rem; color: #16a34a; font-weight: 500; white-space: nowrap; }
        .agent-command-btn { width: 36px; height: 36px; border: none; border-radius: 50%; background: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; transition: all 0.15s; flex-shrink: 0; }
        .agent-command-btn:hover { background: #f0f4ff; }
        .agent-command-btn:disabled { opacity: 0.4; cursor: default; }
        .agent-command-mic { font-size: 1rem; }
        .agent-command-mic.recording { background: #fee2e2; color: #dc2626; animation: agent-mic-pulse 1.2s ease-in-out infinite; }
        @keyframes agent-mic-pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.3); } 50% { box-shadow: 0 0 0 8px rgba(220,38,38,0); } }
        .agent-command-send { background: var(--primary, #2563eb); color: #fff; font-size: 1.1rem; font-weight: 700; }
        .agent-command-send:hover { background: var(--primary-hover, #1d4ed8); }
        .agent-command-send:disabled { background: #94a3b8; }

        /* Recording status inside command bar */
        .agent-recording-status { display: flex; align-items: center; gap: 6px; width: 100%; padding: 8px 10px; }
        .agent-recording-dot { width: 8px; height: 8px; border-radius: 50%; background: #dc2626; animation: agent-blink 0.6s infinite; flex-shrink: 0; }
        @keyframes agent-blink { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        .agent-recording-text { font-size: 0.9rem; color: var(--text-muted, #64748b); font-weight: 500; }
        .agent-recording-timer { font-size: 0.85rem; color: var(--text-muted, #94a3b8); font-family: var(--mono, monospace); }
        .agent-recording-stop { padding: 2px 10px; border: 1px solid #dc2626; border-radius: 12px; background: #fff; color: #dc2626; font-size: 0.75rem; cursor: pointer; font-weight: 600; margin-left: auto; }
        .agent-recording-stop:hover { background: #fee2e2; }

        /* Mic permission warning */
        .agent-mic-permission-warning { max-width: 800px; margin: 4px auto 0; padding: 6px 14px; background: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; font-size: 0.8rem; color: #92400e; text-align: center; }

        .agent-run-timeline { display: flex; flex-direction: column; gap: 6px; margin: 8px 0; }
        .agent-timeline-step { display: flex; gap: 8px; align-items: flex-start; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border, #e2e8f0); }
        .agent-run-header { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
        .agent-run-summary-detailed { background: #f0faf0; border: 1px solid #a5d6a7; border-radius: 8px; padding: 12px; margin-top: 8px; }
        .agent-voice-reply { background: #f0f4f8; border-radius: 8px; padding: 8px 12px; margin: 8px 0; display: flex; align-items: center; gap: 8px; font-size: 0.85rem; border-left: 3px solid var(--primary, #2563eb); }
        .matched-workflow-card { background: #e8f5e9; border-radius: 8px; padding: 10px; margin: 8px 0; border-left: 3px solid #2e7d32; font-size: 0.85rem; }
        .agent-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
        .save-cta-prompt { background: linear-gradient(135deg, #e3f2fd, #eff6ff); border: 1px solid #90caf9; border-radius: 8px; padding: 12px; text-align: center; margin-top: 8px; }
        .save-cta-text { margin: 0 0 8px; font-size: 0.9rem; font-weight: 600; }
        .agent-save-form { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
        .save-form-field { display: flex; flex-direction: column; gap: 4px; }
        .save-form-field label { font-size: 0.8rem; font-weight: 600; }
        .save-form-field input { padding: 6px 10px; border: 1px solid var(--border, #e2e8f0); border-radius: 6px; font-size: 0.85rem; }
        .summary-excel-path { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; padding: 6px; background: #fff; border-radius: 4px; font-size: 0.8rem; font-family: monospace; }
        .summary-ru { font-size: 0.95rem; font-weight: 600; color: #2e7d32; margin-bottom: 4px; }
        .summary-en { font-size: 0.85rem; color: #388e3c; }
      `}</style>
    </div>
  )
}
