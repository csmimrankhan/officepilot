import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth.jsx'
import AppShell from './components/layout/AppShell.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

function RequireAdmin({ children }) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'staff'
  if (!isAdmin) {
    return (
      <div className="error-state">
        <h3>Access Denied</h3>
        <p>You do not have permission to view this page. Admin or Owner role required.</p>
        <Link to="/app/agent" className="btn btn--primary">Go to Agent</Link>
      </div>
    )
  }
  return children
}

// Top-level admin route wrapper: auth check + admin check + AppShell
function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading-state"><div className="spinner" /><p>Checking session...</p></div>
  if (!user) return <Navigate to="/login" replace />
  const isAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'staff'
  if (!isAdmin) {
    return (
      <div className="error-state">
        <h3>Access Denied</h3>
        <p>You do not have permission to view this page. Admin or Owner role required.</p>
        <Link to="/app/agent" className="btn btn--primary">Go to Agent</Link>
      </div>
    )
  }
  return <AppShell>{children}</AppShell>
}

// Core pages
import UpdateBanner from './components/billing/UpdateBanner.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'

// Legacy imports (kept for redirects/routes)
import UploadInvoice from './pages/UploadInvoice.jsx'
import ReviewQueue from './pages/ReviewQueue.jsx'
import InvoiceDetail from './pages/InvoiceDetail.jsx'
import ApprovedInvoices from './pages/ApprovedInvoices.jsx'
import ExportExcel from './pages/ExportExcel.jsx'
import AuditLogs from './pages/AuditLogs.jsx'
import EmailIntegrations from './pages/EmailIntegrations.jsx'
import FolderSettings from './pages/FolderSettings.jsx'
import WorkflowRuns from './pages/WorkflowRuns.jsx'
import WorkflowRunDetail from './pages/WorkflowRunDetail.jsx'
import PendingApprovals from './pages/PendingApprovals.jsx'
import LocalAgent from './pages/LocalAgent.jsx'
import StorageSettings from './pages/StorageSettings.jsx'
import VersionHistory from './pages/VersionHistory.jsx'
import FileSnapshots from './pages/FileSnapshots.jsx'
import WorkflowVersions from './pages/WorkflowVersions.jsx'
import RestoreActivity from './pages/RestoreActivity.jsx'
import BrowserSettings from './pages/BrowserSettings.jsx'
import BrowserTestForm from './pages/BrowserTestForm.jsx'
import BrowserLogs from './pages/BrowserLogs.jsx'
import AccountingIntegrations from './pages/AccountingIntegrations.jsx'
import AccountingMappings from './pages/AccountingMappings.jsx'
import AccountingSyncLogs from './pages/AccountingSyncLogs.jsx'
import RecordingSettings from './pages/RecordingSettings.jsx'
import RecordedWorkflowsList from './pages/RecordedWorkflowsList.jsx'
import ScreenSettings from './pages/ScreenSettings.jsx'
import ScreenAssistant from './pages/ScreenAssistant.jsx'
import ScreenLogs from './pages/ScreenLogs.jsx'
import SafetyPolicyCenter from './pages/SafetyPolicyCenter.jsx'
import PermissionsManager from './pages/PermissionsManager.jsx'
import AuditExport from './pages/AuditExport.jsx'
import ProductionReadiness from './pages/ProductionReadiness.jsx'
import EmergencySafety from './pages/EmergencySafety.jsx'
import DemoMode from './pages/DemoMode.jsx'
import About from './pages/About.jsx'
import FeedbackInbox from './pages/FeedbackInbox.jsx'
import BugReports from './pages/BugReports.jsx'
import PilotUsageReview from './pages/PilotUsageReview.jsx'
import PilotReadinessPage from './pages/PilotReadiness.jsx'
import Landing from './pages/Landing.jsx'
import Waitlist from './pages/Waitlist.jsx'
import DemoScript from './pages/DemoScript.jsx'
import ProductPositioning from './pages/ProductPositioning.jsx'
import FAQPage from './pages/FAQPage.jsx'
import MarketingAssets from './pages/MarketingAssets.jsx'
import AdminWaitlist from './pages/AdminWaitlist.jsx'
import VoiceCommandCenter from './pages/VoiceCommandCenter.jsx'
import VoiceIntents from './pages/VoiceIntents.jsx'
import PrivacyDashboard from './pages/PrivacyDashboard.jsx'
import ImportedEmails from './pages/ImportedEmails.jsx'
import ImportedEmailDetail from './pages/ImportedEmailDetail.jsx'
import ApiSetup from './pages/ApiSetup.jsx'
import VoiceLayerSettings from './pages/VoiceLayerSettings.jsx'
import DictationHistory from './pages/DictationHistory.jsx'
import OnboardingWizard from './pages/OnboardingWizard.jsx'
import AccountingSkills from './pages/AccountingSkills.jsx'
import VerifyEmail from './pages/VerifyEmail.jsx'
import ForgotPassword from './pages/ForgotPassword.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import AdminUsers from './pages/AdminUsers.jsx'
import AdminUserDetail from './pages/AdminUserDetail.jsx'
import GoogleCallback from './pages/GoogleCallback.jsx'
import AdminAuditLogs from './pages/AdminAuditLogs.jsx'
import AdminSystemHealth from './pages/AdminSystemHealth.jsx'
import AdminAIStatus from './pages/AdminAIStatus.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'
import BillingPage from './pages/BillingPage.jsx'
import RouteDiagnostics from './pages/RouteDiagnostics.jsx'

