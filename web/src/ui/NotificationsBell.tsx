import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadNotifications,
  type Notification,
} from '@/data/notifications'
import { formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'
import { destination, notificationLine } from '@/ui/notificationLines'

/** Enough to answer "what happened?" without becoming the page. The rest is
 *  behind "see all". */
const SHOWN = 6

/**
 * The bell.
 *
 * In the header rather than in the nav, because a notification is not a place
 * you go — it is a thing that arrived while you were somewhere else, and it has
 * to be visible from every screen without taking a slot in the menu.
 *
 * Closed it is one number. Open it is the list, and each line does the same
 * thing C6 does: marks itself read and goes to the thing it is about.
 */
export function NotificationsBell({ area }: { area: string }) {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)

  const unread = useUnreadNotifications(true)
  const count = unread.data?.count ?? 0

  // Only fetched once he opens it: the closed bell needs the number, not the
  // rows, and the number is its own endpoint for exactly that reason.
  const notifications = useNotifications(1, open)
  const markRead = useMarkNotificationRead()
  const markAll = useMarkAllNotificationsRead()

  useEffect(() => {
    if (!open) return

    function onPointerDown(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const items = (notifications.data?.items ?? []).slice(0, SHOWN)

  const openOne = (notification: Notification) => {
    setOpen(false)
    if (notification.read_at === null) markRead.mutate({ id: notification.id })
    const to = destination(notification, area)
    if (to) navigate(to)
  }

  return (
    <div ref={container} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={
          count > 0 ? t('notify.bellWith', { count }) : t('notify.title')
        }
        className={cn(
          'relative flex size-9 items-center justify-center rounded-full border text-fg-muted',
          'transition-colors duration-(--duration-fast)',
          'hover:border-border-strong hover:text-fg',
          open ? 'border-border-strong bg-surface-2 text-fg' : 'border-border bg-surface',
        )}
      >
        <BellGlyph ringing={count > 0} />

        {count > 0 && (
          // `-end-1` / `-top-1`, so it sits on the outer corner in both
          // directions rather than crossing the bell in Arabic.
          <span
            aria-hidden
            className="numeric absolute -end-1 -top-1 inline-flex min-w-4.5 items-center justify-center rounded-pill bg-primary px-1 py-px text-[10px] font-bold text-primary-fg"
          >
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute end-0 top-full z-30 mt-2 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-md border border-border bg-surface shadow-lg"
        >
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-fg">{t('notify.title')}</p>
            {count > 0 && (
              <button
                type="button"
                onClick={() => markAll.mutate()}
                className="text-xs font-semibold text-primary underline-offset-2 hover:underline"
              >
                {t('notify.markAll')}
              </button>
            )}
          </div>

          {notifications.isPending ? (
            <p className="px-4 py-6 text-center text-sm text-fg-subtle">
              {t('common.loading')}
            </p>
          ) : items.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-fg-subtle">
              {t('notify.empty')}
            </p>
          ) : (
            // Its own scroll, so six lines never push "see all" off a phone.
            <ul className="max-h-96 overflow-y-auto">
              {items.map((notification) => (
                <li key={notification.id}>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => openOne(notification)}
                    className={cn(
                      'flex w-full items-start gap-2.5 border-b border-border px-4 py-3 text-start last:border-b-0',
                      'transition-colors duration-(--duration-fast) hover:bg-surface-2',
                      notification.read_at === null && 'bg-primary-soft',
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        'mt-1.5 size-1.5 shrink-0 rounded-full',
                        notification.read_at === null ? 'bg-primary' : 'bg-transparent',
                      )}
                    />
                    <span className="min-w-0 flex-1">
                      <span
                        className={cn(
                          'block text-sm',
                          notification.read_at === null
                            ? 'font-semibold text-fg'
                            : 'text-fg-muted',
                        )}
                      >
                        {notificationLine(t, notification, language)}
                      </span>
                      <span className="numeric mt-0.5 block text-xs text-fg-subtle">
                        {formatRelative(notification.created_at, language)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Only where a full page exists. A "see all" that 404s is worse
              than no link. */}
          {area === '/client' && (
            <Link
              to="/client/notifications"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="block border-t border-border px-4 py-2.5 text-center text-sm font-semibold text-primary hover:bg-surface-2"
            >
              {t('notify.seeAll')}
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

function BellGlyph({ ringing }: { ringing: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {/* Tilted a few degrees when something is waiting: the shape says
          "ringing" before the number is read, and it costs no motion. */}
      <g transform={ringing ? 'rotate(-12 12 12)' : undefined}>
        <path d="M18 9a6 6 0 1 0-12 0c0 4.2-1.2 5.7-2 6.5h16c-.8-.8-2-2.3-2-6.5Z" />
        <path d="M10 19a2.2 2.2 0 0 0 4 0" />
      </g>
    </svg>
  )
}
