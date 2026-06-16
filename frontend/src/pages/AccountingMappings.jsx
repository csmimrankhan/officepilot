import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'

export default function AccountingMappings() {
  const [vendorMaps, setVendorMaps] = useState([])
  const [categoryMaps, setCategoryMaps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [provider, setProvider] = useState('quickbooks')
  const [vendorSearch, setVendorSearch] = useState('')
  const [vendorResults, setVendorResults] = useState([])
  const [vendorName, setVendorName] = useState('')
  const [selectedVendor, setSelectedVendor] = useState(null)
  const [categorySearch, setCategorySearch] = useState('')
  const [categoryResults, setCategoryResults] = useState([])
  const [localCategory, setLocalCategory] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const v = await api.listAccountingVendorMappings(provider)
      const c = await api.listAccountingCategoryMappings(provider)
      setVendorMaps(v)
      setCategoryMaps(c)
    } catch (err) {
      setError(err.message || 'Failed to load mappings.')
    } finally {
      setLoading(false)
    }
  }, [provider])

  useEffect(() => { load() }, [load])

  const searchVendors = async () => {
    if (!vendorSearch.trim()) return
    setError('')
    try {
      const results = await api.searchAccountingVendors(provider, vendorSearch)
      setVendorResults(results)
    } catch (err) {
      setError(err.message || 'Failed to search vendors.')
    }
  }

  const searchCategories = async () => {
    if (!categorySearch.trim()) return
    setError('')
    try {
      const results = await api.searchAccountingCategories(provider, categorySearch)
      setCategoryResults(results)
    } catch (err) {
      setError(err.message || 'Failed to search categories.')
    }
  }

  const saveVendorMap = async () => {
    if (!vendorName.trim() || !selectedVendor) return
    setBusy(true)
    setError('')
    try {
      await api.mapAccountingVendor({
        provider,
        local_vendor_name: vendorName.trim(),
        external_contact_id: selectedVendor.id,
        external_contact_name: selectedVendor.name,
      })
      setMessage(`Mapped vendor "${vendorName}" -> "${selectedVendor.name}"`)
      setVendorName('')
      setSelectedVendor(null)
      setVendorResults([])
      await load()
    } catch (err) {
      setError(err.message || 'Failed to map vendor.')
    } finally {
      setBusy(false)
    }
  }

  const saveCategoryMap = async () => {
    if (!localCategory.trim() || !selectedCategory) return
    setBusy(true)
    setError('')
    try {
      await api.mapAccountingCategory({
        provider,
        local_category: localCategory.trim(),
        external_account_id: selectedCategory.id,
        external_account_name: selectedCategory.name,
      })
      setMessage(`Mapped category "${localCategory}" -> "${selectedCategory.name}"`)
      setLocalCategory('')
      setSelectedCategory(null)
      setCategoryResults([])
      await load()
    } catch (err) {
      setError(err.message || 'Failed to map category.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Accounting Mappings</h2>
        <span className="subtle">Map local vendors and categories to external accounting records</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}
      <div className="card">
        <h3>Provider</h3>
        <select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="quickbooks">QuickBooks</option>
          <option value="xero">Xero</option>
        </select>
        <div className="toolbar">
          <button className="secondary" onClick={load}>Refresh</button>
        </div>
      </div>
      <div className="card">
        <h3>Vendor / Contact Mapping</h3>
        <div className="field-row">
          <input
            type="text"
            placeholder="Local vendor name (e.g. Acme Office Supplies)"
            value={vendorName}
            onChange={(e) => setVendorName(e.target.value)}
            style={{ maxWidth: 320 }}
          />
          <input
            type="text"
            placeholder="Search external contacts..."
            value={vendorSearch}
            onChange={(e) => setVendorSearch(e.target.value)}
            style={{ maxWidth: 280 }}
          />
          <button className="secondary" onClick={searchVendors}>Search</button>
        </div>
        {vendorResults.length > 0 && (
          <table className="data-table">
            <thead>
              <tr><th>Contact ID</th><th>Name</th><th></th></tr>
            </thead>
            <tbody>
              {vendorResults.map((v) => (
                <tr key={v.id} className={selectedVendor?.id === v.id ? 'selected' : ''}>
                  <td><code className="mono">{v.id}</code></td>
                  <td>{v.name}</td>
                  <td>
                    <button className="secondary" onClick={() => setSelectedVendor(v)}>
                      {selectedVendor?.id === v.id ? 'Selected' : 'Select'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {selectedVendor && (
          <div className="alert info">
            Selected: <strong>{selectedVendor.name}</strong> ({selectedVendor.id})
          </div>
        )}
        <div className="toolbar">
          <button className="primary" onClick={saveVendorMap} disabled={busy || !vendorName || !selectedVendor}>
            {busy ? 'Saving…' : 'Save Vendor Map'}
          </button>
        </div>
        {vendorMaps.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h4>Existing Vendor Mappings</h4>
            <table className="data-table">
              <thead>
                <tr><th>Local Vendor</th><th>External Contact</th><th>Contact ID</th></tr>
              </thead>
              <tbody>
                {vendorMaps.map((m) => (
                  <tr key={m.id}>
                    <td>{m.local_vendor_name}</td>
                    <td>{m.external_contact_name}</td>
                    <td><code className="mono">{m.external_contact_id}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="card">
        <h3>Category / Account Mapping</h3>
        <div className="field-row">
          <input
            type="text"
            placeholder="Local category (e.g. Office Supplies)"
            value={localCategory}
            onChange={(e) => setLocalCategory(e.target.value)}
            style={{ maxWidth: 320 }}
          />
          <input
            type="text"
            placeholder="Search external accounts..."
            value={categorySearch}
            onChange={(e) => setCategorySearch(e.target.value)}
            style={{ maxWidth: 280 }}
          />
          <button className="secondary" onClick={searchCategories}>Search</button>
        </div>
        {categoryResults.length > 0 && (
          <table className="data-table">
            <thead>
              <tr><th>Account ID</th><th>Name</th><th></th></tr>
            </thead>
            <tbody>
              {categoryResults.map((c) => (
                <tr key={c.id} className={selectedCategory?.id === c.id ? 'selected' : ''}>
                  <td><code className="mono">{c.id}</code></td>
                  <td>{c.name}</td>
                  <td>
                    <button className="secondary" onClick={() => setSelectedCategory(c)}>
                      {selectedCategory?.id === c.id ? 'Selected' : 'Select'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {selectedCategory && (
          <div className="alert info">
            Selected: <strong>{selectedCategory.name}</strong> ({selectedCategory.id})
          </div>
        )}
        <div className="toolbar">
          <button className="primary" onClick={saveCategoryMap} disabled={busy || !localCategory || !selectedCategory}>
            {busy ? 'Saving…' : 'Save Category Map'}
          </button>
        </div>
        {categoryMaps.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h4>Existing Category Mappings</h4>
            <table className="data-table">
              <thead>
                <tr><th>Local Category</th><th>External Account</th><th>Account ID</th><th>Tax Code</th></tr>
              </thead>
              <tbody>
                {categoryMaps.map((m) => (
                  <tr key={m.id}>
                    <td>{m.local_category}</td>
                    <td>{m.external_account_name}</td>
                    <td><code className="mono">{m.external_account_id}</code></td>
                    <td><code className="mono">{m.external_tax_code || '—'}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
