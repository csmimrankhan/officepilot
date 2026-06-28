import { api } from '../api.js'

export function isTauriRuntime() {
  return typeof window !== 'undefined' && window.__TAURI__ !== undefined
}

export async function checkForTauriUpdate() {
  if (isTauriRuntime()) {
    const { check } = await import('@tauri-apps/plugin-updater')
    return check()
  }
  try {
    const res = await api.checkUpdate({
      app_version: '1.0.0',
      platform: 'windows',
      channel: 'stable',
    })
    if (res.update_available) {
      return {
        version: res.latest_version,
        body: res.release_notes || '',
        date: '',
        currentVersion: '0.36.0',
        shouldUpdate: true,
        isCritical: res.critical,
        downloadUrl: res.download_url,
      }
    }
    return null
  } catch {
    return null
  }
}

export async function downloadAndInstallUpdate(update) {
  if (isTauriRuntime()) {
    const { downloadAndInstall, onUpdaterEvent } = await import('@tauri-apps/plugin-updater')
    return new Promise((resolve, reject) => {
      const unlisten = onUpdaterEvent((event) => {
        if (event.status === 'DONE') {
          unlisten()
          resolve()
        } else if (event.status === 'ERROR') {
          unlisten()
          reject(new Error(event.error))
        }
      })
      downloadAndInstall(update)
        .catch(reject)
    })
  }
  if (update && update.downloadUrl) {
    window.open(update.downloadUrl, '_blank')
    return
  }
  throw new Error('No download URL available')
}

export function restartAppIfNeeded() {
  if (!isTauriRuntime()) return
  try {
    window.__TAURI__.process.exit(0)
  } catch {
    try {
      window.__TAURI__.exit(0)
    } catch {
    }
  }
}
