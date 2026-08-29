import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useLogout, useSession } from '@/data/auth'
import type { Me } from '@/data/types'
import { cn } from '@/ui/cn'

/**
 * The account, behind one icon.
 *
 * It is the same control signed in or out — signed out it offers the way in,
 * signed in it carries who you are and the way out. One place to look for
 * "me", which is what a header full of competing text links stops being.
 */
export function ProfileMenu({ className }: { className?: string }) {
  const { t } = useTranslation()
  const { data: user, isPending } = useSession()
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

  if (isPending) {
    return <span aria-hidden className="size-9 animate-pulse rounded-full bg-surface-inset" />
  }

  const close = () => setOpen(false)

  return (
    <div ref={container} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={t('header.account')}
        className={cn(
          'flex size-9 items-center justify-center rounded-full border transition-colors duration-(--duration-fast)',
          user
            ? 'border-transparent bg-primary text-primary-fg'
            : 'border-border bg-surface text-fg-muted hover:border-border-strong hover:text-fg',
        )}
      >
        {user ? <Initials name={user.full_name} /> : <PersonGlyph />}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute end-0 top-full z-30 mt-2 w-60 overflow-hidden rounded-md border border-border bg-surface shadow-lg"
        >
          {user ? <SignedIn user={user} onNavigate={close} /> : <SignedOut onNavigate={close} />}

          {user && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                close()
                logout.mutate()
              }}
              className="block w-full border-t border-border px-4 py-2.5 text-start text-sm text-danger hover:bg-danger-soft"
            >
              {t('common.signOut')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function SignedIn({ user, onNavigate }: { user: Me; onNavigate: () => void }) {
  const { t } = useTranslation()
  const accountPath = `${user.home_path.split('/').slice(0, 2).join('/')}/account`

  return (
    <>
      <div className="border-b border-border px-4 py-3">
        <p className="truncate text-sm font-semibold text-fg">{user.full_name}</p>
        <p className="numeric mt-0.5 text-xs text-fg-subtle">{user.phone}</p>
        <p className="mt-1.5 text-xs font-medium text-primary">{t(`roles.${user.role}`)}</p>
      </div>
      <Item to={user.home_path} onNavigate={onNavigate}>
        {t('nav.dashboard')}
      </Item>
      <Item to={accountPath} onNavigate={onNavigate}>
        {t('nav.account')}
      </Item>
    </>
  )
}

function SignedOut({ onNavigate }: { onNavigate: () => void }) {
  const { t } = useTranslation()

  return (
    <>
      <div className="border-b border-border px-4 py-3">
        <p className="text-sm font-semibold text-fg">{t('header.welcome')}</p>
      </div>
      <Item to="/login" onNavigate={onNavigate}>
        {t('common.signIn')}
      </Item>
      <Item to="/register" onNavigate={onNavigate}>
        {t('common.signUp')}
      </Item>
      <div className="border-t border-border">
        <Item to="/register" onNavigate={onNavigate}>
          {t('landing.ctaProvider')}
        </Item>
      </div>
    </>
  )
}

function Item({
  to,
  onNavigate,
  children,
}: {
  to: string
  onNavigate: () => void
  children: ReactNode
}) {
  return (
    <Link
      to={to}
      role="menuitem"
      onClick={onNavigate}
      className="block px-4 py-2.5 text-sm text-fg hover:bg-surface-2"
    >
      {children}
    </Link>
  )
}

function Initials({ name }: { name: string }) {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()

  return <span className="text-xs font-bold">{initials || '?'}</span>
}

function PersonGlyph() {
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
      <circle cx="12" cy="8.5" r="3.8" />
      <path d="M4.8 20c1.2-4.3 3.9-6.5 7.2-6.5s6 2.2 7.2 6.5" />
    </svg>
  )
}
