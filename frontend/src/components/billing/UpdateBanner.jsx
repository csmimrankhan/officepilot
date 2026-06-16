import { useState, useEffect } from 'react'
import { checkForTauriUpdate, downloadAndInstallUpdate, restartAppIfNeeded, isTauriRuntime } from '../../utils/tauriUpdater.js'

export default function UpdateBanner() {
  const [update, setUpdate] = useState(null)
  const [installing, setInstalling] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const check = async () => {
      try {
        const result = await checkForTauriUpdate()
        if (result) {
          setUpdate(result)
        }
      } catch {}
    }
    const timer = setTimeout(check, 2000)
    const interval = setInterval(check, 3600000)
    return () => { clearTimeout(timer); clearInterval(interval) }
  }, [])

  const handleInstall = async () => {
    if (!update) return
    setInstalling(true)
    setError(null)
    try {
      await downloadAndInstallUpdate(update)
      if (isTauriRuntime()) {
        restartAppIfNeeded()
      }
    } catch (e) {
      setError(e.message || 'Update failed')
      setInstalling(false)
    }
  }

  if (!update) return null

  const isCritical = update.isCritical || update.blocked
  const version = update.latest_version || update.version

  return (
    <div className={`update-banner ${isCritical ? 'update-banner--critical' : 'update-banner--info'}`}>
      <div className="update-banner-content">
        <span className="update-banner-icon">{isCritical ? '⚠️' : '🔄'}</span>
        <div>
          <div className="update-banner-title">
            {isCritical
              ? `Critical update required: v${version}`
              : `Update available: v${version}`}
          </div>
          {(update.release_notes || update.body) && (
            <div className="update-banner-notes">{update.release_notes || update.body}</div>
          )}
          {error && <div className="update-banner-error">{error}</div>}
        </div>
      </div>
      <div className="update-banner-actions">
        {isTauriRuntime() ? (
          <button
            className="btn btn--sm btn--primary"
            onClick={handleInstall}
            disabled={installing}
          >
            {installing ? 'Installing...' : isCritical ? 'Update Now' : 'Download & Install'}
          </button>
        ) : (
          <a
            href={update.downloadUrl || update.download_url || '#'}
            className="btn btn--sm btn--primary"
            target="_blank"
            rel="noopener noreferrer"
          >
            {isCritical ? 'Update Now' : 'Download'}
          </a>
        )}
      </div>
    </div>
  )
}
