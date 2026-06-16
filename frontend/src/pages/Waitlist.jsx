import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from '../api.js'

const ROLES = ['Accountant', 'Bookkeeper', 'Admin Assistant', 'SME Owner', 'BPO/Outsourcing', 'Other']
const VOLUMES = ['<50/mo', '50-200/mo', '200-1000/mo', '1000+/mo']

export default function Waitlist() {
  const navigate = useNavigate()
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    name: '', email: '', company: '', role: '', invoice_volume: '',
    current_workflow: '', interested_features: '', country: '', notes: '',
  })

  function set(field) {
    return function (e) {
      setForm(o => ({ ...o, [field]: e.target.value }))
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.submitWaitlist(form)
      setSubmitted(true)
    } catch (err) {
      setError(err.message || 'Failed to submit. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="card" style={{ maxWidth: '560px', margin: '60px auto', textAlign: 'center' }}>
        <style>{`
          .waitlist-success-icon {
            font-size: 48px;
            margin-bottom: 12px;
          }
        `}</style>
        <div className="waitlist-success-icon">&#10003;</div>
        <h2>You're on the list!</h2>
        <p style={{ color: '#666', marginTop: '8px', lineHeight: '1.6' }}>
          Thanks for joining the OfficePilot AI early pilot program.<br />
          We'll be in touch at <strong>{form.email}</strong> with next steps.
        </p>
        <button className="btn" style={{ marginTop: '20px' }} onClick={() => navigate('/')}>
          Back to Home
        </button>
      </div>
    )
  }

  return (
    <div className="card" style={{ maxWidth: '640px', margin: '40px auto' }}>
      <style>{`
        .waitlist-field { margin-bottom: 16px; }
        .waitlist-field label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 0.9rem; }
        .waitlist-field .required::after { content: ' *'; color: #d32f2f; }
        .waitlist-field input,
        .waitlist-field select,
        .waitlist-field textarea {
          width: 100%; padding: 10px 12px; border: 1px solid #ccc;
          border-radius: 6px; font-size: 0.95rem; box-sizing: border-box;
          font-family: inherit; transition: border-color 0.2s;
        }
        .waitlist-field input:focus,
        .waitlist-field select:focus,
        .waitlist-field textarea:focus {
          outline: none; border-color: #1976d2; box-shadow: 0 0 0 2px rgba(25,118,210,0.15);
        }
        .waitlist-field textarea { min-height: 80px; resize: vertical; }
        .waitlist-row { display: flex; gap: 16px; }
        .waitlist-row .waitlist-field { flex: 1; }
        .waitlist-error {
          background: #ffebee; color: #c62828; padding: 10px 14px;
          border-radius: 6px; margin-bottom: 16px; font-size: 0.9rem;
        }
        @media (max-width: 540px) {
          .waitlist-row { flex-direction: column; gap: 0; }
        }
      `}</style>

      <h2 style={{ marginBottom: '4px' }}>Join the Early Pilot Program</h2>
      <p style={{ color: '#666', marginBottom: '20px', fontSize: '0.95rem' }}>
        Be among the first to experience AI-powered invoice automation. Free during pilot — no credit card needed.
      </p>

      {error && <div className="waitlist-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="waitlist-row">
          <div className="waitlist-field">
            <label className="required">Name</label>
            <input type="text" value={form.name} onChange={set('name')} required placeholder="Your full name" />
          </div>
          <div className="waitlist-field">
            <label className="required">Email</label>
            <input type="email" value={form.email} onChange={set('email')} required placeholder="you@company.com" />
          </div>
        </div>

        <div className="waitlist-row">
          <div className="waitlist-field">
            <label>Company</label>
            <input type="text" value={form.company} onChange={set('company')} placeholder="Company name" />
          </div>
          <div className="waitlist-field">
            <label>Role</label>
            <select value={form.role} onChange={set('role')}>
              <option value="">Select a role</option>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>

        <div className="waitlist-field">
          <label>Monthly Invoice Volume</label>
          <select value={form.invoice_volume} onChange={set('invoice_volume')}>
            <option value="">Select volume</option>
            {VOLUMES.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        <div className="waitlist-field">
          <label>Current Workflow</label>
          <textarea value={form.current_workflow} onChange={set('current_workflow')} placeholder="How do you currently handle invoices?" />
        </div>

        <div className="waitlist-field">
          <label>Interested Features</label>
          <textarea value={form.interested_features} onChange={set('interested_features')} placeholder="Which features interest you most?" />
        </div>

        <div className="waitlist-row">
          <div className="waitlist-field">
            <label>Country</label>
            <input type="text" value={form.country} onChange={set('country')} placeholder="e.g. Philippines" />
          </div>
          <div className="waitlist-field">
            <label>Notes</label>
            <textarea value={form.notes} onChange={set('notes')} placeholder="Anything else?" style={{ minHeight: '42px' }} />
          </div>
        </div>

        <button className="btn" type="submit" disabled={loading} style={{ width: '100%', marginTop: '8px' }}>
          {loading ? 'Submitting...' : 'Join the Early Pilot Program'}
        </button>
      </form>
    </div>
  )
}
