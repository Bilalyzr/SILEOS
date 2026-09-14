import React from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { notificationsApi, AppNotification } from '@/api/notifications'

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = React.useState(false)
  const [items, setItems] = React.useState<AppNotification[]>([])
  const [unread, setUnread] = React.useState(0)

  const load = React.useCallback(async () => {
    try {
      const d = await notificationsApi.list()
      setItems(d.notifications)
      setUnread(d.unread_count)
    } catch {
      /* ignore — bell is non-critical */
    }
  }, [])

  React.useEffect(() => {
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [load])

  const onToggle = async () => {
    const opening = !open
    setOpen(opening)
    if (opening && unread > 0) {
      try {
        await notificationsApi.markAllRead()
        setUnread(0)
        setItems((prev) => prev.map((n) => ({ ...n, is_read: true })))
      } catch {
        /* ignore */
      }
    }
  }

  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-modal" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-white rounded-lg shadow-lg border border-gray-200 z-overlay">
            <div className="px-4 py-2 text-sm font-semibold text-gray-700 border-b">Notifications</div>
            {items.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-500">No notifications</div>
            ) : (
              items.map((n) => (
                <Link
                  key={n.id}
                  to={n.link || '#'}
                  onClick={() => setOpen(false)}
                  className={`block px-4 py-3 text-sm border-b last:border-b-0 hover:bg-gray-50 ${
                    n.is_read ? 'text-gray-600' : 'text-gray-900 bg-blue-50/40'
                  }`}
                >
                  <div className="font-medium">{n.title}</div>
                  {n.message && <div className="text-xs text-gray-500 line-clamp-2">{n.message}</div>}
                </Link>
              ))
            )}
          </div>
        </>
      )}
    </div>
  )
}
