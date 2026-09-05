import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type {
  AdminCity,
  AdminTrade,
  CityFields,
  TradeFields,
  Usage,
} from '@/data/adminCatalog'
import {
  useCatalog,
  useCreateCity,
  useCreateTrade,
  useSetCityActive,
  useSetTradeActive,
  useUpdateCity,
  useUpdateTrade,
} from '@/data/adminCatalog'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatCount, formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { Skeleton } from '@/ui/Skeleton'
import { TradeIcon } from '@/ui/illustrations/TradeIcon'
import { cn } from '@/ui/cn'

/**
 * A6 — trades and cities.
 *
 * The screen is shaped by one fact: **nothing here is ever deleted.** A trade
 * has requests, offers, jobs and profiles hanging off it, so the only removal
 * is deactivation — it stops the trade being offered and leaves every job that
 * went through it exactly where it is. There is no delete button because there
 * is no delete endpoint.
 *
 * What each row carries instead is what points at it. "Hide a trade 41
 * tradesmen work in" is a decision; a bare switch is a click.
 */

type Tab = 'trades' | 'cities'

const BLANK_TRADE: TradeFields & { slug: string } = {
  slug: '',
  name_ar: '',
  name_fr: '',
  name_en: '',
  icon: 'tool',
  lead_fee_centimes: null,
  sort_order: 100,
}

const BLANK_CITY: CityFields & { slug: string } = {
  slug: '',
  name_ar: '',
  name_fr: '',
  name_en: '',
  latitude: 33.5731,
  longitude: -7.5898,
}

export function CatalogPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const catalog = useCatalog()

  const [tab, setTab] = useState<Tab>('trades')
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  function switchTab(next: Tab) {
    setTab(next)
    setAdding(false)
    setEditingId(null)
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('catalog.title')}</h1>
      <p className="mt-2 text-fg-muted">{t('catalog.subtitle')}</p>

      {/* Said once, at the top, because it is the rule that explains why there
          is no delete button anywhere below it. */}
      <Alert tone="info" className="mt-5">
        {t('catalog.neverDeleted')}
      </Alert>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {(['trades', 'cities'] as Tab[]).map((option) => (
            <Button
              key={option}
              size="sm"
              variant={tab === option ? 'primary' : 'secondary'}
              onClick={() => switchTab(option)}
            >
              {t(option === 'trades' ? 'catalog.trades' : 'catalog.cities')}
            </Button>
          ))}
        </div>

        <Button
          variant="secondary"
          onClick={() => {
            setAdding((open) => !open)
            setEditingId(null)
          }}
        >
          {t(tab === 'trades' ? 'catalog.newTrade' : 'catalog.newCity')}
        </Button>
      </div>

      {catalog.isPending ? (
        <div className="mt-6 flex flex-col gap-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : catalog.isError ? (
        <div className="mt-6">
          <ErrorState error={catalog.error} onRetry={() => void catalog.refetch()} />
        </div>
      ) : tab === 'trades' ? (
        <Trades
          trades={catalog.data.trades}
          language={language}
          adding={adding}
          editingId={editingId}
          onDoneAdding={() => setAdding(false)}
          onEdit={setEditingId}
        />
      ) : (
        <Cities
          cities={catalog.data.cities}
          language={language}
          adding={adding}
          editingId={editingId}
          onDoneAdding={() => setAdding(false)}
          onEdit={setEditingId}
        />
      )}
    </div>
  )
}

// -- trades -----------------------------------------------------------------

function Trades({
  trades,
  language,
  adding,
  editingId,
  onDoneAdding,
  onEdit,
}: {
  trades: AdminTrade[]
  language: Language
  adding: boolean
  editingId: number | null
  onDoneAdding: () => void
  onEdit: (id: number | null) => void
}) {
  const { t } = useTranslation()
  const create = useCreateTrade()

  return (
    <div className="mt-6 flex flex-col gap-3">
      {adding && (
        <TradeForm
          title={t('catalog.newTrade')}
          initial={BLANK_TRADE}
          withSlug
          pending={create.isPending}
          error={create.error}
          onSubmit={(fields) => create.mutate(fields, { onSuccess: onDoneAdding })}
          onCancel={onDoneAdding}
        />
      )}

      {trades.map((trade) =>
        editingId === trade.id ? (
          <EditTrade key={trade.id} trade={trade} onDone={() => onEdit(null)} />
        ) : (
          <TradeRow
            key={trade.id}
            trade={trade}
            language={language}
            onEdit={() => onEdit(trade.id)}
          />
        ),
      )}
    </div>
  )
}

