import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useLogout } from '@/data/auth'
import type { Me } from '@/data/types'
import { cn } from '@/ui/cn'

/**
 * Who is signed in, and the way out.
 *
 * This replaces the sign-in and register buttons entirely once there is a
 * session: offering "sign in" to somebody who is already signed in is the
 * header telling them it has not noticed them.
 */
export function UserMenu({ user, className }: { user: Me; className?: string }) {
  const { t } = useTranslation()
  const logout = useLogout()
  const [open, setOpen] = useState(false)
  const container = useRef<HTMLDivElement>(null)

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

  const accountPath = `${user.home_path.split('/').slice(0, 2).join('/')}/account`

  return (
    <div ref={container} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex min-h-9 items-center gap-2 rounded-md border border-border bg-surface ps-1 pe-2.5 transition-colors duration-(--duration-fast) hover:border-border-strong"
      >
        <Avatar user={user} />
        <span className="hidden max-w-32 truncate text-sm font-medium text-fg sm:inline">
          {user.full_name}
        </span>
        <svg
          viewBox="0 0 24 24"
          className={cn(
            'size-4 text-fg-subtle transition-transform duration-(--duration-fast)',
            open && 'rotate-180',
          )}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute end-0 top-full z-30 mt-2 w-56 overflow-hidden rounded-md border border-border bg-surface shadow-lg"
        >
          <div className="border-b border-border px-4 py-3">
            <p className="truncate text-sm font-semibold text-fg">{user.full_name}</p>
            <p className="numeric mt-0.5 text-xs text-fg-subtle">{user.phone}</p>
            <p className="mt-1.5 text-xs font-medium text-primary">{t(`roles.${user.role}`)}</p>
          </div>

          <Link
            to={user.home_path}
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-4 py-2.5 text-sm text-fg hover:bg-surface-2"
          >
            {t('nav.dashboard')}
          </Link>
          <Link
            to={accountPath}
            role="menuitem"
            onClick={() => setOpen(false)}
            className="block px-4 py-2.5 text-sm text-fg hover:bg-surface-2"
          >
            {t('nav.account')}
          </Link>

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false)
              logout.mutate()
            }}
            className="block w-full border-t border-border px-4 py-2.5 text-start text-sm text-danger hover:bg-danger-soft"
          >
            {t('common.signOut')}
          </button>
        </div>
      )}
    </div>
  )
}

function Avatar({ user }: { user: Me }) {
  const initials = user.full_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()

  return (
    <span className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-primary text-xs font-bold text-primary-fg">
      {initials || '?'}
    </span>
  )
}
