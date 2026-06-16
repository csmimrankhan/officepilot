import { useState } from 'react'
import * as api from '../api.js'

const FAQ_DATA = [
  {
    q: 'What is OfficePilot AI?',
    a: 'OfficePilot AI is a safe, local-first AI office worker that helps you process invoices, export to Excel, sync with QuickBooks or Xero, and maintain a complete audit trail — all with human approval at every step.'
  },
  {
    q: 'How does invoice parsing work?',
    a: 'When you upload an invoice or import it from email, OfficePilot AI extracts fields like vendor, amount, date, and line items. You can choose between the built-in parser, Tesseract OCR, or PaddleOCR for maximum accuracy.'
  },
  {
    q: 'Is my data stored locally?',
    a: 'Yes. All data stays on your machine. OfficePilot AI uses a local SQLite database and never sends your invoice data to external servers. You control where files are stored and can export or back up at any time.'
  },
  {
    q: 'Do I need an internet connection?',
    a: 'OfficePilot AI works fully offline for core invoice processing. An internet connection is only required if you want to sync with QuickBooks/Xero, use Gmail integration, or automate browser-based workflows.'
  },
  {
    q: 'How does the approval workflow work?',
    a: 'Every invoice goes through a review queue where you can inspect the parsed data. You approve, reject, or mark duplicates before data is exported or synced. Nothing leaves the review stage without your explicit approval.'
  },
  {
    q: 'Can I export to QuickBooks or Xero?',
    a: 'Yes. OfficePilot AI supports QuickBooks and Xero accounting sync. You map your invoice fields once, preview the sync, approve the data, and it is pushed to your accounting provider with a full audit log.'
  },
  {
    q: 'What is the Voice Recorder?',
    a: 'The Voice Recorder lets you record any workflow by voice. Start recording, perform your steps, stop recording — OfficePilot captures every click, type, and navigation. It converts your recording into a reusable skill with AI-generated name and trigger phrases. Replay the skill anytime with approval checkpoints.'
  },
  {
    q: 'What happens if a parser makes a mistake?',
    a: 'Every extraction is flagged with a confidence score. Low-confidence fields are highlighted in the review queue for your attention. You can correct any field before approval, and all corrections are recorded in the audit log.'
  },
  {
    q: 'How do I restore a previous version?',
    a: 'OfficePilot AI keeps version history for invoices, settings, and workflows. You can browse the change timeline, compare versions side by side, and restore any previous version with a single click and a mandatory reason.'
  },
  {
    q: 'Can I automate browser tasks?',
    a: 'Yes, with safety guardrails. OfficePilot AI can fill forms and navigate approved domains. All browser actions require preview and approval. Sensitive fields like passwords are redacted and skipped. Banking and payment sites are blocked by default.'
  },
  {
    q: 'Is there a demo mode?',
    a: 'Yes. Enable demo mode from the settings page to explore all features with sample data. Demo data is clearly marked and can be reset at any time without affecting your real invoices.'
  },
  {
    q: 'How do I get support?',
    a: 'OfficePilot AI includes a built-in feedback system and bug report tool that packages diagnostics safely. You can also submit a bug report from within the app — logs and screenshots are included only if you opt in.'
  }
]

const BADGES = [
  { title: 'Local-First', desc: 'All data stays on your machine. No cloud dependency.' },
  { title: 'Approval Gates', desc: 'Every action requires human approval before execution.' },
  { title: 'Audit Logs', desc: 'Every change is recorded with actor, timestamp, and diff.' },
  { title: 'Restore', desc: 'Version history lets you undo changes with a reason.' },
  { title: 'Open Source', desc: 'The source code is available for review and contribution.' }
]

