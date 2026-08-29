import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'

import { useSession } from '@/data/auth'
import { Button } from '@/ui/Button'
import { CategoryBar } from '@/ui/CategoryBar'
import { HeaderSearch } from '@/ui/HeaderSearch'
import { Logo, LogoMark } from '@/ui/illustrations/Logo'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ProfileMenu } from '@/ui/ProfileMenu'
import { ThemeToggle } from '@/ui/ThemeToggle'

export function PublicLayout() {
  const { t } = useTranslation()
  const { data: user } = useSession()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-5 py-3">
          <Link to="/" aria-label={t('common.appName')} className="shrink-0">
            <Logo className="hidden sm:inline-flex" />
            <LogoMark className="size-9 text-primary sm:hidden" />
          </Link>

          {/* The search sits in the header, not only in the hero: it has to be
              there on the pages a visitor lands on second and third. */}
          <HeaderSearch className="mx-1 max-w-xl flex-1" />

          <div className="flex shrink-0 items-center gap-2">
            <Link
              to="/register"
              className="hidden rounded-md px-3 py-2 text-sm font-semibold text-fg-muted transition-colors duration-(--duration-fast) hover:bg-surface-2 hover:text-fg lg:block"
            >
              {t('landing.ctaProvider')}
            </Link>
            <ThemeToggle className="hidden sm:inline-flex" />
            <LanguageSelect className="hidden md:inline-flex" />
            <ProfileMenu />
            {!user && (
              <Link to="/register" className="hidden sm:block">
                <Button size="sm">{t('common.signUp')}</Button>
              </Link>
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
