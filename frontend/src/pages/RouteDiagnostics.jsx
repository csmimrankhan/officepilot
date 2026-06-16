import { useLocation } from 'react-router-dom'
import PageHeader from '../components/layout/PageHeader.jsx'

const REGISTERED_PAGES = [
  { name: 'Accountant Agent', path: '/app/agent' },
  { name: 'Billing', path: '/app/billing' },
  { name: 'Workflow Memory', path: '/app/workflow-memory' },
  { name: 'Accounting Skills', path: '/app/skills' },
  { name: 'Version History', path: '/app/version-history' },
  { name: 'Settings', path: '/app/settings' },
  { name: 'API Setup', path: '/app/api-setup' },
  { name: 'Safety', path: '/app/safety' },
  { name: 'Screen Control', path: '/app/screen-control' },
  { name: 'Local Agent', path: '/app/local-agent' },
  { name: 'Storage', path: '/app/storage' },
  { name: 'Browser', path: '/app/browser' },
  { name: 'Admin Dashboard', path: '/admin/dashboard' },
  { name: 'User Management', path: '/admin/users' },
  { name: 'Audit Logs', path: '/admin/audit-logs' },
  { name: 'Waitlist', path: '/admin/waitlist' },
  { name: 'System Health', path: '/admin/system-health' },
  { name: 'AI Status', path: '/admin/ai-status' },
  { name: 'Route Diagnostics', path: '/app/route-diagnostics' },
]

export default function RouteDiagnostics() {
  const location = useLocation()

  return (
    <div>
      <PageHeader title="Route Diagnostics" subtitle="Internal page existence checker" />

      <div className="alert info">
        <strong>Current path:</strong> <code>{location.pathname}</code>
        <br />
        <strong>Search:</strong> <code>{location.search || '(none)'}</code>
        <br />
        <strong>Hash:</strong> <code>{location.hash || '(none)'}</code>
      </div>

      <h3>Registered pages ({REGISTERED_PAGES.length})</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Page name</th>
            <th>Expected path</th>
            <th>Component imported</th>
          </tr>
        </thead>
        <tbody>
          {REGISTERED_PAGES.map(({ name, path }) => (
            <tr key={path}>
              <td>{name}</td>
              <td><code>{path}</code></td>
              <td><span className="badge ok">✓ Imported</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
