import { useState, useEffect, useCallback } from 'react';
import { Eye, Mail, HardDrive, Folder, Plus, Play, Pause, Trash2, RefreshCw } from 'lucide-react';
import { api } from '../api';

const SOURCE_OPTIONS = [
  { value: 'gmail', label: 'Gmail Inbox', icon: Mail, color: '#ea4335' },
  { value: 'drive', label: 'Google Drive', icon: HardDrive, color: '#34a853' },
  { value: 'folder', label: 'Local Folder', icon: Folder, color: '#fbbc04' },
];

export default function WatcherSettings() {
  const [watchers, setWatchers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState('');
  const [formSource, setFormSource] = useState('gmail');
  const [formInterval, setFormInterval] = useState(60);
  const [formKeywords, setFormKeywords] = useState('');
  const [formDaysBack, setFormDaysBack] = useState(1);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [runningIds, setRunningIds] = useState(new Set());

  const fetchWatchers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listWatchers();
      setWatchers(res.watchers || []);
    } catch (err) {
      setError(err.message || 'Failed to load watchers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWatchers();
  }, [fetchWatchers]);

  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const config = {};
      if (formKeywords.trim()) {
        config.keywords = formKeywords.split(',').map(k => k.trim()).filter(Boolean);
      }
      if (formDaysBack > 0) {
        config.days_back = formDaysBack;
      }
      await api.createWatcher({
        name: formName.trim(),
        source_type: formSource,
        config_json: config,
        schedule_minutes: formInterval,
      });
      setShowForm(false);
      setFormName('');
      setFormSource('gmail');
      setFormInterval(60);
      setFormKeywords('');
      setFormDaysBack(1);
      showSuccess('Watcher created');
      await fetchWatchers();
    } catch (err) {
      setError(err.message || 'Failed to create watcher');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (w) => {
    try {
      const newStatus = w.status === 'active' ? 'paused' : 'active';
      await api.updateWatcher(w.id, { status: newStatus });
      showSuccess(newStatus === 'active' ? 'Watcher resumed' : 'Watcher paused');
      await fetchWatchers();
    } catch (err) {
      setError(err.message || 'Failed to toggle watcher');
    }
  };

  const handleDelete = async (w) => {
    if (!confirm(`Delete watcher "${w.name}"?`)) return;
    try {
      await api.deleteWatcher(w.id);
      showSuccess('Watcher deleted');
      await fetchWatchers();
    } catch (err) {
      setError(err.message || 'Failed to delete watcher');
    }
  };

  const handleRunNow = async (w) => {
    setRunningIds(prev => new Set(prev).add(w.id));
    setError(null);
    try {
      await api.runWatcherNow(w.id);
      showSuccess(`Watcher "${w.name}" triggered`);
      await fetchWatchers();
    } catch (err) {
      setError(err.message || 'Failed to run watcher');
    } finally {
      setRunningIds(prev => {
        const next = new Set(prev);
        next.delete(w.id);
        return next;
      });
    }
  };

  const SourceIcon = ({ type, size = 20 }) => {
    const opt = SOURCE_OPTIONS.find(s => s.value === type);
    if (!opt) return <Eye size={size} />;
    const Icon = opt.icon;
    return <Icon size={size} style={{ color: opt.color }} />;
  };

  if (loading && watchers.length === 0) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1><Eye size={24} style={{ verticalAlign: 'middle', marginRight: 8 }} />Background Watchers</h1>
          <p className="page-subtitle">Always-on invoice monitoring for Gmail, Drive, and local folders</p>
        </div>
        <div className="loading-state">Loading watchers…</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1><Eye size={24} style={{ verticalAlign: 'middle', marginRight: 8 }} />Background Watchers</h1>
        <p className="page-subtitle">Always-on invoice monitoring for Gmail, Drive, and local folders</p>
      </div>

      {error && <div className="error-message">{error}</div>}
      {successMsg && <div className="success-message">{successMsg}</div>}

      <div className="watcher-actions">
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} /> New Watcher
        </button>
        <button className="btn btn-secondary" onClick={fetchWatchers}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {showForm && (
        <form className="watcher-form" onSubmit={handleCreate}>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={formName}
              onChange={e => setFormName(e.target.value)}
              placeholder="e.g. Gmail Invoice Watcher"
              required
            />
          </div>

          <div className="form-group">
            <label>Source</label>
            <div className="source-options">
              {SOURCE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  className={`source-option ${formSource === opt.value ? 'active' : ''}`}
                  onClick={() => setFormSource(opt.value)}
                >
                  <opt.icon size={18} style={{ color: opt.color }} />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Check interval (minutes)</label>
            <input
              type="number"
              value={formInterval}
              onChange={e => setFormInterval(Number(e.target.value))}
              min={1}
              max={1440}
            />
          </div>

          <div className="form-group">
            <label>Keywords (comma-separated)</label>
            <input
              type="text"
              value={formKeywords}
              onChange={e => setFormKeywords(e.target.value)}
              placeholder="e.g. invoice, receipt, bill"
            />
          </div>

          <div className="form-group">
            <label>Days back to search</label>
            <input
              type="number"
              value={formDaysBack}
              onChange={e => setFormDaysBack(Number(e.target.value))}
              min={1}
              max={90}
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving || !formName.trim()}>
              {saving ? 'Creating…' : 'Create Watcher'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {watchers.length === 0 && !loading ? (
        <div className="empty-state">
          <Eye size={48} strokeWidth={1} />
          <p>No background watchers yet.</p>
          <p className="text-muted">Create a watcher to automatically monitor Gmail, Drive, or local folders for invoices.</p>
        </div>
      ) : (
        <div className="watcher-list">
          {watchers.map(w => (
            <div key={w.id} className={`watcher-card ${w.status === 'paused' ? 'paused' : ''}`}>
              <div className="watcher-card-header">
                <div className="watcher-card-info">
                  <SourceIcon type={w.source_type} size={24} />
                  <div>
                    <h3>{w.name}</h3>
                    <span className={`watcher-badge watcher-badge--${w.status}`}>{w.status}</span>
                    <span className="watcher-source-label">{SOURCE_OPTIONS.find(s => s.value === w.source_type)?.label || w.source_type}</span>
                  </div>
                </div>
                <div className="watcher-card-meta">
                  <span className="watcher-interval">Every {w.schedule_minutes} min</span>
                  {w.last_run_at && (
                    <span className="watcher-last-run">Last: {new Date(w.last_run_at).toLocaleString()}</span>
                  )}
                  {!w.last_run_at && <span className="watcher-last-run text-muted">Never run</span>}
                </div>
              </div>
              <div className="watcher-card-actions">
                <button className="btn btn-sm" onClick={() => handleRunNow(w)} disabled={runningIds.has(w.id)} title="Run now">
                  {runningIds.has(w.id) ? <RefreshCw size={14} className="spinning" /> : <Play size={14} />}
                  Run Now
                </button>
                <button className="btn btn-sm" onClick={() => handleToggle(w)} title={w.status === 'active' ? 'Pause' : 'Resume'}>
                  {w.status === 'active' ? <Pause size={14} /> : <Play size={14} />}
                  {w.status === 'active' ? 'Pause' : 'Resume'}
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(w)} title="Delete">
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
