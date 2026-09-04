import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet } from 'react-router-dom'

import { useUnreadChats } from '@/data/chat'
import { cn } from '@/ui/cn'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ThemeToggle } from '@/ui/ThemeToggle'
import { ProfileMenu } from '@/ui/ProfileMenu'

export interface NavItem {
  to: string
  labelKey: string
  end?: boolean
  /** Marks the item that owns the chats, so it can carry the unread count.
   *  Only one item per role has it, and the roles without one never ask. */
  chats?: boolean
}

/**
 * The shell for every signed-in role. The nav differs, the chrome does not.
 */
export function AppLayout({ items }: { items: NavItem[] }) {
  const { t } = useTranslation()

  // A moderator has no conversations, so his shell never asks for a count.
  const unread = useUnreadChats(items.some((item) => item.chats))
  const waiting = unread.data?.count ?? 0

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
                {item.chats && waiting > 0 && (
                  <span
                    className="numeric ms-1.5 inline-flex min-w-5 items-center justify-center rounded-pill bg-primary px-1.5 py-0.5 text-xs font-bold text-primary-fg"
                    aria-label={t('nav.unread', { count: waiting })}
                  >
                    {waiting}
                  </span>
                )}
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