function TradeRow({
  trade,
  language,
  onEdit,
}: {
  trade: AdminTrade
  language: Language
  onEdit: () => void
}) {
  const { t } = useTranslation()
  const toggle = useSetTradeActive()

  return (
    <Card className={cn(!trade.is_active && 'opacity-70')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="rounded-md bg-surface-2 p-2">
            <TradeIcon name={trade.icon} className="size-6 text-fg-muted" />
          </span>
          <div className="min-w-0">
            <p dir="auto" className="font-bold text-fg">
              {localised(trade, language)}
            </p>
            <p className="numeric text-xs text-fg-subtle">{trade.slug}</p>
          </div>
        </div>

        {trade.is_active ? (
          <Badge tone="success">{t('catalog.active')}</Badge>
        ) : (
          <Badge tone="neutral">{t('catalog.hidden')}</Badge>
        )}
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <Stat
          label={t('catalog.fee')}
          value={
            trade.lead_fee_centimes === null
              ? t('catalog.feeDefault')
              : formatDirhams(trade.lead_fee_centimes, language)
          }
        />
        <Stat label={t('catalog.sortOrder')} value={formatCount(trade.sort_order, language)} />
        <Stat
          label={t('catalog.otherNames')}
          value={otherNames(trade, language)}
          plain
        />
      </dl>

      <UsageRow usage={trade.usage} language={language} />

      <div className="mt-4 flex flex-wrap gap-3">
        <Button size="sm" variant="secondary" onClick={onEdit}>
          {t('catalog.edit')}
        </Button>
        <ToggleButton
          active={trade.is_active}
          usage={trade.usage}
          language={language}
          pending={toggle.isPending}
          onToggle={() => toggle.mutate({ id: trade.id, isActive: !trade.is_active })}
        />
      </div>
    </Card>
  )
}

function EditTrade({ trade, onDone }: { trade: AdminTrade; onDone: () => void }) {
  const { t } = useTranslation()
  const update = useUpdateTrade()

  return (
    <TradeForm
      title={t('catalog.edit')}
      initial={trade}
      pending={update.isPending}
      error={update.error}
      onSubmit={(fields) =>
        update.mutate({ id: trade.id, ...fields }, { onSuccess: onDone })
      }
      onCancel={onDone}
    />
  )
}

function TradeForm({
  title,
  initial,
  withSlug = false,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  title: string
  initial: TradeFields & { slug: string }
  withSlug?: boolean
  pending: boolean
  error: unknown
  onSubmit: (fields: TradeFields & { slug: string }) => void
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()

  const [slug, setSlug] = useState(initial.slug)
  const [names, setNames] = useState({
    name_ar: initial.name_ar,
    name_fr: initial.name_fr,
    name_en: initial.name_en,
  })
  const [icon, setIcon] = useState(initial.icon)
  const [fee, setFee] = useState(
    initial.lead_fee_centimes === null ? '' : String(initial.lead_fee_centimes / 100),
  )
  const [order, setOrder] = useState(String(initial.sort_order))

  const complete =
    (!withSlug || slug.trim().length > 0) &&
    Object.values(names).every((value) => value.trim().length > 0)

  return (
    <Card>
      <h2 className="text-lg font-bold text-fg">{title}</h2>

      {Boolean(error) && (
        <Alert tone="danger" className="mt-4">
          {message(error)}
        </Alert>
      )}

      <div className="mt-5 flex flex-col gap-5">
        {withSlug ? (
          <Field
            label={t('catalog.slug')}
            hint={t('catalog.slugHint')}
            value={slug}
            maxLength={64}
            onChange={(event) => setSlug(event.target.value)}
          />
        ) : (
          <div>
            <p className="text-sm font-semibold text-fg">{t('catalog.slug')}</p>
            <p className="numeric mt-1 text-sm text-fg-muted">{initial.slug}</p>
            {/* Not a disabled input: an input somebody cannot type in reads as
                broken, where a sentence reads as a reason. */}
            <p className="mt-1 text-xs text-fg-subtle">{t('catalog.slugLocked')}</p>
          </div>
        )}

        <Names names={names} onChange={setNames} />

        <Field
          label={t('catalog.icon')}
          hint={t('catalog.iconHint')}
          value={icon}
          maxLength={64}
          onChange={(event) => setIcon(event.target.value)}
        />

        <Field
          label={t('catalog.fee')}
          hint={t('catalog.feeHint')}
          type="number"
          numeric
          prefix="DH"
          value={fee}
          onChange={(event) => setFee(event.target.value)}
        />

        <Field
          label={t('catalog.sortOrder')}
          hint={t('catalog.sortOrderHint')}
          type="number"
          numeric
          value={order}
          onChange={(event) => setOrder(event.target.value)}
        />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button
          loading={pending}
          disabled={!complete}
          onClick={() =>
            onSubmit({
              slug: slug.trim(),
              ...names,
              icon: icon.trim(),
              // An empty box means "use the platform default", which is what
              // null means on the wire. Zero would mean free.
              lead_fee_centimes: fee.trim() ? Math.round(Number(fee) * 100) : null,
              sort_order: Number(order) || 0,
            })
          }
        >
          {t('catalog.save')}
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          {t('catalog.cancel')}
        </Button>
      </div>
    </Card>
  )
}

// -- cities -----------------------------------------------------------------

function Cities({
  cities,
  language,
  adding,
  editingId,
  onDoneAdding,
  onEdit,
}: {
  cities: AdminCity[]
  language: Language
  adding: boolean
  editingId: number | null
  onDoneAdding: () => void
  onEdit: (id: number | null) => void
}) {
  const { t } = useTranslation()
  const create = useCreateCity()

  return (
    <div className="mt-6 flex flex-col gap-3">
      {adding && (
        <CityForm
          title={t('catalog.newCity')}
          initial={BLANK_CITY}
          withSlug
          pending={create.isPending}
          error={create.error}
          onSubmit={(fields) => create.mutate(fields, { onSuccess: onDoneAdding })}
          onCancel={onDoneAdding}
        />
      )}

      {cities.map((city) =>
        editingId === city.id ? (
          <EditCity key={city.id} city={city} onDone={() => onEdit(null)} />
        ) : (
          <CityRow
            key={city.id}
            city={city}
            language={language}
            onEdit={() => onEdit(city.id)}
          />
        ),
      )}
    </div>
  )
}

function CityRow({
  city,
  language,
  onEdit,
}: {
  city: AdminCity
  language: Language
  onEdit: () => void
}) {
  const { t } = useTranslation()
  const toggle = useSetCityActive()

  return (
    <Card className={cn(!city.is_active && 'opacity-70')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p dir="auto" className="font-bold text-fg">
            {localised(city, language)}
          </p>
          <p className="numeric text-xs text-fg-subtle">{city.slug}</p>
        </div>

        {city.is_active ? (
          <Badge tone="success">{t('catalog.active')}</Badge>
        ) : (
          <Badge tone="neutral">{t('catalog.hidden')}</Badge>
        )}
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <Stat
          label={t('catalog.coordinates')}
          value={`${city.latitude.toFixed(4)}, ${city.longitude.toFixed(4)}`}
        />
        <Stat
          label={t('catalog.otherNames')}
          value={otherNames(city, language)}
          plain
        />
      </dl>

      <UsageRow usage={city.usage} language={language} />

      <div className="mt-4 flex flex-wrap gap-3">
        <Button size="sm" variant="secondary" onClick={onEdit}>
          {t('catalog.edit')}
        </Button>
        <ToggleButton
          active={city.is_active}
          usage={city.usage}
          language={language}
          pending={toggle.isPending}
          onToggle={() => toggle.mutate({ id: city.id, isActive: !city.is_active })}
        />
      </div>
    </Card>
  )
}

function EditCity({ city, onDone }: { city: AdminCity; onDone: () => void }) {
  const { t } = useTranslation()
  const update = useUpdateCity()

  return (
    <CityForm
      title={t('catalog.edit')}
      initial={city}
      pending={update.isPending}
      error={update.error}
      onSubmit={(fields) => update.mutate({ id: city.id, ...fields }, { onSuccess: onDone })}
      onCancel={onDone}
    />
  )
}

function CityForm({
  title,
  initial,
  withSlug = false,
  pending,
  error,
  onSubmit,
  onCancel,
}: {
  title: string
  initial: CityFields & { slug: string }
  withSlug?: boolean
  pending: boolean
  error: unknown
  onSubmit: (fields: CityFields & { slug: string }) => void
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()

  const [slug, setSlug] = useState(initial.slug)
  const [names, setNames] = useState({
    name_ar: initial.name_ar,
    name_fr: initial.name_fr,
    name_en: initial.name_en,
  })
  const [latitude, setLatitude] = useState(String(initial.latitude))
  const [longitude, setLongitude] = useState(String(initial.longitude))

  const complete =
    (!withSlug || slug.trim().length > 0) &&
    Object.values(names).every((value) => value.trim().length > 0) &&
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude))

  return (
    <Card>
      <h2 className="text-lg font-bold text-fg">{title}</h2>

      {Boolean(error) && (
        <Alert tone="danger" className="mt-4">
          {message(error)}
        </Alert>
      )}

      <div className="mt-5 flex flex-col gap-5">
        {withSlug ? (
          <Field
            label={t('catalog.slug')}
            hint={t('catalog.slugHint')}
            value={slug}
            maxLength={64}
            onChange={(event) => setSlug(event.target.value)}
          />
        ) : (
          <div>
            <p className="text-sm font-semibold text-fg">{t('catalog.slug')}</p>
            <p className="numeric mt-1 text-sm text-fg-muted">{initial.slug}</p>
            <p className="mt-1 text-xs text-fg-subtle">{t('catalog.slugLocked')}</p>
          </div>
        )}

        <Names names={names} onChange={setNames} />

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label={t('catalog.latitude')}
            type="number"
            numeric
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
          />
          <Field
            label={t('catalog.longitude')}
            type="number"
            numeric
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
          />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button
          loading={pending}
          disabled={!complete}
          onClick={() =>
            onSubmit({
              slug: slug.trim(),
              ...names,
              latitude: Number(latitude),
              longitude: Number(longitude),
            })
          }
        >
          {t('catalog.save')}
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          {t('catalog.cancel')}
        </Button>
      </div>
    </Card>
  )
}

// -- shared -----------------------------------------------------------------

/** All three, always. A trade with no Arabic name is a blank row to this
 *  product's default audience. */
function Names({
  names,
  onChange,
}: {
  names: { name_ar: string; name_fr: string; name_en: string }
  onChange: (next: { name_ar: string; name_fr: string; name_en: string }) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col gap-5">
      {(['name_ar', 'name_fr', 'name_en'] as const).map((field) => (
        <Field
          key={field}
          label={t(`catalog.${field}`)}
          value={names[field]}
          maxLength={120}
          dir="auto"
          onChange={(event) => onChange({ ...names, [field]: event.target.value })}
        />
      ))}
    </div>
  )
}

/**
 * The switch, with what it would hide standing next to it.
 *
 * Turning something *on* asks nothing — it adds an option and breaks nothing.
 * Turning it off is the one that needs the question, and the question carries
 * the counts.
 */
function ToggleButton({
  active,
  usage,
  language,
  pending,
  onToggle,
}: {
  active: boolean
  usage: Usage
  language: Language
  pending: boolean
  onToggle: () => void
}) {
  const { t } = useTranslation()

  if (!active) {
    return (
      <Button size="sm" variant="secondary" loading={pending} onClick={onToggle}>
        {t('catalog.turnOn')}
      </Button>
    )
  }

  return (
    <ConfirmButton
      size="sm"
      variant="secondary"
      tone="danger"
      label={t('catalog.turnOff')}
      question={t('catalog.turnOffConfirm', {
        providers: formatCount(usage.providers, language),
        requests: formatCount(usage.requests, language),
      })}
      confirmLabel={t('catalog.turnOffYes')}
      loading={pending}
      onConfirm={onToggle}
    />
  )
}

function UsageRow({ usage, language }: { usage: Usage; language: Language }) {
  const { t } = useTranslation()

  return (
    <p className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-subtle">
      <span>
        {t('catalog.usageProviders')}:{' '}
        <span className="numeric font-semibold text-fg-muted">
          {formatCount(usage.providers, language)}
        </span>
      </span>
      <span>
        {t('catalog.usageRequests')}:{' '}
        <span className="numeric font-semibold text-fg-muted">
          {formatCount(usage.requests, language)}
        </span>
      </span>
      <span>
        {t('catalog.usageJobs')}:{' '}
        <span className="numeric font-semibold text-fg-muted">
          {formatCount(usage.jobs, language)}
        </span>
      </span>
    </p>
  )
}

function Stat({
  label,
  value,
  plain = false,
}: {
  label: string
  value: string
  plain?: boolean
}) {
  return (
    <div>
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd dir="auto" className="mt-0.5 text-sm font-medium text-fg">
        {plain ? value : <span className="numeric">{value}</span>}
      </dd>
    </div>
  )
}

interface Named {
  name_ar: string
  name_fr: string
  name_en: string
}

function localised(row: Named, language: Language): string {
  return language === 'fr' ? row.name_fr : language === 'en' ? row.name_en : row.name_ar
}

/** The two the reader is not looking at, so a missing translation is visible
 *  from the list rather than only from the form. */
function otherNames(row: Named, language: Language): string {
  const all: [Language, string][] = [
    ['ar', row.name_ar],
    ['fr', row.name_fr],
    ['en', row.name_en],
  ]
  return all
    .filter(([code]) => code !== language)
    .map(([, name]) => name)
    .join(' · ')
}
