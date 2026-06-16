import { useState } from 'react';

const steps5 = [
  { num: 1, title: 'Upload an Invoice', detail: 'Drag a sample invoice PDF onto the Upload page. The parser extracts vendor, total, line items, and confidence score automatically.' },
  { num: 2, title: 'Review & Approve', detail: 'Open the Review Queue. Verify the extracted fields. Click Approve to commit the invoice.' },
  { num: 3, title: 'Export to Excel', detail: 'Go to Export Excel. Select the approved invoice. Download the .xlsx file with line items and metadata.' },
  { num: 4, title: 'Audit Trail', detail: 'Open Audit Logs. See every action: upload, review, approve, export — all timestamped and attributed.' },
  { num: 5, title: 'Version Restore', detail: 'Go to Version History. Select any previous invoice version and click Restore with a reason. Confirm the restore in Restore Activity.' },
];

const steps15 = [
  { num: 1, title: 'Upload an Invoice', detail: 'Drag a sample invoice PDF onto the Upload page. The parser extracts vendor, total, line items, and confidence score automatically.' },
  { num: 2, title: 'Review & Approve', detail: 'Open the Review Queue. Verify the extracted fields. Click Approve to commit the invoice.' },
  { num: 3, title: 'Export to Excel', detail: 'Go to Export Excel. Select the approved invoice. Download the .xlsx file with line items and metadata.' },
  { num: 4, title: 'Audit Trail', detail: 'Open Audit Logs. See every action: upload, review, approve, export — all timestamped and attributed.' },
  { num: 5, title: 'Version Restore', detail: 'Go to Version History. Select any previous invoice version and click Restore with a reason. Confirm the restore in Restore Activity.' },
  { num: 6, title: 'Gmail Import', detail: 'Connect a test Gmail account. Run an email import. See invoices extracted from email attachments automatically.' },
  { num: 7, title: 'Workflow Automation', detail: 'Go to Workflow Runs. Start a new LangGraph workflow. Watch it move through nodes: extract, validate, enrich, approve, export.' },
  { num: 8, title: 'Browser Test Form', detail: 'Open Browser Test Form. Fill out a test web form with invoice data. Preview the action, then execute. Check Browser Logs for the audit trail.' },
  { num: 9, title: 'QuickBooks Sandbox', detail: 'Open Accounting Integrations. Connect the QuickBooks mock sandbox. Preview a sync entry. Approve and verify the sync log.' },
  { num: 10, title: 'Workflow Recording', detail: 'Open Recordings. Start a dry-run recording. Walk through invoice approval steps. Stop recording. Replay the recording step by step.' },
  { num: 11, title: 'Screen Assistant', detail: 'Open Screen Assistant. Click \'What is on my screen?\' to detect the active window. See OCR text from the current screen.' },
  { num: 12, title: 'Safety Policy', detail: 'Open Safety Policy Center. Review the current safety policies. Check the Automation Kill Switch status. Export an audit log.' },
];

function StepCard({ step, isOpen, onToggle }) {
  return (
    <div className={`step-card ${isOpen ? 'step-card--open' : ''}`} onClick={onToggle}>
      <div className="step-card__header">
        <span className="step-card__num">Step {step.num}</span>
        <span className="step-card__title">{step.title}</span>
        <span className="step-card__chevron">{isOpen ? '\u25B2' : '\u25BC'}</span>
      </div>
      {isOpen && <div className="step-card__detail">{step.detail}</div>}
    </div>
  );
}

export default function DemoScript() {
  const [activeTab, setActiveTab] = useState('5min');
  const [expanded, setExpanded] = useState({});

  const steps = activeTab === '5min' ? steps5 : steps15;

  const toggleStep = (num) => {
    setExpanded((prev) => ({ ...prev, [num]: !prev[num] }));
  };

  return (
    <div className="demo-script">
      <style>{`
        .demo-script {
          max-width: 800px;
          margin: 0 auto;
          padding: 24px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          color: #1a1a2e;
        }
        .demo-script__title {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 4px 0;
        }
        .demo-script__subtitle {
          font-size: 0.875rem;
          color: #6b7280;
          margin: 0 0 24px 0;
        }
        .demo-script__tabs {
          display: flex;
          gap: 0;
          border-bottom: 2px solid #e5e7eb;
          margin-bottom: 24px;
        }
        .demo-script__tab {
          padding: 10px 24px;
          border: none;
          background: none;
          font-size: 0.9rem;
          font-weight: 500;
          color: #6b7280;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
          transition: color 0.15s, border-color 0.15s;
        }
        .demo-script__tab:hover {
          color: #374151;
        }
        .demo-script__tab--active {
          color: #2563eb;
          border-bottom-color: #2563eb;
        }
        .demo-script__count {
          font-size: 0.8rem;
          color: #9ca3af;
          margin-bottom: 16px;
        }
        .step-card {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          margin-bottom: 8px;
          background: #ffffff;
          cursor: pointer;
          transition: box-shadow 0.15s;
          overflow: hidden;
        }
        .step-card:hover {
          box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }
        .step-card--open {
          border-color: #93c5fd;
        }
        .step-card__header {
          display: flex;
          align-items: center;
          padding: 14px 18px;
          gap: 12px;
        }
        .step-card__num {
          background: #2563eb;
          color: #fff;
          font-size: 0.75rem;
          font-weight: 600;
          border-radius: 99px;
          padding: 2px 10px;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .step-card__title {
          flex: 1;
          font-size: 0.95rem;
          font-weight: 500;
        }
        .step-card__chevron {
          font-size: 0.7rem;
          color: #9ca3af;
          flex-shrink: 0;
        }
        .step-card__detail {
          padding: 0 18px 14px 18px;
          font-size: 0.85rem;
          color: #4b5563;
          line-height: 1.5;
          border-top: 1px solid #f3f4f6;
          margin-top: 0;
          padding-top: 12px;
        }
      `}</style>

      <div style={{background:'#eff6ff', border:'1px solid #bfdbfe', borderRadius:'8px', padding:'16px 20px', marginBottom:'24px', textAlign:'center', fontSize:'0.9rem', color:'#1e40af', lineHeight:'1.5'}}>
        <strong>Want to try OfficePilot?</strong> Join the early pilot program — free, no credit card, sample data included.{' '}
        <a href="/welcome" style={{color:'#2563eb', fontWeight:600, textDecoration:'underline'}}>Sign up</a> or{' '}
        <a href="/faq" style={{color:'#2563eb', fontWeight:600, textDecoration:'underline'}}>learn more</a>.
      </div>

      <h1 className="demo-script__title">Demo Script</h1>
      <p className="demo-script__subtitle">Guided walkthrough of OfficePilot features</p>

      <div className="demo-script__tabs">
        <button
          className={`demo-script__tab ${activeTab === '5min' ? 'demo-script__tab--active' : ''}`}
          onClick={() => { setActiveTab('5min'); setExpanded({}); }}
        >
          5-Minute Demo
        </button>
        <button
          className={`demo-script__tab ${activeTab === '15min' ? 'demo-script__tab--active' : ''}`}
          onClick={() => { setActiveTab('15min'); setExpanded({}); }}
        >
          15-Minute Demo
        </button>
      </div>

      <p className="demo-script__count">{steps.length} steps</p>

      {steps.map((step) => (
        <StepCard
          key={step.num}
          step={step}
          isOpen={!!expanded[step.num]}
          onToggle={() => toggleStep(step.num)}
        />
      ))}
    </div>
  );
}