const AccountantAgent = lazy(() => import('./pages/AccountantAgent.jsx'))
const VoiceRecorder = lazy(() => import('./pages/VoiceRecorder.jsx'))
const ReleaseReadiness = lazy(() => import('./pages/ReleaseReadiness.jsx'))
const StartupMetrics = lazy(() => import('./pages/StartupMetrics.jsx'))
const CleanupPage = lazy(() => import('./pages/CleanupPage.jsx'))

function NotFound() {
  return (
    <div className="error-state">
      <h3>Page not found</h3>
      <p>This page is not registered: <code>{window.location.pathname}</code></p>
      <Link to="/app/agent" className="btn btn--primary">Go to Agent</Link>
    </div>
  )
}

function AuthenticatedRoutes() {
  const { user, loading } = useAuth()

  const agentFirst = true // APP_EXPERIENCE_MODE == agent_first

  if (loading) return <div className="loading-state"><div className="spinner" /><p>Checking session...</p></div>
  if (!user) return <Navigate to="/login" replace />

  const isOnboardingPath = window.location.pathname === '/app/onboarding'

  if (!user.onboarding_completed && !isOnboardingPath) {
    return (
      <AppShell>
        <ErrorBoundary>
          <Navigate to="/app/onboarding" replace />
        </ErrorBoundary>
      </AppShell>
    )
  }

  // New clean routes
  const routes = [
    // === Onboarding Wizard ===
    { path: '/app/onboarding', element: <OnboardingWizard /> },

    // === Core Accountant AutoPilot (Agent-first) ===
    { path: '/app/agent', element: <AccountantAgent /> },
    { path: '/app/billing', element: <BillingPage /> },
    { path: '/app/dashboard', element: agentFirst ? <Navigate to="/app/agent" replace /> : <Dashboard /> },
    { path: '/app/workflow-memory', element: <WorkflowRuns /> },
    { path: '/app/workflow-memory/skills', element: <AccountingSkills /> },
    { path: '/app/excel-agent', element: <ExportExcel /> },
    { path: '/app/accounting-agent', element: <AccountingIntegrations /> },
    { path: '/app/invoice-workflow', element: <ReviewQueue /> },
    { path: '/app/browser-desktop', element: <ScreenAssistant /> },
    { path: '/app/browser-desktop/browser', element: <BrowserTestForm /> },
    { path: '/app/browser-desktop/screen', element: <ScreenAssistant /> },
    { path: '/app/browser-desktop/recording', element: <RecordedWorkflowsList /> },
    { path: '/app/voice-recorder', element: <VoiceRecorder /> },
    { path: '/app/browser-desktop/logs', element: <BrowserLogs /> },

    // Safety & Audit
    { path: '/app/audit-restore', element: <AuditLogs /> },
    { path: '/app/audit-restore/versions', element: <VersionHistory /> },
    { path: '/app/audit-restore/snapshots', element: <FileSnapshots /> },
    { path: '/app/audit-restore/restore', element: <RestoreActivity /> },
    { path: '/app/safety-center', element: <SafetyPolicyCenter /> },
    { path: '/app/safety-center/emergency', element: <EmergencySafety /> },
    { path: '/app/safety-center/readiness', element: <ProductionReadiness /> },
    { path: '/app/safety-center/permissions', element: <PermissionsManager /> },
    { path: '/app/safety-center/backup', element: <Navigate to="/app/safety-center/readiness" replace /> },

    // Admin
    { path: '/app/admin', element: <Navigate to="/app/settings" replace /> },
    { path: '/app/advanced', element: <Navigate to="/app/settings" replace /> },

    // Settings
    { path: '/app/settings', element: <LocalAgent /> },
    { path: '/app/settings/integrations', element: <EmailIntegrations /> },
    { path: '/app/settings/folder', element: <FolderSettings /> },
    { path: '/app/settings/storage', element: <StorageSettings /> },
    { path: '/app/settings/browser', element: <BrowserSettings /> },
    { path: '/app/settings/screen', element: <ScreenSettings /> },
    { path: '/app/settings/recording', element: <RecordingSettings /> },
    { path: '/app/settings/api-setup', element: <ApiSetup /> },
    { path: '/app/settings/voice-layer', element: <VoiceLayerSettings /> },

    // Advanced app routes
    { path: '/app/browser', element: <BrowserSettings /> },
    { path: '/app/screen-control', element: <ScreenAssistant /> },
    { path: '/app/local-agent', element: <LocalAgent /> },
    { path: '/app/storage', element: <StorageSettings /> },
    { path: '/app/safety', element: <SafetyPolicyCenter /> },
    { path: '/app/skills', element: <AccountingSkills /> },
    { path: '/app/version-history', element: <VersionHistory /> },
    { path: '/app/api-setup', element: <ApiSetup /> },
    { path: '/app/route-diagnostics', element: <RouteDiagnostics /> },

    // Legacy route redirects (new -> old)
    { path: '/upload', element: <UploadInvoice /> },
    { path: '/review', element: <ReviewQueue /> },
    { path: '/invoices/:id', element: <InvoiceDetail /> },
    { path: '/approved', element: <ApprovedInvoices /> },
    { path: '/export', element: <ExportExcel /> },
    { path: '/integrations', element: <EmailIntegrations /> },
    { path: '/imported-emails', element: <ImportedEmails /> },
    { path: '/imported-emails/:id', element: <ImportedEmailDetail /> },
    { path: '/workflows', element: <WorkflowRuns /> },
    { path: '/workflows/approvals', element: <PendingApprovals /> },
    { path: '/workflows/:id', element: <WorkflowRunDetail /> },
    { path: '/audit', element: <AuditLogs /> },
    { path: '/settings/folder', element: <FolderSettings /> },
    { path: '/local', element: <LocalAgent /> },
    { path: '/local/storage', element: <StorageSettings /> },
    { path: '/local/privacy', element: <PrivacyDashboard /> },
    { path: '/versions', element: <VersionHistory /> },
    { path: '/versions/:entityType/:entityId', element: <VersionHistory /> },
    { path: '/snapshots', element: <FileSnapshots /> },
    { path: '/workflow-versions', element: <WorkflowVersions /> },
    { path: '/workflow-versions/:id', element: <WorkflowVersions /> },
    { path: '/restore-activity', element: <RestoreActivity /> },
    { path: '/browser/settings', element: <BrowserSettings /> },
    { path: '/browser/test-form', element: <BrowserTestForm /> },
    { path: '/browser/logs', element: <BrowserLogs /> },
    { path: '/accounting', element: <AccountingIntegrations /> },
    { path: '/accounting/mappings', element: <AccountingMappings /> },
    { path: '/accounting/sync-logs', element: <AccountingSyncLogs /> },
    { path: '/recording/settings', element: <RecordingSettings /> },
    { path: '/recording/workflows', element: <RecordedWorkflowsList /> },
    { path: '/api-setup', element: <ApiSetup /> },
    { path: '/screen/settings', element: <ScreenSettings /> },
    { path: '/screen/assistant', element: <ScreenAssistant /> },
    { path: '/screen/logs', element: <ScreenLogs /> },
    { path: '/safety', element: <SafetyPolicyCenter /> },
    { path: '/safety/emergency', element: <EmergencySafety /> },
    { path: '/permissions', element: <PermissionsManager /> },
    { path: '/audit/export', element: <AuditExport /> },
    { path: '/system/readiness', element: <ProductionReadiness /> },
    { path: '/backup', element: <Navigate to="/system/readiness" replace /> },
    { path: '/voices', element: <VoiceIntents /> },
    { path: '/demo', element: <DemoMode /> },
    { path: '/about', element: <About /> },
    { path: '/voice', element: <VoiceCommandCenter /> },
    { path: '/voice-layer/settings', element: <VoiceLayerSettings /> },
    { path: '/dictation-history', element: <DictationHistory /> },
    { path: '/release/readiness', element: <ReleaseReadiness /> },
    { path: '/system/startup-metrics', element: <StartupMetrics /> },
    { path: '/pilot/feedback', element: <FeedbackInbox /> },
    { path: '/pilot/bug-reports', element: <BugReports /> },
    { path: '/pilot/usage', element: <PilotUsageReview /> },
    { path: '/pilot/readiness', element: <PilotReadinessPage /> },

    // Admin routes — always present but gated by RequireAdmin
    { path: '/admin', element: <RequireAdmin><AdminDashboard /></RequireAdmin> },
    { path: '/admin/dashboard', element: <RequireAdmin><AdminDashboard /></RequireAdmin> },
    { path: '/admin/users', element: <RequireAdmin><AdminUsers /></RequireAdmin> },
    { path: '/admin/users/:id', element: <RequireAdmin><AdminUserDetail /></RequireAdmin> },
    { path: '/admin/audit-logs', element: <RequireAdmin><AdminAuditLogs /></RequireAdmin> },
    { path: '/admin/waitlist', element: <RequireAdmin><AdminWaitlist /></RequireAdmin> },
    { path: '/admin/system-health', element: <RequireAdmin><AdminSystemHealth /></RequireAdmin> },
    { path: '/admin/ai-status', element: <RequireAdmin><AdminAIStatus /></RequireAdmin> },
    { path: '/system/cleanup', element: <RequireAdmin><CleanupPage /></RequireAdmin> },

    // Admin compatibility aliases
    { path: '/app/admin/system-health', element: <Navigate to="/admin/system-health" replace /> },
    { path: '/app/admin/ai-status', element: <Navigate to="/admin/ai-status" replace /> },
    { path: '/admin/health', element: <Navigate to="/admin/system-health" replace /> },
    { path: '/admin/ai', element: <Navigate to="/admin/ai-status" replace /> },

    { path: '/', element: <Navigate to="/app/agent" replace /> },
  ]

  return (
      <AppShell>
        <ErrorBoundary>
          <Suspense fallback={<div className="loading-state"><div className="spinner" /><p>Loading page...</p></div>}>
            <Routes>
              {routes.map(r => <Route key={r.path} {...r} />)}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </AppShell>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <UpdateBanner />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/auth/google/callback" element={<GoogleCallback />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/landing" element={<Landing />} />
        <Route path="/waitlist" element={<Waitlist />} />
        <Route path="/demo-script" element={<DemoScript />} />
        <Route path="/positioning" element={<ProductPositioning />} />
        <Route path="/faq" element={<FAQPage />} />
        <Route path="/marketing-assets" element={<MarketingAssets />} />
        <Route path="/welcome" element={<Landing />} />

        {/* Top-level admin routes — match before /* catch-all */}
        <Route path="/admin/system-health" element={<AdminRoute><AdminSystemHealth /></AdminRoute>} />
        <Route path="/admin/ai-status" element={<AdminRoute><AdminAIStatus /></AdminRoute>} />
        <Route path="/admin/health" element={<Navigate to="/admin/system-health" replace />} />
        <Route path="/admin/ai" element={<Navigate to="/admin/ai-status" replace />} />
        <Route path="/app/admin/system-health" element={<Navigate to="/admin/system-health" replace />} />
        <Route path="/app/admin/ai-status" element={<Navigate to="/admin/ai-status" replace />} />

        <Route path="/*" element={<AuthenticatedRoutes />} />
      </Routes>
    </AuthProvider>
  )
}
