import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'

const FIELD_KEYS = [
  'vendor_name',
  'invoice_number',
  'invoice_date',
  'due_date',
  'currency',
  'subtotal',
  'tax',
  'total_amount'
]

const FIELD_LABELS = {
  vendor_name: 'Vendor',
  invoice_number: 'Invoice #',
  invoice_date: 'Invoice date',
  due_date: 'Due date',
  currency: 'Currency',
  subtotal: 'Subtotal',
  tax: 'Tax',
  total_amount: 'Total'
}

function pct(value) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}

function matchBadge(match) {
  if (match === true) return <span className="badge ok">match</span>
  if (match === false) return <span className="badge bad">mismatch</span>
  return <span className="badge">—</span>
}

export default function ParserBenchmark() {
  const [engines, setEngines] = useState([])
  const [selected, setSelected] = useState([])
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listParserEngines()
      .then((res) => {
        setEngines(res.engines || [])
        setSelected((res.engines || []).map((e) => e.name))
      })
      .catch((e) => setError(e.message || String(e)))
  }, [])

  const toggle = (name) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    )
  }

  const runBenchmark = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.runParserBenchmark({ engines: selected, format: 'json' })
      setReport(r)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const downloadCsv = async () => {
    try {
      const text = await api.runParserBenchmark({ engines: selected, format: 'csv' })
      const blob = new Blob([text], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'parser_benchmark.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message || String(e))
    }
  }

  // Build a 2D table: rows = (engine, fixture), cols = fields.
  const tableData = useMemo(() => {
    if (!report) return { rows: [], engines: [], fixtures: [] }
    const fixtures = Array.from(new Set(report.runs.map((r) => r.name)))
    const enginesUsed = Array.from(new Set(report.runs.map((r) => r.parser_engine)))
    const rows = []
    for (const eng of enginesUsed) {
      for (const fix of fixtures) {
        const run = report.runs.find((r) => r.parser_engine === eng && r.name === fix)
        rows.push({ engine: eng, fixture: fix, run })
      }
    }
    return { rows, engines: enginesUsed, fixtures }
  }, [report])

  return (
    <div className="page">
      <h2>Parser Benchmark <small>Phase 5</small></h2>
      <p className="muted">
        Compares the registered parser engines (existing, docling, ocr, hybrid)
        against three synthetic golden invoices. Use this to A/B test new
        engines before flipping the production <code>PARSER_ENGINE</code> setting.
      </p>

      <div className="card">
        <h3>Engines</h3>
        {engines.length === 0 && <p className="muted">Loading engines…</p>}
        <ul className="engine-list">
          {engines.map((e) => (
            <li key={e.name}>
              <label>
                <input
                  type="checkbox"
                  checked={selected.includes(e.name)}
                  onChange={() => toggle(e.name)}
                />
                <strong>{e.name}</strong>
                <span className="muted"> — {e.description || e.class}</span>
              </label>
            </li>
          ))}
        </ul>
        <div className="actions">
          <button className="primary" onClick={runBenchmark} disabled={loading || selected.length === 0}>
            {loading ? 'Running…' : 'Run benchmark'}
          </button>
          <button onClick={downloadCsv} disabled={loading || !report}>
            Download CSV
          </button>
        </div>
        {error && <div className="error">Error: {error}</div>}
      </div>

      {report && (
        <>
          <div className="card">
            <h3>Per-engine summary</h3>
            <table className="benchmark-summary">
              <thead>
                <tr>
                  <th>Engine</th>
                  <th>Runs</th>
                  <th>Avg runtime</th>
                  <th>OCR used</th>
                  <th>Line-item accuracy</th>
                  <th>Warnings</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(report.summary).map((s) => (
                  <tr key={s.engine}>
                    <td><strong>{s.engine}</strong></td>
                    <td>{s.runs}</td>
                    <td>{s.avg_runtime_ms?.toFixed?.(1) ?? '—'} ms</td>
                    <td>{pct(s.ocr_used_pct)}</td>
                    <td>{pct(s.line_item_count_accuracy)}</td>
                    <td>{s.total_warnings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Per-field accuracy</h3>
            <table className="benchmark-summary">
              <thead>
                <tr>
                  <th>Engine</th>
                  {FIELD_KEYS.map((k) => <th key={k}>{FIELD_LABELS[k]}</th>)}
                </tr>
              </thead>
              <tbody>
                {Object.values(report.summary).map((s) => (
                  <tr key={s.engine}>
                    <td><strong>{s.engine}</strong></td>
                    {FIELD_KEYS.map((k) => (
                      <td key={k}>{pct(s.field_accuracy?.[k]?.accuracy)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Per (engine, fixture) detail</h3>
            <table className="benchmark-detail">
              <thead>
                <tr>
                  <th>Engine</th>
                  <th>Fixture</th>
                  <th>Runtime</th>
                  <th>OCR</th>
                  <th>Text source</th>
                  {FIELD_KEYS.map((k) => <th key={k}>{FIELD_LABELS[k]}</th>)}
                  <th>Line items</th>
                </tr>
              </thead>
              <tbody>
                {tableData.rows.map((row, i) => (
                  <tr key={`${row.engine}-${row.fixture}-${i}`}>
                    <td>{row.engine}</td>
                    <td>{row.fixture}</td>
                    <td>{row.run?.runtime_ms?.toFixed?.(1) ?? '—'} ms</td>
                    <td>{row.run?.used_ocr ? 'yes' : 'no'}</td>
                    <td><code>{row.run?.text_source ?? '—'}</code></td>
                    {FIELD_KEYS.map((k) => (
                      <td key={k}>
                        {matchBadge(row.run?.fields?.[k]?.match)}
                        <div className="muted small">
                          {row.run?.fields?.[k]?.actual ?? '—'}
                        </div>
                      </td>
                    ))}
                    <td>
                      {matchBadge(row.run?.line_item_count_match)}
                      <div className="muted small">{row.run?.line_item_count} items</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
