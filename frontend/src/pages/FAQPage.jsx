import React from 'react';

const faqs = [
  {
    q: 'What does OfficePilot do?',
    a: 'OfficePilot is a Universal Voice Accountant Agent. You tell it what to do by voice or text, it plans the task step-by-step, shows you the preview, asks for your approval, and executes safely. It works with Excel, any browser app, any accounting platform (QuickBooks, Xero, Zoho Books, Odoo, FreshBooks, Wave, Sage, custom ERP), and your desktop workflows. Invoice processing is one of many workflow templates.',
  },
  {
    q: 'Is OfficePilot limited to QuickBooks and Xero?',
    a: 'No. OfficePilot works with any accounting platform you already use. You log into your accounting website or desktop app yourself. OfficePilot reads the visible screen, helps you copy/paste/report/update forms with your approval, and records repeatable workflows. No official API is required — it works with any platform the user can see and use.',
  },
  {
    q: 'Is OfficePilot a cloud service?',
    a: 'No. OfficePilot runs entirely on your local machine. All data stays on your computer unless you explicitly connect it to Gmail, QuickBooks, or Xero. No data is sent to external AI providers.',
  },
  {
    q: 'Does OfficePilot require internet access?',
    a: 'The core app works offline. Internet is only needed for optional features: Gmail email import, QuickBooks/Xero accounting sync, and browser automation. If you use only local invoice upload + Excel export, no internet is needed.',
  },
  {
    q: 'Is my data safe?',
    a: 'Yes. OfficePilot is local-first. All invoice data, audit logs, and version history are stored on your machine. Your team controls every button through approval gates and role-based permissions. Snapshots are taken before every mutation, and a global kill switch can halt all automation instantly.',
  },
  {
    q: 'Can OfficePilot access my bank accounts?',
    a: 'No. OfficePilot does not connect to banks, process payments, or automate banking websites. Banking domains are blocked in browser automation mode. The app is designed for invoice processing — not payment execution.',
  },
  {
    q: 'Does OfficePilot use AI for extraction?',
    a: 'OfficePilot uses a combination of PDF parsing (PyMuPDF, pdfplumber), OCR (Tesseract), and pattern matching to extract invoice data. It does NOT use external AI APIs or cloud LLMs. All extraction happens locally.',
  },
  {
    q: 'Can I use OfficePilot with my accounting software?',
    a: 'OfficePilot supports QuickBooks Online and Xero via their official APIs. Sync is preview-first: you review a draft entry before it reaches your accounting system. Both mock/sandbox and real modes are supported.',
  },
  {
    q: 'Who should use OfficePilot?',
    a: 'OfficePilot is designed for accountants, bookkeepers, administrative teams, small business owners, and BPO/outsourcing firms who process invoices regularly and want a local, auditable, safe automation layer.',
  },
  {
    q: 'Is OfficePilot open source?',
    a: 'OfficePilot is source-available. The code is published on GitHub for review and self-hosting. The project uses a standard open-source license. Commercial use terms are defined in the license.',
  },
  {
    q: 'Does OfficePilot support multiple users?',
    a: 'Yes. OfficePilot has built-in role-based permissions with 5 roles and 18 permissions. The first user to register becomes the owner and can invite/manage other users.',
  },
  {
    q: 'How do I get started?',
    a: 'Download the latest installer from the GitHub releases page, run the setup, and register as the first owner. The built-in onboarding checklist will guide you through the initial setup. Demo mode is also available with sample invoice data.',
  },
  {
    q: 'What makes OfficePilot different from other invoice tools?',
    a: 'OfficePilot combines four things most tools don\'t: (1) local-first processing — your data never leaves your machine, (2) approval gates on every write, export, and sync, (3) full version history with one-click restore and mandatory reason, and (4) a global kill switch that can halt all automation instantly. It\'s designed for teams that need automation they can trust, not just automation that\'s fast.',
  },
];

export default function FAQPage() {
  return (
    <div className="faq-page">
      <style>{`
        .faq-page {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem 1.5rem;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          color: #1a1a2e;
          min-height: 100vh;
        }
        .faq-page h1 {
          font-size: 1.75rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
          color: #0f0f23;
          letter-spacing: -0.02em;
        }
        .faq-page .subtitle {
          font-size: 0.95rem;
          color: #6b7280;
          margin-bottom: 2rem;
          line-height: 1.5;
        }
        .faq-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        .faq-list details {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          overflow: hidden;
          box-shadow: 0 1px 2px rgba(0,0,0,0.04);
          transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }
        .faq-list details[open] {
          border-color: #3b82f6;
          box-shadow: 0 2px 8px rgba(59,130,246,0.08);
        }
        .faq-list summary {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.25rem;
          font-weight: 600;
          font-size: 0.95rem;
          cursor: pointer;
          user-select: none;
          line-height: 1.4;
          color: #1f2937;
          background: #fafbfc;
          transition: background 0.15s ease;
        }
        .faq-list summary:hover {
          background: #f3f4f6;
        }
        .faq-list details[open] summary {
          background: #eff6ff;
          color: #1d4ed8;
          border-bottom: 1px solid #e5e7eb;
        }
        .faq-list summary::-webkit-details-marker {
          display: none;
        }
        .faq-list summary::marker {
          display: none;
        }
        .faq-list summary::after {
          content: '+';
          font-size: 1.25rem;
          font-weight: 400;
          color: #9ca3af;
          margin-left: 1rem;
          flex-shrink: 0;
          transition: transform 0.2s ease, color 0.2s ease;
        }
        .faq-list details[open] summary::after {
          content: '−';
          color: #3b82f6;
          transform: rotate(180deg);
        }
        .faq-list .answer {
          padding: 0 1.25rem 1.125rem;
          font-size: 0.9rem;
          line-height: 1.7;
          color: #4b5563;
        }
        .faq-list .answer a {
          color: #2563eb;
          text-decoration: none;
        }
        .faq-list .answer a:hover {
          text-decoration: underline;
        }
        .faq-footer {
          margin-top: 2.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #e5e7eb;
          text-align: center;
          font-size: 0.85rem;
          color: #9ca3af;
        }
      `}</style>
      <h1>Frequently Asked Questions</h1>
      <p className="subtitle">Common questions about OfficePilot AI.</p>
      <div className="faq-list">
        {faqs.map((faq, i) => (
          <details key={i}>
            <summary>{faq.q}</summary>
            <div className="answer">{faq.a}</div>
          </details>
        ))}
      </div>
      <div className="faq-footer">
        OfficePilot AI &mdash; Local First. Always Auditable.
      </div>
    </div>
  );
}
