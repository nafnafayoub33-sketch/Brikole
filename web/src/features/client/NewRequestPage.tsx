import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { useCities, useTrades } from '@/data/catalog'
import { useCreateRequest, useMyRequests, type Urgency } from '@/data/requests'
import { localisedName } from '@/data/types'
import { EMPTY_DRAFT, clearDraft, readDraft, writeDraft } from '@/features/client/draft'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { EmptyState } from '@/ui/EmptyState'
import { Field } from '@/ui/Field'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { PhotoGallery, type PickedPhoto } from '@/ui/PhotoInput'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

const STEPS = 4
const MAX_PHOTOS = 6
const MIN_DESCRIPTION = 20
const MIN_TITLE = 5
const OPEN_REQUEST_CAP = 3

const URGENCIES: Urgency[] = ['today', 'this_week', 'flexible']

/**
 * C1 — the most important screen in the product.
 *
 * Four steps, and the draft survives a closed tab: describing a job is real
 * work, and losing it to a misplaced tap is the difference between a request
 * posted and a visitor who does not come back.
 */
export function NewRequestPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const navigate = useNavigate()

  const trades = useTrades()
  const cities = useCities()
  const existing = useMyRequests()
  const create = useCreateRequest()
  const message = useErrorMessage()

  const [draft, setDraft] = useState(() => readDraft())
  const [tradeQuery, setTradeQuery] = useState('')
  const [photos, setPhotos] = useState<PickedPhoto[]>(() =>
    readDraft().photoPaths.map((path) => ({ path, preview: `/api/v1/uploads/${path}` })),
  )

  // Every keystroke, because the tab can close between any two of them.
  useEffect(() => {
    writeDraft({ ...draft, photoPaths: photos.map((photo) => photo.path) })
  }, [draft, photos])

  function set<K extends keyof typeof draft>(key: K, value: (typeof draft)[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  const openRequests = (existing.data?.items ?? []).filter((item) => item.status === 'open')
  const atCap = openRequests.length >= OPEN_REQUEST_CAP

  const tradeList = trades.data ?? []
  const cityList = cities.data ?? []
  const trade = tradeList.find((item) => item.id === draft.tradeId) ?? null
  const city = cityList.find((item) => item.id === draft.cityId) ?? null

  const matching = tradeQuery.trim()
    ? tradeList.filter((item) =>
        localisedName(item, language).toLowerCase().includes(tradeQuery.trim().toLowerCase()),
      )
    : tradeList

  const complete: Record<number, boolean> = {
    1: draft.tradeId !== null,
    2: draft.title.trim().length >= MIN_TITLE && draft.description.trim().length >= MIN_DESCRIPTION,
    3: draft.cityId !== null && draft.address.trim().length > 0,
    4: true,
  }

  function publish() {
    create.mutate(
      {
        trade_id: draft.tradeId as number,
        city_id: draft.cityId as number,
        title: draft.title.trim(),
        description: draft.description.trim(),
        address: draft.address.trim(),
        latitude: null,
        longitude: null,
        urgency: draft.urgency,
        budget_min_centimes: toCentimes(draft.budgetMin),
        budget_max_centimes: toCentimes(draft.budgetMax),
        photo_paths: photos.map((photo) => photo.path),
      },
      {
        onSuccess: (request) => {
          clearDraft()
          setDraft(EMPTY_DRAFT)
          setPhotos([])
          navigate(`/client/requests/${request.id}`)
        },
      },
    )
  }

  if (trades.isPending || cities.isPending || existing.isPending) {
    return <Skeleton className="h-96" />
  }

  // The cap is not an error to hit at the end of four steps. Say it first.
  if (atCap) {
    return (
      <EmptyState
        title={t('request.capTitle', { count: openRequests.length })}
        body={t('request.capBody')}
        action={
          <Link to="/client/requests">
            <Button>{t('request.seeRequests')}</Button>
          </Link>
        }
      />
    )
  }

  const step = Math.min(STEPS, Math.max(1, draft.step))

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('request.newTitle')}</h1>
      <p className="mt-2 text-fg-muted">{t('request.newSubtitle')}</p>

      <div className="mt-8">
        <Progress step={step} />
      </div>

      <Card className="mt-6">
        {step === 1 && (
          <Step title={t('request.step1')} body={t('request.step1Body')}>
            <Field
              label={t('request.searchTrade')}
              value={tradeQuery}
              onChange={(event) => setTradeQuery(event.target.value)}
              placeholder={t('request.searchTrade')}
            />
            <div className="mt-5">
              {matching.length === 0 ? (
                <p className="text-sm text-fg-subtle">{t('request.noTrade')}</p>
              ) : (
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {matching.map((item) => {
                    const picked = draft.tradeId === item.id
                    return (
                      <li key={item.id}>
                        <button
                          type="button"
                          aria-pressed={picked}
                          onClick={() => set('tradeId', picked ? null : item.id)}
                          className={cn(
                            'flex w-full flex-col items-start gap-2 rounded-md border-2 p-3 text-start',
                            'transition-colors duration-(--duration-fast)',
                            picked
                              ? 'border-primary bg-primary-soft'
                              : 'border-border bg-surface hover:border-border-strong',
                          )}
                        >
                          <TradeIcon
                            name={item.icon}
                            className={cn('size-6', picked ? 'text-primary' : 'text-fg-muted')}
                          />
                          <span className="text-sm font-medium text-fg">
                            {localisedName(item, language)}
                          </span>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </Step>
        )}

        {step === 2 && (
          <Step title={t('request.step2')} body={t('request.step2Body')}>
            <div className="flex flex-col gap-6">
              <Field
                label={t('request.title')}
                placeholder={t('request.titlePlaceholder')}
                value={draft.title}
                onChange={(event) => set('title', event.target.value)}
                maxLength={160}
              />

              <label className="flex flex-col gap-2">
                <span className="text-sm font-semibold text-fg">{t('request.description')}</span>
                <textarea
                  value={draft.description}
                  onChange={(event) => set('description', event.target.value)}
                  placeholder={t('request.descriptionPlaceholder')}
                  rows={5}
                  maxLength={2000}
                  className="rounded-md border border-border-strong bg-surface p-3.5 text-fg outline-none focus:border-primary placeholder:text-fg-subtle"
                />
                <span className="text-xs text-fg-subtle">{t('request.descriptionHint')}</span>
              </label>

              <PhotoGallery
                label={t('request.photos')}
                hint={t('request.photosHint')}
                value={photos}
                onChange={setPhotos}
                max={MAX_PHOTOS}
                purpose="request_photo"
              />
            </div>
          </Step>
        )}

        {step === 3 && (
          <Step title={t('request.step3')} body={t('request.step3Body')}>
            <div className="flex flex-col gap-6">
              <label className="flex flex-col gap-2">
                <span className="text-sm font-semibold text-fg">{t('request.city')}</span>
                <select
                  aria-label={t('request.city')}
                  value={draft.cityId ?? ''}
                  onChange={(event) => set('cityId', Number(event.target.value) || null)}
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

              <Field
                label={t('request.address')}
                placeholder={t('request.addressPlaceholder')}
                value={draft.address}
                onChange={(event) => set('address', event.target.value)}
                maxLength={255}
              />
              <Alert tone="info">{t('request.addressPrivate')}</Alert>

              <fieldset>
                <legend className="mb-3 text-sm font-semibold text-fg">
                  {t('request.urgency')}
                </legend>
                <div className="grid gap-3 sm:grid-cols-3">
                  {URGENCIES.map((option) => (
                    <button
                      key={option}
                      type="button"
                      aria-pressed={draft.urgency === option}
                      onClick={() => set('urgency', option)}
                      className={cn(
                        'rounded-md border-2 px-4 py-3 text-sm font-medium',
                        'transition-colors duration-(--duration-fast)',
                        draft.urgency === option
                          ? 'border-primary bg-primary-soft text-primary'
                          : 'border-border bg-surface text-fg hover:border-border-strong',
                      )}
                    >
                      {t(urgencyKey(option))}
                    </button>
                  ))}
                </div>
              </fieldset>
            </div>
          </Step>
        )}

        {step === 4 && (
          <Step title={t('request.step4')} body={t('request.step4Body')}>
            <div className="flex flex-col gap-6">
              <div>
                <p className="mb-2 text-sm font-semibold text-fg">{t('request.budget')}</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    label={t('request.budgetFrom')}
                    type="number"
                    numeric
                    min={0}
                    prefix="DH"
                    value={draft.budgetMin}
                    onChange={(event) => set('budgetMin', event.target.value)}
                  />
                  <Field
                    label={t('request.budgetTo')}
                    type="number"
                    numeric
                    min={0}
                    prefix="DH"
                    value={draft.budgetMax}
                    onChange={(event) => set('budgetMax', event.target.value)}
                  />
                </div>
                <p className="mt-2 text-xs text-fg-subtle">{t('request.budgetHint')}</p>
              </div>

              <div className="rounded-md border border-border bg-surface-2 p-5">
                <p className="mb-3 text-sm font-semibold text-fg">{t('request.review')}</p>
                <dl className="divide-y divide-border text-sm">
                  <Row label={t('request.step1')} value={trade ? localisedName(trade, language) : '—'} />
                  <Row label={t('request.title')} value={draft.title || '—'} />
                  <Row label={t('request.city')} value={city ? localisedName(city, language) : '—'} />
                  <Row label={t('request.address')} value={draft.address || '—'} />
                  <Row label={t('request.urgency')} value={t(urgencyKey(draft.urgency))} />
                  <Row
                    label={t('request.budget')}
                    value={budgetLabel(draft.budgetMin, draft.budgetMax, language)}
                  />
                  <Row label={t('request.photos')} value={String(photos.length)} numeric />
                </dl>
              </div>

              {create.isError && <Alert tone="danger">{message(create.error)}</Alert>}
            </div>
          </Step>
        )}

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-border pt-6">
          <Button variant="ghost" onClick={() => set('step', step - 1)} disabled={step === 1}>
            {t('onboarding.back')}
          </Button>

          {step < STEPS ? (
            <Button size="lg" onClick={() => set('step', step + 1)} disabled={!complete[step]}>
              {t('onboarding.next')}
            </Button>
          ) : (
            <Button size="lg" onClick={publish} loading={create.isPending}>
              {t('request.publish')}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

function urgencyKey(urgency: Urgency): string {
  return {
    today: 'request.urgencyToday',
    this_week: 'request.urgencyWeek',
    flexible: 'request.urgencyFlexible',
  }[urgency]
}

function toCentimes(value: string): number | null {
  if (value.trim() === '') return null
  const amount = Number(value)
  return Number.isFinite(amount) && amount > 0 ? Math.round(amount * 100) : null
}

function budgetLabel(min: string, max: string, language: Language): string {
  const low = toCentimes(min)
  const high = toCentimes(max)
  if (low === null && high === null) return '—'
  if (low !== null && high !== null) {
    return `${formatDirhams(low, language)} – ${formatDirhams(high, language)}`
  }
  return formatDirhams((low ?? high) as number, language)
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
    t('request.step1'),
    t('request.step2'),
    t('request.step3'),
    t('request.step4'),
  ]

  return (
    <div>
      <p className="mb-3 text-xs font-semibold text-fg-subtle">
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

function Row({
  label,
  value,
  numeric = false,
}: {
  label: string
  value: string
  numeric?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <dt className="shrink-0 text-fg-subtle">{label}</dt>
      <dd dir="auto" className={cn('text-end font-medium text-fg', numeric && 'numeric')}>
        {value}
      </dd>
    </div>
  )
}
