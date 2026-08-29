import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { useSession } from '@/data/auth'
import type { Role } from '@/data/types'

/**
 * The route gate.
 *
 * It decides what to *show*. It is not the security boundary — the API is, and
 * every endpoint declares the role it needs. Someone who edits this component
 * in their browser gets to look at an empty admin shell whose every request
 * comes back 403.
 */
export function RequireRole({ allow, children }: { allow: Role[]; children: ReactNode }) {
  const { data: user, isPending } = useSession()
  const location = useLocation()

  if (isPending) return <FullPageLoading />

  if (!user) {
    // Remember where they were headed so sign-in can finish the journey.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (!allow.includes(user.role)) return <Forbidden role={user.role} home={user.home_path} />

  return <>{children}</>
}

export function FullPageLoading() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-screen items-center justify-center">
      <span className="sr-only">{t('common.loading')}</span>
      <span
        aria-hidden
        className="size-6 animate-spin rounded-full border-2 border-border-strong border-t-primary"
      />
    </div>
  )
}

/** S2 — never a blank page, always a way back to where they belong. */
function Forbidden({ role, home }: { role: Role; home: string }) {
  const { t } = useTranslation()
  return (
    <div className="mx-auto flex max-w-prose flex-col items-center gap-3 px-6 py-20 text-center">
      <h1 className="text-xl font-semibold text-fg">{t('forbidden.title')}</h1>
      <p className="text-sm text-fg-muted">{t('forbidden.body', { role: t(`roles.${role}`) })}</p>
      <Link
        to={home}
        className="mt-2 inline-flex min-h-tap items-center rounded-md border border-border-strong bg-surface px-4 text-sm font-medium text-fg hover:bg-surface-2"
      >
        {t('forbidden.cta')}
      </Link>
    </div>
  )
}
