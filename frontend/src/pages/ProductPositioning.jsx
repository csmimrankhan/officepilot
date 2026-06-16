import React from 'react';

const style = document.createElement('style');
style.textContent = `
  .pp-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 48px 24px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1a1a2e;
  }

  .pp-header {
    text-align: center;
    margin-bottom: 56px;
  }

  .pp-header h1 {
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 8px;
    color: #1a1a2e;
  }

  .pp-header p {
    font-size: 16px;
    color: #6b7280;
    margin: 0;
    line-height: 1.6;
  }

  .pp-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    margin-bottom: 64px;
  }

  .pp-column {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }

  .pp-column h2 {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid #e5e7eb;
  }

  .pp-column.is-not h2 {
    color: #dc2626;
    border-bottom-color: #fecaca;
  }

  .pp-column.is h2 {
    color: #2563eb;
    border-bottom-color: #bfdbfe;
  }

  .pp-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .pp-list li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 15px;
    line-height: 1.5;
    color: #374151;
  }

  .pp-icon {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    margin-top: 2px;
  }

  .pp-icon.is-not {
    background: #fef2f2;
    color: #dc2626;
  }

  .pp-icon.is {
    background: #eff6ff;
    color: #2563eb;
  }

  .pp-who {
    text-align: center;
    margin-bottom: 40px;
  }

  .pp-who h2 {
    font-size: 28px;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0 0 8px;
  }

  .pp-who p {
    font-size: 16px;
    color: #6b7280;
    margin: 0;
  }

  .pp-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
  }

  .pp-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 28px 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s, border-color 0.2s;
  }

  .pp-card:hover {
    box-shadow: 0 4px 12px rgba(37,99,235,0.1);
    border-color: #bfdbfe;
  }

  .pp-card-emoji {
    font-size: 32px;
    margin-bottom: 16px;
    display: block;
  }

  .pp-card h3 {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a2e;
    margin: 0 0 8px;
  }

  .pp-card p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
    line-height: 1.5;
  }

  .pp-footer {
    text-align: center;
    margin-top: 48px;
    padding-top: 32px;
    border-top: 1px solid #e5e7eb;
  }

  .pp-footer p {
    font-size: 14px;
    color: #9ca3af;
    margin: 0;
  }

  @media (max-width: 900px) {
    .pp-columns {
      grid-template-columns: 1fr;
      gap: 24px;
    }

    .pp-cards {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 600px) {
    .pp-container {
      padding: 24px 16px;
    }

    .pp-header h1 {
      font-size: 26px;
    }

    .pp-column {
      padding: 24px 20px;
    }

    .pp-cards {
      grid-template-columns: 1fr;
    }
  }
`;

if (!document.head.querySelector('[data-pp-style]')) {
  style.setAttribute('data-pp-style', '');
  document.head.appendChild(style);
}

function ProductPositioning() {
  const notItems = [
    'A general-purpose chatbot or AI assistant',
    'A screen-clicking bot that automates anything on your computer',
    'A banking or payment automation system',
    'A replacement for your accountant or bookkeeper',
    'A cloud service that sends your data to external AI providers',
    'A no-code automation platform like Zapier or Power Automate',
  ];

  const isItems = [
    'An invoice automation system that turns emailed PDFs into structured data',
    'An Excel export and accounting draft sync tool',
    'A workflow recording and replay system for repetitive tasks',
    'A browser assistant with approval gates for every write operation',
    'A screen context tool that reads what\'s on your screen with your permission',
    'A local-first, audit-logged, restore-safe automation platform',
  ];

  const whoCards = [
    {
      emoji: '\u{1F4C7}',
      title: 'Accountants & Bookkeepers',
      desc: 'Automate invoice data entry and focus on exceptions',
    },
    {
      emoji: '\u{1F465}',
      title: 'Admin Teams',
      desc: 'Stop copy-pasting between email, Excel, and accounting systems',
    },
    {
      emoji: '\u{1F3E2}',
      title: 'SME Owners',
      desc: 'Get visibility into your payables without hiring a full-time AP clerk',
    },
    {
      emoji: '\u{1F30D}',
      title: 'BPO / Outsourcing Firms',
      desc: 'Standardize invoice processing across multiple clients',
    },
  ];

  return (
    <div className="pp-container">
      <div className="pp-header">
        <h1>What OfficePilot Is &amp; Is Not</h1>
        <p>
          OfficePilot is purpose-built for one thing &mdash; invoice automation on
          your Windows desktop. Here&rsquo;s exactly where it fits and where it
          doesn&rsquo;t.
        </p>
      </div>

      <div className="pp-columns">
        <div className="pp-column is-not">
          <h2>OfficePilot Is NOT</h2>
          <ul className="pp-list">
            {notItems.map((item, i) => (
              <li key={i}>
                <span className="pp-icon is-not">&times;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="pp-column is">
          <h2>OfficePilot IS</h2>
          <ul className="pp-list">
            {isItems.map((item, i) => (
              <li key={i}>
                <span className="pp-icon is">&check;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="pp-who">
        <h2>Who It&rsquo;s For</h2>
        <p>Designed for teams that process invoices day in and day out</p>
      </div>

      <div className="pp-cards">
        {whoCards.map((card, i) => (
          <div className="pp-card" key={i}>
            <span className="pp-card-emoji">{card.emoji}</span>
            <h3>{card.title}</h3>
            <p>{card.desc}</p>
          </div>
        ))}
      </div>

      <div className="pp-footer">
        <p>OfficePilot &mdash; Local-first invoice automation for Windows</p>
      </div>
    </div>
  );
}

export default ProductPositioning;
