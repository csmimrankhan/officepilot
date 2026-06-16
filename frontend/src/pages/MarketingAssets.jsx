const style = document.createElement('style');
style.textContent = `
  .marketing-assets {
    padding: 32px;
    max-width: 1100px;
    margin: 0 auto;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    color: #1a1a1a;
  }
  .marketing-assets h1 {
    font-size: 28px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: #111;
  }
  .marketing-assets .subtitle {
    font-size: 15px;
    color: #666;
    margin: 0 0 32px 0;
    line-height: 1.5;
  }
  .marketing-assets table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    overflow: hidden;
  }
  .marketing-assets th {
    background: #f8f9fa;
    text-align: left;
    padding: 14px 16px;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #555;
    border-bottom: 2px solid #e9ecef;
  }
  .marketing-assets td {
    padding: 16px;
    font-size: 14px;
    line-height: 1.5;
    border-bottom: 1px solid #f0f0f0;
    vertical-align: top;
  }
  .marketing-assets tr:last-child td {
    border-bottom: none;
  }
  .marketing-assets .num {
    text-align: center;
    width: 40px;
    font-weight: 600;
    color: #888;
  }
  .marketing-assets .name {
    font-weight: 600;
    color: #1a73e8;
    white-space: nowrap;
  }
  .marketing-assets .notes {
    font-size: 13px;
    color: #666;
    max-width: 320px;
  }
  .marketing-assets .notes strong {
    color: #444;
  }
  .marketing-assets tr:hover td {
    background: #fafcff;
  }
`;
document.head.appendChild(style);

const screenshots = [
  {
    name: 'Invoice Review Queue',
    description: 'The Review Queue page showing a list of extracted invoices with confidence scores, Approve/Reject buttons, and status filters.',
    notes: 'Full page, browser window 1280x800. Show at least 4 invoices with mixed confidence scores.',
  },
  {
    name: 'Excel Export Preview',
    description: 'The Export Excel page with a preview of exported data, column mappings, and the Download button.',
    notes: 'Show the export preview table with 3-4 invoice rows. Highlight the column mapping section.',
  },
  {
    name: 'Accounting Sync Preview',
    description: 'The accounting sync preview showing draft journal entries ready for QuickBooks/Xero.',
    notes: 'Show the approval modal with entry details, vendor name, amount, and Approve/Reject buttons.',
  },
  {
    name: 'Audit Log & Restore',
    description: 'The Audit Logs page next to the Version History page showing the change timeline.',
    notes: 'Two-panel layout: audit log on the left, version history card on the right. Highlight a restore action.',
  },
  {
    name: 'Safety Policy Center',
    description: 'The Safety Policy Center showing policy toggles, kill switch status, and the role permissions grid.',
    notes: 'Show the full policy page with 5 toggle cards, the global kill switch at the top, and the permissions table below.',
  },
  {
    name: 'Screen Assistant with Voice',
    description: 'The Screen Assistant panel showing detected active window, OCR text excerpt, and action approval buttons.',
    notes: 'Show the assistant panel docked to the right side of the app, with a detected window name and action buttons.',
  },
];

function MarketingAssets() {
  return (
    <div className="marketing-assets">
      <h1>Marketing Screenshot Assets</h1>
      <p className="subtitle">
        Placeholder descriptions of screenshots to capture for the product landing page and demo materials.
      </p>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Screenshot Name</th>
            <th>Description</th>
            <th>Composition Notes</th>
          </tr>
        </thead>
        <tbody>
          {screenshots.map((s, i) => (
            <tr key={i}>
              <td className="num">{i + 1}</td>
              <td className="name">{s.name}</td>
              <td>{s.description}</td>
              <td className="notes"><strong>Capture:</strong> {s.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default MarketingAssets;
