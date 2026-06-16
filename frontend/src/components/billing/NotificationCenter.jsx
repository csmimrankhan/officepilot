import { useState, useEffect } from 'react'
import { api } from '../../api.js'

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadNotifications()
  }, [])

  const loadNotifications = async () => {
    setLoading(true)
    try {
      const data = await api.getNotifications()
      setNotifications(data.notifications || [])
    } catch {}
    setLoading(false)
  }

  const handleSeen = async (id) => {
    try {
      await api.markNotificationSeen(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, seen: true, seen_at: new Date().toISOString() } : n))
    } catch {}
  }

  return (
    <div className="notification-center">
      <h3 className="notification-center-title">Notifications</h3>
      {loading && <div className="text-muted" style={{ padding: '12px' }}>Loading...</div>}
      {!loading && notifications.length === 0 && (
        <div className="text-muted" style={{ padding: '12px' }}>No notifications</div>
      )}
      <div className="notification-list">
        {notifications.map(n => (
          <div key={n.id} className={`notification-item ${n.seen ? 'notification-item--seen' : 'notification-item--unseen'}`}>
            <div className="notification-item-header">
              <span className={`notification-type-badge notification-type--${n.type}`}>{n.type}</span>
              <span className="notification-item-date">
                {new Date(n.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="notification-item-title">{n.title}</div>
            {n.message && <div className="notification-item-message">{n.message}</div>}
            <div className="notification-item-actions">
              {n.action_url && (
                <a href={n.action_url} className="btn btn--ghost btn--xs" target="_blank" rel="noopener noreferrer">
                  View
                </a>
              )}
              {!n.seen && (
                <button className="btn btn--ghost btn--xs" onClick={() => handleSeen(n.id)}>
                  Mark as read
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
