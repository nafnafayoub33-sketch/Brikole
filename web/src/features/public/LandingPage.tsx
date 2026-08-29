import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { useCities, useTrades } from '@/data/catalog'
import { useCityStore } from '@/data/cityPreference'
import { useProviders } from '@/data/providers'
import { localisedName, type Trade } from '@/data/types'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { CitySelect } from '@/ui/CitySelect'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { HeroArt } from '@/ui/illustrations/AuthArt'
import { AvatarStack } from '@/ui/illustrations/People'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { ProviderCard, ProviderCardSkeleton } from '@/ui/ProviderCard'
import { Skeleton } from '@/ui/Skeleton'

/** P1 — the tradesmen first, because that is what a visitor came to see. */
export function LandingPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const { cityId } = useCityStore()
  const trades = useTrades(cityId)
  const cities = useCities()
  const providers = useProviders({ cityId, sort: 'rating', perPage: 8 })
  const [query, setQuery] = useState('')

  const selectedCity = cities.data?.find((city) => city.id === cityId)
  const context = selectedCity
    ? t('landing.countsInCity', { city: localisedName(selectedCity, language) })
    : t('landing.countsEverywhere')

  function search(event: FormEvent) {
    event.preventDefault()
    // The search box starts a request — C1 is where a job gets described.
    navigate('/client/requests/new')
  }

  return (
    <>
      <section className="brand-panel relative overflow-hidden">
        <div className="brand-grid absolute inset-0 opacity-50" aria-hidden />

        <div className="relative mx-auto grid max-w-6xl items-center gap-8 px-5 py-12 lg:grid-cols-[1.1fr_1fr] lg:py-16">
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

            <p className="mt-6 text-sm text-fg-on-brand-muted">{t('landing.trustNote')}</p>
          </div>

          <HeroArt
            className="hidden w-full lg:block"
            city={selectedCity ? localisedName(selectedCity, language) : undefined}
          />
        </div>
      </section>

      {/* The tradesmen themselves, immediately. A marketplace that opens on a
          grid of category tiles makes a visitor work before it shows them
          anybody they could actually hire. */}
      <section aria-labelledby="providers-heading" className="mx-auto max-w-6xl px-5 py-14">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 id="providers-heading" className="text-2xl font-bold text-fg">
            {t('landing.topProviders')}
          </h2>
          <span className="text-sm font-medium text-fg-muted">{context}</span>
          {providers.isSuccess && providers.data.total > 0 && (
            <Link
              to="/services"
              className="ms-auto text-sm font-semibold text-primary underline-offset-4 hover:underline"
            >
              {t('landing.seeAll')}
            </Link>
          )}
        </div>

        <div className="mt-6">
          {providers.isPending && (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 8 }, (_, index) => (
                <ProviderCardSkeleton key={index} />
              ))}
            </div>
          )}
          {providers.isError && (
            <ErrorState error={providers.error} onRetry={() => void providers.refetch()} />
          )}
          {providers.isSuccess && providers.data.items.length === 0 && (
            <EmptyState
              title={t('landing.noProviders')}
              body={t('landing.forProsBody')}
              action={
                <Link to="/register">
                  <Button variant="secondary">{t('landing.ctaProvider')}</Button>
                </Link>
              }
            />
          )}
          {providers.isSuccess && providers.data.items.length > 0 && (
            <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {providers.data.items.map((provider) => (
                <li key={provider.id}>
                  <ProviderCard provider={provider} language={language} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section aria-labelledby="trades-heading" className="bg-surface-2 py-14">
        <div className="mx-auto max-w-6xl px-5">
          <h2 id="trades-heading" className="text-2xl font-bold text-fg">
            {t('landing.browseByTrade')}
          </h2>

          <div className="mt-6">
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
        </div>
      </section>

      <section aria-labelledby="how-heading" className="mx-auto max-w-6xl px-5 py-16">
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
              <p className="text-sm leading-relaxed text-fg-muted">{t(`landing.${step}Body`)}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-16">
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

      <span className="mt-auto flex items-center gap-2 pt-1">
        {count === 0 ? (
          <span className="text-xs text-fg-subtle">{t('landing.noProviderHere')}</span>
        ) : (
          <>
            <AvatarStack count={Math.min(3, count)} />
            <span className="text-xs font-medium text-fg-muted">
              {count === 1 ? t('landing.providersOne') : t('landing.providersMany', { count })}
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
