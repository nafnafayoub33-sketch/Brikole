import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router-dom'

import { cn } from '@/ui/cn'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ThemeToggle } from '@/ui/ThemeToggle'
import { ProfileMenu } from '@/ui/ProfileMenu'

export interface NavItem {
  to: string
  labelKey: string
  end?: boolean
}

/**
 * The shell for every signed-in role. The nav differs, the chrome does not.
 */
export function AppLayout({ items }: { items: NavItem[] }) {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <Link to="/" className="font-semibold text-fg">
            {t('common.appName')}
          </Link>

          <nav className="flex flex-wrap items-center gap-1">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-2 text-sm font-medium transition-colors duration-(--duration-fast)',
                    isActive ? 'bg-primary-soft text-primary' : 'text-fg-muted hover:bg-surface-2',
                  )
                }
              >
                {t(item.labelKey)}
              </NavLink>
            ))}
          </nav>

          <div className="ms-auto flex items-center gap-2">
            <ThemeToggle className="hidden sm:inline-flex" />
            <LanguageSelect className="hidden md:inline-flex" />
            <ProfileMenu />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
