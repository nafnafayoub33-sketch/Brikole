import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router-dom'

import { useTrades } from '@/data/catalog'
import { useCityStore } from '@/data/cityPreference'
import { localisedName } from '@/data/types'
import type { Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'

/**
 * The trades, as a strip directly under the header.
 *
 * This is the site's real navigation: somebody arrives knowing they need a
 * plumber, not knowing they need to scroll. It scrolls sideways rather than
 * wrapping, so the header keeps one height on every screen.
 */
export function CategoryBar() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const { cityId } = useCityStore()
  const trades = useTrades(cityId)

  return (
    <nav
      aria-label={t('landing.tradesTitle')}
      className="border-b border-border bg-surface"
    >
      <div className="mx-auto max-w-6xl px-5">
        <ul className="flex gap-1 overflow-x-auto py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {trades.isPending &&
            Array.from({ length: 8 }, (_, index) => (
              <li key={index} className="py-2.5">
                <span className="block h-4 w-24 animate-pulse rounded-sm bg-surface-inset" />
              </li>
            ))}

          {trades.data?.map((trade) => (
            <li key={trade.id}>
              <NavLink
                to={`/services/${trade.slug}`}
                className={({ isActive }) =>
                  cn(
                    'block whitespace-nowrap rounded-md px-3 py-2.5 text-sm font-medium',
                    'transition-colors duration-(--duration-fast)',
                    isActive
                      ? 'text-primary'
                      : 'text-fg-muted hover:bg-surface-2 hover:text-fg',
                  )
                }
              >
                {localisedName(trade, language)}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}
