import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'

import { useSession } from '@/data/auth'
import { Button } from '@/ui/Button'
import { CategoryBar } from '@/ui/CategoryBar'
import { Logo } from '@/ui/illustrations/Logo'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ThemeToggle } from '@/ui/ThemeToggle'
import { UserMenu } from '@/ui/UserMenu'

export function PublicLayout() {
  const { t } = useTranslation()
  const { data: user, isPending } = useSession()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-surface/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-5 py-3">
          <Link to="/" aria-label={t('common.appName')}>
            <Logo />
          </Link>

          <div className="ms-auto flex flex-wrap items-center gap-2">
            <ThemeToggle />
            <LanguageSelect />

            {/* While the session is still being restored we show neither the
                account nor the sign-in buttons: flashing "sign in" at somebody
                who is already signed in is worse than a moment of nothing. */}
            {isPending ? (
              <span aria-hidden className="h-9 w-24 animate-pulse rounded-md bg-surface-inset" />
            ) : user ? (
              <UserMenu user={user} />
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost" size="sm">
                    {t('common.signIn')}
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="sm">{t('common.signUp')}</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* The trades are the site's navigation, so they sit under the header on
          every public page rather than only on the home page. */}
      <CategoryBar />

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-surface-2">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-5 py-6">
          <Logo />
          <span className="ms-auto text-xs text-fg-subtle">{t('landing.trustNote')}</span>
        </div>
      </footer>
    </div>
  )
}
