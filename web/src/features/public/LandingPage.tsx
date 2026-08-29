import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { useCities, useTrades } from '@/data/catalog'
import { useCityStore } from '@/data/cityPreference'
import { localisedName, type Trade } from '@/data/types'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { CitySelect } from '@/ui/CitySelect'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { HeroArt } from '@/ui/illustrations/AuthArt'
import { AvatarStack } from '@/ui/illustrations/People'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { Skeleton } from '@/ui/Skeleton'

/** P1 — explain the thing in five seconds, and start a request. */
export function LandingPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const { cityId } = useCityStore()
  const trades = useTrades(cityId)
  const cities = useCities()
  const [query, setQuery] = useState('')

  const cityName = cities.data?.find((city) => city.id === cityId)
  const context = cityName
    ? t('landing.countsInCity', { city: localisedName(cityName, language) })
    : t('landing.countsEverywhere')

  function search(event: FormEvent) {
    event.preventDefault()
    // The search box starts a request — C1 is where a job gets described.
    navigate('/client/requests/new')
  }

  // Busiest first, so the chips are the trades somebody can actually be served
  // in, in the city they picked.
  const popular = [...(trades.data ?? [])]
    .sort((a, b) => b.providers_count - a.providers_count)
    .slice(0, 4)

  return (
    <>
      <section className="brand-panel relative overflow-hidden">
        <div className="brand-grid absolute inset-0 opacity-50" aria-hidden />

        <div className="relative mx-auto grid max-w-6xl items-center gap-8 px-5 py-14 lg:grid-cols-[1.1fr_1fr] lg:py-20">
          <div>
            <h1 className="text-4xl leading-tight font-bold text-white sm:text-5xl">
              {t('landing.title')}
            </h1>
            <p className="mt-4 max-w-xl text-lg text-fg-on-brand-muted">
              {t('landing.subtitle')}
            </p>

            <form
              onSubmit={search}
              className="mt-8 flex flex-col gap-2 rounded-lg bg-white/10 p-2 backdrop-blur sm:flex-row sm:items-center"
            >
              <label htmlFor="hero-search" className="sr-only">
                {t('landing.searchPlaceholder')}
              </label>
              <div className="flex min-w-0 flex-[2] items-center gap-2.5 rounded-md bg-white px-4">
                <SearchGlyph />
                <input
                  id="hero-search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={t('landing.searchPlaceholder')}
                  className="min-h-12 w-full bg-transparent text-navy-900 outline-none placeholder:text-fg-subtle"
                />
              </div>
              <CitySelect onBrand className="sm:w-44 sm:flex-none" />
              <Button type="submit" variant="onBrand" size="lg">
                {t('landing.searchCta')}
              </Button>
            </form>

            {popular.length > 0 && (
              <div className="mt-5 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-fg-on-brand-muted">
                  {t('landing.popular')}
                </span>
                {popular.map((trade) => (
                  <Link
                    key={trade.id}
                    to={`/services/${trade.slug}`}
                    className="rounded-pill border border-white/25 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-(--duration-fast) hover:bg-white/15"
                  >
                    {localisedName(trade, language)}
                  </Link>
                ))}
              </div>
            )}

            <p className="mt-6 text-sm text-fg-on-brand-muted">{t('landing.trustNote')}</p>
          </div>

          <HeroArt
            className="hidden w-full lg:block"
            city={cityName ? localisedName(cityName, language) : undefined}
          />
        </div>
      </section>

      <section aria-labelledby="trades-heading" className="mx-auto max-w-6xl px-5 py-16">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 id="trades-heading" className="text-2xl font-bold text-fg">
            {t('landing.tradesTitle')}
          </h2>
          <span className="text-sm font-medium text-fg-muted">{context}</span>
        </div>

        <div className="mt-6">
          {/* The four states every list owes the reader. */}
          {trades.isPending && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 8 }, (_, index) => (
                <Skeleton key={index} className="h-36" />
              ))}
            </div>
          )}
          {trades.isError && (
            <ErrorState error={trades.error} onRetry={() => void trades.refetch()} />
          )}
          {trades.isSuccess && trades.data.length === 0 && (
            <EmptyState title={t('landing.tradesEmpty')} />
          )}
          {trades.isSuccess && trades.data.length > 0 && (
            <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {trades.data.map((trade) => (
                <li key={trade.id}>
                  <TradeCard trade={trade} language={language} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section aria-labelledby="how-heading" className="bg-surface-2 py-16">
        <div className="mx-auto max-w-6xl px-5">
          <h2 id="how-heading" className="text-2xl font-bold text-fg">
            {t('landing.howTitle')}
          </h2>
          <ol className="mt-8 grid gap-8 sm:grid-cols-3">
            {(['how1', 'how2', 'how3'] as const).map((step, index) => (
              <li key={step} className="flex flex-col gap-3">
                <span className="numeric flex size-11 items-center justify-center rounded-md bg-primary text-base font-bold text-primary-fg shadow-brand">
                  {index + 1}
                </span>
                <h3 className="text-lg font-semibold text-fg">{t(`landing.${step}Title`)}</h3>
                <p className="text-sm leading-relaxed text-fg-muted">
                  {t(`landing.${step}Body`)}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <div className="brand-panel relative overflow-hidden rounded-xl px-8 py-12 sm:px-12">
          <div className="brand-grid absolute inset-0 opacity-50" aria-hidden />
          <div className="relative max-w-2xl">
            <h2 className="text-2xl font-bold text-white">{t('landing.forProsTitle')}</h2>
            <p className="mt-3 text-fg-on-brand-muted">{t('landing.forProsBody')}</p>
            <Link to="/register" className="mt-7 inline-block">
              <Button variant="onBrand" size="lg">
                {t('landing.ctaProvider')}
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}

function TradeCard({ trade, language }: { trade: Trade; language: Language }) {
  const { t } = useTranslation()
  const count = trade.providers_count

  return (
    <Link
      to={`/services/${trade.slug}`}
      className="group flex h-full flex-col gap-3 rounded-lg border border-border bg-surface p-5 shadow-sm transition-all duration-(--duration-fast) hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
    >
      <span className="flex size-11 items-center justify-center rounded-md bg-primary-soft text-primary transition-colors duration-(--duration-fast) group-hover:bg-primary group-hover:text-primary-fg">
        <TradeIcon name={trade.icon} />
      </span>
      <span className="text-sm font-semibold text-fg">{localisedName(trade, language)}</span>

      {/* The count is the whole reason to trust the tile. Zero says so plainly
          rather than leaving the visitor to find out after writing a request. */}
      <span className="mt-auto flex items-center gap-2 pt-1">
        {count === 0 ? (
          <span className="text-xs text-fg-subtle">{t('landing.noProviderHere')}</span>
        ) : (
          <>
            <AvatarStack count={Math.min(3, count)} />
            <span className="text-xs font-medium text-fg-muted">
              {count === 1
                ? t('landing.providersOne')
                : t('landing.providersMany', { count })}
            </span>
          </>
        )}
      </span>
    </Link>
  )
}

function SearchGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-5 shrink-0 text-fg-subtle"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 4 4" />
    </svg>
  )
}