export default function Landing() {
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', company: '', role: '' })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  function handleFormChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleFormSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.submitWaitlist(form)
      setSubmitted(true)
    } catch (err) {
      setError(err.message || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="landing">
      <style>{`
        .landing {
          font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
          color: #1c2330;
          line-height: 1.6;
        }
        .landing * { box-sizing: border-box; }
        .landing a { color: #1f4e78; text-decoration: none; }
        .landing a:hover { text-decoration: underline; }
        .landing h2 { font-size: 1rem; margin: 0; }
        .landing-section { padding: 48px 24px; max-width: 960px; margin: 0 auto; }
        .landing-section h3 { font-size: 1.5rem; margin: 0 0 24px; text-align: center; color: #1c2330; }
        .landing-hero {
          text-align: center;
          padding: 64px 24px 48px;
          background: linear-gradient(135deg, #1f4e78 0%, #163a5a 100%);
          color: #fff;
        }
        .landing-hero h1 { font-size: 2.2rem; margin: 0 0 12px; font-weight: 700; }
        .landing-hero p { font-size: 1.05rem; opacity: 0.9; max-width: 640px; margin: 0 auto 24px; }
        .landing-hero .btn-group { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
        .landing-hero .btn {
          display: inline-block; padding: 10px 24px; border-radius: 6px;
          font-weight: 600; cursor: pointer; border: none; font-size: 0.95rem;
        }
        .landing-hero .btn-primary { background: #fff; color: #1f4e78; }
        .landing-hero .btn-primary:hover { background: #e8f0f8; }
        .landing-hero .btn-outline { background: transparent; color: #fff; border: 2px solid rgba(255,255,255,0.5); }
        .landing-hero .btn-outline:hover { border-color: #fff; }
        .problem-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .problem-card {
          background: #fff; border: 1px solid #d8dee6; border-radius: 8px;
          padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .problem-card h4 { margin: 0 0 8px; font-size: 1.1rem; color: #1f4e78; }
        .problem-card p { margin: 0; font-size: 0.9rem; color: #5b6472; }
        .steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .step {
          text-align: center; padding: 20px 12px;
          background: #f9fbfd; border-radius: 8px; border: 1px solid #d8dee6;
        }
        .step .num {
          display: flex; align-items: center; justify-content: center;
          width: 40px; height: 40px; border-radius: 50%;
          background: #1f4e78; color: #fff; font-weight: 700;
          margin: 0 auto 12px; font-size: 1.1rem;
        }
        .step h4 { margin: 0 0 6px; font-size: 1rem; }
        .step p { margin: 0; font-size: 0.85rem; color: #5b6472; }
        .demo-box {
          background: #e8f0f8; border: 1px solid #b6c8e2; border-radius: 8px;
          padding: 24px; text-align: center;
        }
        .demo-box p { margin: 0 0 16px; color: #1c2330; }
        .badge-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }
        .badge-card {
          text-align: center; padding: 20px 12px;
          background: #fff; border: 1px solid #d8dee6; border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .badge-card .icon {
          font-size: 1.8rem; margin-bottom: 8px;
          display: flex; align-items: center; justify-content: center;
        }
        .badge-card h4 { margin: 0 0 4px; font-size: 0.95rem; color: #1c2330; }
        .badge-card p { margin: 0; font-size: 0.8rem; color: #5b6472; }
        .faq-list details {
          background: #f9fbfd; border: 1px solid #d8dee6;
          border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;
        }
        .faq-list details summary {
          cursor: pointer; font-weight: 600; color: #1c2330;
          display: flex; align-items: center; gap: 8px;
        }
        .faq-list details summary::before { content: '▸'; color: #1f4e78; font-size: 0.9rem; }
        .faq-list details[open] summary::before { content: '▾'; }
        .faq-list details p { margin: 8px 0 0; font-size: 0.9rem; color: #5b6472; }
        .landing-footer {
          text-align: center; padding: 24px; border-top: 1px solid #d8dee6;
          background: #f4f6f9; font-size: 0.85rem; color: #5b6472;
        }
        .landing-footer nav { display: flex; gap: 16px; justify-content: center; margin-bottom: 8px; }
        .waitlist-form { max-width: 480px; margin: 0 auto; }
        .waitlist-form .field { margin-bottom: 14px; }
        .waitlist-form label { display: block; font-size: 0.85rem; color: #5b6472; margin-bottom: 4px; }
        .waitlist-form input {
          width: 100%; padding: 10px 12px; border: 1px solid #d8dee6;
          border-radius: 6px; font: inherit; color: #1c2330;
        }
        .waitlist-form input:focus { outline: 2px solid #1f4e78; outline-offset: -1px; }
        .waitlist-form .btn-submit {
          width: 100%; padding: 10px; border: none; border-radius: 6px;
          background: #1f4e78; color: #fff; font-weight: 600; cursor: pointer; font-size: 1rem;
        }
        .waitlist-form .btn-submit:hover { background: #163a5a; }
        .waitlist-form .btn-submit:disabled { opacity: 0.55; cursor: not-allowed; }
        .waitlist-form .error { color: #b13a3a; font-size: 0.85rem; margin-top: 8px; }
        .waitlist-form .thanks {
          text-align: center; padding: 20px; background: #e0f2e9;
          border: 1px solid #aedcc4; border-radius: 8px; color: #1f7a4d;
        }
        .waitlist-form .thanks h4 { margin: 0 0 4px; }
        .waitlist-form .thanks p { margin: 0; font-size: 0.9rem; }
        .landing .bg-alt { background: #f4f6f9; }

        @media (max-width: 768px) {
          .landing-hero h1 { font-size: 1.6rem; }
          .landing-hero p { font-size: 0.95rem; }
          .landing-section { padding: 32px 16px; }
          .problem-grid { grid-template-columns: 1fr; }
          .steps { grid-template-columns: 1fr 1fr; }
          .badge-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 480px) {
          .steps { grid-template-columns: 1fr; }
          .badge-grid { grid-template-columns: 1fr; }
        }
      `}</style>

      <section className="landing-hero">
        <h1>OfficePilot AI — Universal Voice Accountant Agent</h1>
        <p>Use your voice to automate accounting work across Excel, browser apps, and any accounting platform — safely. Works with QuickBooks, Xero, Zoho Books, Odoo, FreshBooks, Wave, Sage, and any ERP you already use.</p>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>Join the Early Pilot Program</button>
          <a className="btn btn-outline" href="https://github.com/anomalyco/officepilot" target="_blank" rel="noopener noreferrer">View on GitHub</a>
        </div>
      </section>

      <section className="landing-section">
        <h3>The Problem</h3>
        <div className="problem-grid">
          <div className="problem-card">
            <h4>Manual Data Entry</h4>
            <p>Hours wasted typing invoice data by hand. Prone to typos, lost files, and inconsistent formats across vendors.</p>
          </div>
          <div className="problem-card">
            <h4>Email Chaos</h4>
            <p>Invoices buried in inbox clutter. No automatic capture, no structured data extraction, no way to track what arrived.</p>
          </div>
          <div className="problem-card">
            <h4>No Audit Trail</h4>
            <p>No record of who approved what or when. Mistakes are hard to trace, and restoring a previous state is impossible without backups.</p>
          </div>
          <div className="problem-card">
            <h4>Repetitive Workflows</h4>
            <p>Same steps every day: download invoices, open Excel, create summaries. OfficePilot records your workflow once and replays it with voice approval.</p>
          </div>
        </div>
      </section>

      <section className="landing-section bg-alt">
        <h3>How It Works</h3>
        <div className="steps">
          <div className="step">
            <div className="num">1</div>
            <h4>Tell OfficePilot What to Do</h4>
            <p>Use voice or text to describe your task: "Create a vendor payment report", "Update my Excel sheet", "Copy this balance into my spreadsheet".</p>
          </div>
          <div className="step">
            <div className="num">2</div>
            <h4>Review the Plan</h4>
            <p>OfficePilot builds a step-by-step plan. You preview every action before any click, type, or data change happens.</p>
          </div>
          <div className="step">
            <div className="num">3</div>
            <h4>Approve &amp; Execute</h4>
            <p>Approve the plan by voice or click. Each step is executed safely with your permission. Nothing happens silently.</p>
          </div>
          <div className="step">
            <div className="num">4</div>
            <h4>Record &amp; Replay</h4>
            <p>Record your workflow with voice — OfficePilot captures every click and input. Name it with AI and replay anytime.</p>
          </div>
          <div className="step">
            <div className="num">5</div>
            <h4>Sync with QuickBooks</h4>
            <p>Read-only sync shows accounts, customers, and invoices before approval. Sandbox mode for worry-free testing.</p>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <h3>Demo Workflow</h3>
        <div className="demo-box">
          <p>Try the full invoice processing pipeline with sample data in Demo Mode. Upload a mock invoice, review the extraction, approve it, export to Excel, and view the audit trail — all without touching real data. Enable demo mode from the settings page to get started.</p>
          <div className="btn-group">
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>Try the Demo</button>
          </div>
        </div>
      </section>

      <section className="landing-section bg-alt">
        <h3>Safety &amp; Trust</h3>
        <div className="badge-grid">
          {BADGES.map(b => (
            <div className="badge-card" key={b.title}>
              <div className="icon">{
                b.title === 'Local-First' ? '\u{1F4E1}' :
                b.title === 'Approval Gates' ? '\u{2705}' :
                b.title === 'Audit Logs' ? '\u{1F4CB}' :
                b.title === 'Restore' ? '\u{1F504}' : '\u{1F4F1}'
              }</div>
              <h4>{b.title}</h4>
              <p>{b.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <h3>Frequently Asked Questions</h3>
        <div className="faq-list">
          {FAQ_DATA.map((item, i) => (
            <details key={i}>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-section bg-alt">
        <h3>Join the Early Pilot Program</h3>
        {submitted ? (
          <div className="waitlist-form">
            <div className="thanks">
              <h4>Thank You!</h4>
              <p>You have been added to the waitlist. We will notify you when early access is ready.</p>
            </div>
          </div>
        ) : (
          <form className="waitlist-form" onSubmit={handleFormSubmit}>
            <div className="field">
              <label>Name</label>
              <input name="name" value={form.name} onChange={handleFormChange} required />
            </div>
            <div className="field">
              <label>Email</label>
              <input type="email" name="email" value={form.email} onChange={handleFormChange} required />
            </div>
            <div className="field">
              <label>Company</label>
              <input name="company" value={form.company} onChange={handleFormChange} />
            </div>
            <div className="field">
              <label>Role</label>
              <input name="role" value={form.role} onChange={handleFormChange} />
            </div>
            {error && <p className="error">{error}</p>}
            <button className="btn-submit" type="submit" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Join the Early Pilot Program'}
            </button>
          </form>
        )}
      </section>

      <footer className="landing-footer">
        <nav>
          <a href="https://github.com/anomalyco/officepilot" target="_blank" rel="noopener noreferrer">GitHub</a>
          <a href="https://opencode.ai" target="_blank" rel="noopener noreferrer">Docs</a>
          <a href="https://github.com/anomalyco/officepilot/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">License</a>
        </nav>
        <p>&copy; {new Date().getFullYear()} OfficePilot AI. All rights reserved.</p>
      </footer>
    </div>
  )
}
