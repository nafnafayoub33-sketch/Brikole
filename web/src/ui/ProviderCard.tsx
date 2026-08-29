import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { localisedName, type Provider } from '@/data/types'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'

/**
 * One tradesman, as a card.
 *
 * The order is the order somebody decides in: what he does, who he is, where,
 * how he has been rated, and only then what he starts at. The cover is drawn
 * rather than uploaded — nobody has photographed their work on day one, and a
 * grid of grey placeholders is what makes a new marketplace look abandoned.
 */

/** Deterministic, so the same tradesman always has the same cover. */
const COVERS = [
  'from-navy-700 to-navy-500',
  'from-navy-800 to-navy-600',
  'from-navy-600 to-navy-400',
  'from-navy-900 to-navy-700',
  'from-navy-500 to-navy-300',
] as const

export function ProviderCard({ provider, language }: { provider: Provider; language: Language }) {
  const { t } = useTranslation()
  const trade = provider.trades[0]
  const cover = COVERS[provider.id % COVERS.length]

  return (
    <article className="group h-full overflow-hidden rounded-lg border border-border bg-surface shadow-sm transition-all duration-(--duration-fast) hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
      <Link to={`/m3allem/${provider.id}`} className="flex h-full flex-col">
        <div
          className={cn(
            'relative flex h-32 items-center justify-center bg-gradient-to-br',
            cover,
          )}
        >
          {trade && (
            <TradeIcon name={trade.icon} className="size-16 text-white/85" />
          )}
          {/* Rare on purpose: a badge half the grid carries is decoration. */}
          {provider.jobs_done >= 40 && provider.rating_count >= 15 && provider.rating_avg >= 4.7 && (
            <span className="absolute end-3 top-3 rounded-pill bg-white/90 px-2.5 py-1 text-[11px] font-bold text-navy-800">
              {t('provider.topRated')}
            </span>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-3 p-4">
          <div className="flex items-center gap-2.5">
            <Avatar name={provider.full_name} url={provider.avatar_url} />
            <span className="min-w-0">
              <span dir="auto" className="block truncate text-sm font-semibold text-fg">
                {provider.full_name}
              </span>
              <span className="block truncate text-xs text-fg-subtle">
                {localisedName(provider.city, language)}
              </span>
            </span>
          </div>

          {provider.headline && (
            <p dir="auto" className="line-clamp-2 text-sm leading-snug text-fg-muted">
              {provider.headline}
            </p>
          )}

          <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 pt-1 text-xs">
            {provider.rating_count > 0 ? (
              <>
                <StarGlyph />
                <span className="numeric font-bold text-fg">
                  {provider.rating_avg.toFixed(1)}
                </span>
                <span className="numeric text-fg-subtle">({provider.rating_count})</span>
              </>
            ) : (
              <span className="text-fg-subtle">{t('provider.newHere')}</span>
            )}
            {provider.jobs_done > 0 && (
              <span className="text-fg-subtle">
                · {t('provider.jobsDone', { count: provider.jobs_done })}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          {trade && (
            <span className="truncate text-xs font-medium text-fg-muted">
              {localisedName(trade, language)}
            </span>
          )}
          {provider.starting_price_centimes !== null ? (
            <span className="shrink-0 text-end">
              <span className="block text-[10px] font-semibold tracking-wide text-fg-subtle uppercase">
                {t('provider.startingAt')}
              </span>
              <span className="numeric block text-sm font-bold text-fg">
                {formatDirhams(provider.starting_price_centimes, language)}
              </span>
            </span>
          ) : (
            <span className="shrink-0 text-xs font-medium text-primary">
              {t('provider.onQuote')}
            </span>
          )}
        </div>
      </Link>
    </article>
  )
}

function Avatar({ name, url }: { name: string; url: string | null }) {
  if (url) {
    return <img src={url} alt="" className="size-9 shrink-0 rounded-full object-cover" />
  }

  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()

  return (
    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-soft-strong text-xs font-bold text-primary">
      {initials || '?'}
    </span>
  )
}

function StarGlyph() {
  return (
    <svg viewBox="0 0 20 20" className="size-3.5 text-star" fill="currentColor" aria-hidden>
      <path d="M10 1.8l2.4 5 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L2.2 7.6l5.4-.8 2.4-5Z" />
    </svg>
  )
}

export function ProviderCardSkeleton() {
  return (
    <div className="h-full overflow-hidden rounded-lg border border-border bg-surface">
      <div className="h-32 animate-pulse bg-surface-inset" />
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-center gap-2.5">
          <span className="size-9 animate-pulse rounded-full bg-surface-inset" />
          <span className="h-4 w-28 animate-pulse rounded-sm bg-surface-inset" />
        </div>
        <span className="h-3.5 w-full animate-pulse rounded-sm bg-surface-inset" />
        <span className="h-3.5 w-2/3 animate-pulse rounded-sm bg-surface-inset" />
      </div>
      <div className="border-t border-border px-4 py-3">
        <span className="block h-4 w-20 animate-pulse rounded-sm bg-surface-inset" />
      </div>
    </div>
  )
}
