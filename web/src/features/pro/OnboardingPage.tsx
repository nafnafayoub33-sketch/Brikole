import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'

import { useSession } from '@/data/auth'
import { useCities, useTrades } from '@/data/catalog'
import { useMyProfile, useSubmitApplication } from '@/data/pro'
import { localisedName } from '@/data/types'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { Field } from '@/ui/Field'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { PhotoGallery, PhotoInput, type PickedPhoto } from '@/ui/PhotoInput'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

const STEPS = 4
const MAX_TRADES = 5
const MAX_PHOTOS = 10
const MIN_BIO = 20

/**
 * M1 — the application.
 *
 * Four steps, and beside them a live preview of the card a client will see.
 * Filling in a profile without seeing what it produces is how people end up
 * writing "plombier" in a field labelled "your service in one line".
 */
export function OnboardingPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const { data: user } = useSession()
  const trades = useTrades()
  const cities = useCities()
  const existing = useMyProfile()
  const submit = useSubmitApplication()
  const message = useErrorMessage()

  const [step, setStep] = useState(1)
  const [tradeIds, setTradeIds] = useState<number[]>([])
  const [cityId, setCityId] = useState<number | null>(null)
  const [radiusKm, setRadiusKm] = useState(10)
  const [headline, setHeadline] = useState('')
  const [bio, setBio] = useState('')
  const [years, setYears] = useState('')
  const [priceDh, setPriceDh] = useState('')
  const [avatar, setAvatar] = useState<PickedPhoto | null>(null)
  const [idCard, setIdCard] = useState<PickedPhoto | null>(null)
  const [photos, setPhotos] = useState<PickedPhoto[]>([])

  const tradeList = trades.data ?? []
  const cityList = cities.data ?? []
  const city = cityList.find((item) => item.id === cityId) ?? null
  // A filter over sixteen items does not need memoising, and memoising it
  // over a list that is a new array each render would not help anyway.
  const pickedTrades = tradeList.filter((trade) => tradeIds.includes(trade.id))

  const complete: Record<number, boolean> = {
    1: tradeIds.length > 0,
    2: cityId !== null && radiusKm >= 1,
    3:
      headline.trim().length > 0 &&
      bio.trim().length >= MIN_BIO &&
      years !== '' &&
      idCard !== null,
    4: true,
  }

  function send() {
    submit.mutate(
      {
        trade_ids: tradeIds,
        city_id: cityId as number,
        radius_km: radiusKm,
        headline: headline.trim(),
        bio: bio.trim(),
        years_experience: Number(years) || 0,
        starting_price_centimes: priceDh === '' ? null : Math.round(Number(priceDh) * 100),
        avatar_path: avatar?.path ?? null,
        id_card_path: idCard?.path ?? null,
        photo_paths: photos.map((photo) => photo.path),
      },
      { onSuccess: () => navigate('/pro/status') },
    )
  }

  if (existing.isPending || trades.isPending || cities.isPending) {
    return (
      <div className="mx-auto max-w-5xl px-5 py-10">
        <Skeleton className="h-96" />
      </div>
    )
  }

  // An approved tradesman edits at M8; resubmitting would take him out of the
  // grid he was let into.
  if (existing.data && existing.data.status === 'approved') {
    return <Navigate to="/pro" replace />
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-10">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('onboarding.title')}</h1>
      <p className="mt-2 max-w-2xl text-fg-muted">{t('onboarding.subtitle')}</p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_320px]">
        <div>
          <Progress step={step} />

          <Card className="mt-6">
            {step === 1 && (
              <Step title={t('onboarding.step1')} body={t('onboarding.step1Body')}>
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {tradeList.map((trade) => {
                    const picked = tradeIds.includes(trade.id)
                    const full = tradeIds.length >= MAX_TRADES && !picked
                    return (
                      <li key={trade.id}>
                        <button
                          type="button"
                          aria-pressed={picked}
                          disabled={full}
                          onClick={() =>
                            setTradeIds((current) =>
                              picked
                                ? current.filter((id) => id !== trade.id)
                                : [...current, trade.id],
                            )
                          }
                          className={cn(
                            'flex w-full flex-col items-start gap-2 rounded-md border-2 p-3 text-start',
                            'transition-colors duration-(--duration-fast)',
                            picked
                              ? 'border-primary bg-primary-soft'
                              : 'border-border bg-surface hover:border-border-strong',
                            full && 'cursor-not-allowed opacity-40',
                          )}
                        >
                          <TradeIcon
                            name={trade.icon}
                            className={cn('size-6', picked ? 'text-primary' : 'text-fg-muted')}
                          />
                          <span className="text-sm font-medium text-fg">
                            {localisedName(trade, language)}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
                <p className="mt-4 text-xs text-fg-subtle">
                  {t('onboarding.tradesPicked', { count: tradeIds.length })}
                </p>
              </Step>
            )}

            {step === 2 && (
              <Step title={t('onboarding.step2')} body={t('onboarding.step2Body')}>
                <div className="flex flex-col gap-6">
                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-semibold text-fg">
                      {t('onboarding.city')}
                    </span>
                    <select
                      aria-label={t('onboarding.city')}
                      value={cityId ?? ''}
                      onChange={(event) => setCityId(Number(event.target.value) || null)}
                      className="min-h-12 rounded-md border border-border-strong bg-surface px-3.5 text-fg outline-none focus:border-primary"
                    >
                      <option value="">—</option>
                      {cityList.map((item) => (
                        <option key={item.id} value={item.id}>
                          {localisedName(item, language)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex flex-col gap-2">
                    <span className="flex items-baseline justify-between text-sm font-semibold text-fg">
                      {t('onboarding.radius')}
                      <span className="numeric text-primary">
                        {t('profile.km', { count: radiusKm })}
                      </span>
                    </span>
                    <input
                      type="range"
                      aria-label={t('onboarding.radius')}
                      min={1}
                      max={100}
                      value={radiusKm}
                      onChange={(event) => setRadiusKm(Number(event.target.value))}
                      className="accent-primary"
                    />
                    <span className="text-xs text-fg-subtle">{t('onboarding.radiusHint')}</span>
                  </label>
                </div>
              </Step>
            )}

            {step === 3 && (
              <Step title={t('onboarding.step3')} body={t('onboarding.step3Body')}>
                <div className="flex flex-col gap-6">
                  <Field
                    label={t('onboarding.headline')}
                    placeholder={t('onboarding.headlinePlaceholder')}
                    value={headline}
                    onChange={(event) => setHeadline(event.target.value)}
                    maxLength={160}
                  />

                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-semibold text-fg">{t('onboarding.bio')}</span>
                    <textarea
                      value={bio}
                      onChange={(event) => setBio(event.target.value)}
                      placeholder={t('onboarding.bioPlaceholder')}
                      rows={5}
                      maxLength={2000}
                      className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
                    />
                    <span className="text-xs text-fg-subtle">{t('onboarding.bioHint')}</span>
                  </label>

                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field
                      label={t('onboarding.years')}
                      type="number"
                      numeric
                      min={0}
                      max={70}
                      value={years}
                      onChange={(event) => setYears(event.target.value)}
                    />
                    <Field
                      label={t('onboarding.price')}
                      hint={t('onboarding.priceHint')}
                      type="number"
                      numeric
                      min={0}
                      prefix={t('onboarding.priceUnit')}
                      value={priceDh}
                      onChange={(event) => setPriceDh(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-6 sm:grid-cols-2">
                    <PhotoInput
                      round
                      label={t('onboarding.avatar')}
                      hint={t('onboarding.avatarHint')}
                      purpose="avatar"
                      value={avatar}
                      onChange={setAvatar}
                    />
                    <PhotoInput
                      label={t('onboarding.idCard')}
                      hint={t('onboarding.idCardHint')}
                      note={t('onboarding.idCardPrivate')}
                      purpose="id_card"
                      value={idCard}
                      onChange={setIdCard}
                    />
                  </div>
                </div>
              </Step>
            )}

            {step === 4 && (
              <Step title={t('onboarding.step4')} body={t('onboarding.step4Body')}>
                <PhotoGallery
                  label={t('onboarding.portfolio')}
                  hint={t('onboarding.portfolioHint')}
                  value={photos}
                  onChange={setPhotos}
                  max={MAX_PHOTOS}
                />
                {submit.isError && (
                  <div className="mt-6">
                    <Alert tone="danger">{message(submit.error)}</Alert>
                  </div>
                )}
              </Step>
            )}

            <div className="mt-8 flex items-center justify-between gap-3 border-t border-border pt-6">
              <Button
                variant="ghost"
                onClick={() => setStep((value) => value - 1)}
                disabled={step === 1}
              >
                {t('onboarding.back')}
              </Button>

              {step < STEPS ? (
                <Button
                  size="pro"
                  onClick={() => setStep((value) => value + 1)}
                  disabled={!complete[step]}
                >
                  {t('onboarding.next')}
                </Button>
              ) : (
                <Button size="pro" onClick={send} loading={submit.isPending}>
                  {t('onboarding.submit')}
                </Button>
              )}
            </div>
          </Card>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <p className="mb-3 text-sm font-semibold text-fg">{t('onboarding.preview')}</p>
          <Card className="flex flex-col items-center gap-3 text-center">
            {avatar ? (
              <img src={avatar.preview} alt="" className="size-20 rounded-full object-cover" />
            ) : (
              <span className="flex size-20 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-fg">
                {initials(user?.full_name ?? '')}
              </span>
            )}

            <div>
              <p dir="auto" className="text-lg font-bold text-fg">
                {user?.full_name ?? '—'}
              </p>
              <p className="mt-0.5 text-sm text-fg-muted">
                {city ? localisedName(city, language) : '—'}
              </p>
            </div>

            {headline && (
              <p dir="auto" className="text-sm text-fg-muted">
                {headline}
              </p>
            )}

            <dl className="mt-1 w-full divide-y divide-border text-sm">
              <Row label={t('profile.city')} value={city ? localisedName(city, language) : '—'} />
              <Row
                label={t('profile.experience')}
                value={years === '' ? '—' : t('profile.years', { count: Number(years) })}
              />
              <Row label={t('profile.radius')} value={t('profile.km', { count: radiusKm })} />
              <Row
                label={t('provider.startingAt')}
                value={
                  priceDh === ''
                    ? t('provider.onQuote')
                    : formatDirhams(Math.round(Number(priceDh) * 100), language)
                }
              />
            </dl>

            {pickedTrades.length > 0 && (
              <ul className="flex flex-wrap justify-center gap-1.5 pt-1">
                {pickedTrades.map((trade) => (
                  <li
                    key={trade.id}
                    className="rounded-pill bg-primary-soft px-2.5 py-1 text-xs font-medium text-primary"
                  >
                    {localisedName(trade, language)}
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <p className="mt-2 text-xs text-fg-subtle">{t('onboarding.previewHint')}</p>
        </aside>
      </div>
    </div>
  )
}

function Step({
  title,
  body,
  children,
}: {
  title: string
  body: string
  children: React.ReactNode
}) {
  return (
    <div>
      <h2 className="text-lg font-bold text-fg">{title}</h2>
      <p className="mt-1 mb-6 text-sm text-fg-muted">{body}</p>
      {children}
    </div>
  )
}

function Progress({ step }: { step: number }) {
  const { t } = useTranslation()
  const labels = [
    t('onboarding.step1'),
    t('onboarding.step2'),
    t('onboarding.step3'),
    t('onboarding.step4'),
  ]

  return (
    <div>
      <p className="numeric mb-3 text-xs font-semibold text-fg-subtle">
        {t('onboarding.stepOf', { step, total: STEPS })}
      </p>
      <ol className="flex gap-2">
        {labels.map((label, index) => (
          <li key={label} className="flex-1">
            <span
              className={cn(
                'block h-1.5 rounded-pill',
                index + 1 <= step ? 'bg-primary' : 'bg-surface-inset',
              )}
            />
            <span
              className={cn(
                'mt-2 block truncate text-xs',
                index + 1 === step ? 'font-semibold text-fg' : 'text-fg-subtle',
              )}
            >
              {label}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <dt className="text-fg-subtle">{label}</dt>
      <dd className="font-medium text-fg">{value}</dd>
    </div>
  )
}

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0] ?? '')
      .join('')
      .toUpperCase() || '?'
  )
}
