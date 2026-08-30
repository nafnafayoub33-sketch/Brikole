import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { useTrades } from '@/data/catalog'
import { useCityStore } from '@/data/cityPreference'
import { useProviders, type ProviderSort } from '@/data/providers'
import { localisedName } from '@/data/types'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { CitySelect } from '@/ui/CitySelect'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { ProviderCard, ProviderCardSkeleton } from '@/ui/ProviderCard'
import { cn } from '@/ui/cn'

const SORTS: ProviderSort[] = ['rating', 'jobs', 'price', 'newest']
const PER_PAGE = 12

/**
 * P2 — browse, and where the header search lands.
 *
 * The whole state of the screen is in the URL: the term, the trade, the sort
 * and the page. That is what makes a result shareable, bookmarkable and
 * survivable across a reload, none of which is true of a search that lives
 * only in component state.
 */
export function BrowsePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const { slug } = useParams<{ slug?: string }>()
  const [params, setParams] = useSearchParams()

  const { cityId } = useCityStore()
  const trades = useTrades(cityId)

  const query = params.get('q')?.trim() ?? ''
  const sort = (SORTS.find((option) => option === params.get('sort')) ?? 'rating') as ProviderSort
  const page = Math.max(1, Number(params.get('page') ?? 1) || 1)

  const trade = slug ? trades.data?.find((item) => item.slug === slug) : undefined
  // While the trades are still loading we do not yet know the trade's id, and
  // asking without it would show every trade for a moment.
  const waitingForTrade = Boolean(slug) && trades.isPending

  const providers = useProviders({
    query: query || null,
    tradeId: trade?.id ?? null,
    cityId,
    sort,
    page,
    perPage: PER_PAGE,
    enabled: !waitingForTrade,
  })

  const title = query
    ? t('browse.resultsFor', { query })
    : trade
      ? localisedName(trade, language)
      : t('browse.allTitle')

  const total = providers.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PER_PAGE))

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key)
      else next.set(key, value)
    }
    // Any change to the query resets the page: page 4 of a different search is
    // not a place anybody meant to be.
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  const pending = providers.isPending || waitingForTrade

  return (
    <div className="mx-auto max-w-6xl px-5 py-10">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{title}</h1>

      <div className="mt-5 flex flex-wrap items-center gap-3 border-b border-border pb-5">
        <CitySelect className="w-full sm:w-52" />

        <label className="relative inline-flex items-center rounded-md border border-border-strong bg-surface">
          <span className="ps-3.5 text-xs font-medium text-fg-subtle">{t('browse.sort')}</span>
          <select
            value={sort}
            onChange={(event) => update({ sort: event.target.value })}
            className="min-h-12 cursor-pointer appearance-none bg-transparent ps-2 pe-8 text-sm font-medium text-fg outline-none"
          >
            <option value="rating">{t('browse.sortRating')}</option>
            <option value="jobs">{t('browse.sortJobs')}</option>
            <option value="price">{t('browse.sortPrice')}</option>
            <option value="newest">{t('browse.sortNewest')}</option>
          </select>
          <ChevronGlyph />
        </label>

        {!pending && providers.isSuccess && (
          <span className="text-sm font-medium text-fg-muted">
            {total === 1 ? t('browse.foundOne') : t('browse.found', { count: total })}
          </span>
        )}

        {query && (
          <Link
            to={slug ? `/services/${slug}` : '/services'}
            className="ms-auto text-sm font-semibold text-primary underline-offset-4 hover:underline"
          >
            {t('browse.clear')}
          </Link>
        )}
      </div>

      <div className="mt-7">
        {pending && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 8 }, (_, index) => (
              <ProviderCardSkeleton key={index} />
            ))}
          </div>
        )}

        {providers.isError && (
          <ErrorState error={providers.error} onRetry={() => void providers.refetch()} />
        )}

        {!pending && providers.isSuccess && providers.data.items.length === 0 && (
          <EmptyState
            title={t('browse.none')}
            body={t('browse.noneBody')}
            action={
              <Link to="/client/requests/new">
                <Button>{t('landing.ctaClient')}</Button>
              </Link>
            }
          />
        )}

        {!pending && providers.isSuccess && providers.data.items.length > 0 && (
          <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {providers.data.items.map((provider) => (
              <li key={provider.id}>
                <ProviderCard provider={provider} language={language} />
              </li>
            ))}
          </ul>
        )}
      </div>

      {!pending && providers.isSuccess && pages > 1 && (
        <nav
          aria-label={t('browse.pageOf', { page, pages })}
          className="mt-10 flex items-center justify-center gap-4"
        >
          <PageButton
            disabled={page <= 1}
            onClick={() => update({ page: String(page - 1) })}
            label={t('browse.previous')}
          />
          <span className="text-sm font-medium text-fg-muted">
            {t('browse.pageOf', { page, pages })}
          </span>
          <PageButton
            disabled={page >= pages}
            onClick={() => update({ page: String(page + 1) })}
            label={t('browse.next')}
          />
        </nav>
      )}
    </div>
  )
}

function PageButton({
  disabled,
  onClick,
  label,
}: {
  disabled: boolean
  onClick: () => void
  label: string
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'min-h-tap rounded-md border border-border-strong bg-surface px-4 text-sm font-semibold',
        'transition-colors duration-(--duration-fast)',
        disabled
          ? 'cursor-not-allowed text-fg-subtle opacity-50'
          : 'text-fg hover:border-primary hover:text-primary',
      )}
    >
      {label}
    </button>
  )
}

function ChevronGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="pointer-events-none absolute end-2.5 size-4 text-fg-subtle"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}
