import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'

import { SESSION_KEY, useLogout } from '@/data/auth'
import { usePlatformStore } from '@/data/platform'
import { formatDate } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { Logo } from '@/ui/illustrations/Logo'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ThemeToggle } from '@/ui/ThemeToggle'

/**
 * S3 and S4 — the two answers that replace the app instead of appearing in it.
 *
 * Neither belongs to a route: a suspended account and a closed platform are
 * true of every screen at once, and routing to `/suspended` would leave the
 * person one back-button away from a shell whose every request fails. So this
 * sits above the router and swaps the whole tree.
 *
 * The api client is what notices — see `data/platform.ts`. It sees every call,
 * including the ones an anonymous visitor makes on the landing page, which no
 * screen and no session hook ever would.
 */
export function PlatformGate({ children }: { children: ReactNode }) {
  const block = usePlatformStore((state) => state.block)
  const suspension = usePlatformStore((state) => state.suspension)

  if (block === 'maintenance') return <Maintenance />
  if (block === 'suspended') return <Suspended until={suspension?.until ?? null} reason={suspension?.reason ?? null} />
  return <>{children}</>
}

/** The frame both of them wear: the logo, the two controls that still work,
 *  and one message in the middle of the screen. */
function FullScreen({ children }: { children: ReactNode }) {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-screen flex-col px-5 py-6 sm:px-10">
      <div className="flex items-center justify-between gap-4">
        <span aria-label={t('common.appName')}>
          <Logo />
        </span>
        {/* Still switchable: somebody who cannot read the message cannot act
            on it, and the theme is the reader's, not the platform's. */}
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <LanguageSelect />
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center py-10">
        <div className="w-full max-w-md text-center">{children}</div>
      </div>
    </div>
  )
}

/** S4 — A7's switch is on. */
function Maintenance() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return (
    <FullScreen>
      <h1 className="text-2xl font-bold text-fg">{t('platform.maintenanceTitle')}</h1>
      <p className="mt-3 text-fg-muted">{t('platform.maintenanceBody')}</p>

      {/* The gate reads the switch on every request, so one retry is the whole
          recovery — there is no cache to wait out. */}
      <div className="mt-8 flex justify-center">
        <Button variant="secondary" onClick={() => void queryClient.refetchQueries()}>
          {t('platform.retry')}
        </Button>
      </div>
    </FullScreen>
  )
}

/** S3 — this account is shut. */
function Suspended({ until, reason }: { until: string | null; reason: string | null }) {
  const { t, i18n } = useTranslation()
  const logout = useLogout()
  const queryClient = useQueryClient()

  return (
    <FullScreen>
      <h1 className="text-2xl font-bold text-fg">{t('platform.suspendedTitle')}</h1>

      <p className="mt-3 text-fg-muted">
        {until
          ? t('platform.suspendedUntil', {
              date: formatDate(until, i18n.language as Language),
            })
          : t('platform.suspendedForever')}
      </p>

      {/* The reason an admin typed, shown to the person it is about. A3 asks
          for it precisely so it can be read here. */}
      {reason && (
        <p className="mt-4 rounded-md border border-border bg-surface-2 px-4 py-3 text-start text-sm text-fg">
          {reason}
        </p>
      )}

      <p className="mt-4 text-sm text-fg-subtle">{t('platform.suspendedContact')}</p>

      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {/* A timed suspension lifts itself on the way in, so checking again is
            the honest first move rather than a date to wait out alone. */}
        <Button
          variant="secondary"
          onClick={() => {
            void queryClient.refetchQueries({ queryKey: SESSION_KEY })
          }}
        >
          {t('platform.retry')}
        </Button>
        <Button
          variant="ghost"
          loading={logout.isPending}
          onClick={() => logout.mutate()}
        >
          {t('account.signOut')}
        </Button>
      </div>
    </FullScreen>
  )
}
