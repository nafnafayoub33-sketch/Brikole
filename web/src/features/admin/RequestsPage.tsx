import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type {
  AdminRequest,
  AdminRequestOffer,
  AdminRequestRow,
  RequestFilters,
} from '@/data/adminRequests'
import {
  REQUESTS_PER_PAGE,
  useAdminRequest,
  useAdminRequests,
  useCancelRequest,
} from '@/data/adminRequests'
import { useCities, useTrades } from '@/data/catalog'
import type { RequestStatus } from '@/data/requests'
import { localisedName } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import {
  formatBudget,
  formatCount,
  formatDateTime,
  formatDirhams,
  formatPhone,
  formatRelative,
} from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { JobStatusBadge } from '@/ui/JobStatusBadge'
import { Pager } from '@/ui/Pager'
import { RequestStatusBadge } from '@/ui/RequestStatusBadge'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'
import { URGENCY_KEYS } from '@/ui/urgencyLabels'

/**
 * A4 — requests and jobs.
 *
 * Every question this screen answers has the same shape: somebody is on the
 * phone about a request, find it and say what happened to it. So the box takes
 * whatever the caller has to hand — an id, a title, a name, a phone spoken the
 * way people speak it — and the pane shows the whole story at once rather than
 * making an admin click through it while somebody waits.
 *
 * Read-only apart from one action, and that action is the one support actually
 * needs: closing a request somebody posted by mistake. An assigned request is
 * not cancelled here. There is a tradesman who may be on his way and a fee
 * already charged, and that is a dispute.
 */

const STATUSES: RequestStatus[] = ['open', 'assigned', 'done', 'cancelled', 'expired']

const STATUS_KEYS: Record<RequestStatus, string> = {
  open: 'requests.statusOpen',
  assigned: 'requests.statusAssigned',
  done: 'requests.statusDone',
  cancelled: 'requests.statusCancelled',
  expired: 'requests.statusExpired',
}

const OFFER_KEYS = {
  pending: 'adminRequests.offerPending',
  accepted: 'adminRequests.offerAccepted',
  rejected: 'adminRequests.offerRejected',
  withdrawn: 'adminRequests.offerWithdrawn',
  expired: 'adminRequests.offerExpired',
} as const

const EMPTY: RequestFilters = { q: '', status: '', cityId: '', tradeId: '' }

export function RequestsPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language

  const [filters, setFilters] = useState<RequestFilters>(EMPTY)
  const [pageNumber, setPageNumber] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const requests = useAdminRequests(filters, pageNumber)
  const page = requests.data

  function changeFilters(next: RequestFilters) {
    setFilters(next)
    // Page 4 of a different search is not somewhere anybody meant to be.
    setPageNumber(1)
  }

  const pages = page ? Math.max(1, Math.ceil(page.total / REQUESTS_PER_PAGE)) : 1

  // The selection follows the list: filtering a row away must not leave the
  // pane pointing at something no longer on screen.
  useEffect(() => {
    const list = page?.items ?? []
    setSelectedId((current) =>
      current !== null && list.some((row) => row.id === current)
        ? current
        : (list[0]?.id ?? null),
    )
  }, [page])

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline gap-x-3">
        <h1 className="text-2xl font-bold text-fg">{t('adminRequests.title')}</h1>
        {page && (
          <span className="text-sm font-medium text-fg-muted">
            {page.total === 1
              ? t('adminRequests.foundOne')
              : t('adminRequests.found', { value: formatCount(page.total, language) })}
          </span>
        )}
      </div>
      <p className="mb-6 text-fg-muted">{t('adminRequests.subtitle')}</p>

      <Filters filters={filters} language={language} onChange={changeFilters} />

      {requests.isPending ? (
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      ) : requests.isError ? (
        <ErrorState error={requests.error} onRetry={() => void requests.refetch()} />
      ) : requests.data.items.length === 0 ? (
        <EmptyState
          title={t('adminRequests.empty')}
          body={t('adminRequests.emptyBody')}
        />
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[340px_1fr]">
          <div className="flex flex-col gap-3 lg:sticky lg:top-6">
            {/* The list scrolls inside itself. A thousand requests down one
                page push the detail — the thing being read — off the screen. */}
            <ul className="flex max-h-[70vh] flex-col gap-2 overflow-y-auto pe-1">
              {requests.data.items.map((row) => (
                <li key={row.id}>
                  <ListRow
                    row={row}
                    language={language}
                    selected={row.id === selectedId}
                    onSelect={() => setSelectedId(row.id)}
                  />
                </li>
              ))}
            </ul>

            {pages > 1 && (
              <Pager
                page={pageNumber}
                pages={pages}
                language={language}
                onChange={setPageNumber}
              />
            )}
          </div>

          {selectedId === null ? (
            <EmptyState title={t('adminRequests.pick')} />
          ) : (
            <Detail key={selectedId} requestId={selectedId} language={language} />
          )}
        </div>
      )}
    </div>
  )
}

function Filters({
  filters,
  language,
  onChange,
}: {
  filters: RequestFilters
  language: Language
  onChange: (next: RequestFilters) => void
}) {
  const { t } = useTranslation()
  const cities = useCities()
  const trades = useTrades()

  return (
    <div className="mb-6 flex flex-wrap items-end gap-3">
      <div className="min-w-56 flex-1">
        <Field
          label={t('adminRequests.search')}
          hint={t('adminRequests.searchHint')}
          value={filters.q}
          onChange={(event) => onChange({ ...filters, q: event.target.value })}
        />
      </div>

      <Select
        label={t('adminRequests.status')}
        value={filters.status}
        onChange={(value) =>
          onChange({ ...filters, status: value as RequestStatus | '' })
        }
        options={[
          { value: '', label: t('adminRequests.anyStatus') },
          ...STATUSES.map((status) => ({ value: status, label: t(STATUS_KEYS[status]) })),
        ]}
      />

      <Select
        label={t('adminRequests.city')}
        value={String(filters.cityId)}
        onChange={(value) => onChange({ ...filters, cityId: value ? Number(value) : '' })}
        options={[
          { value: '', label: t('adminRequests.anyCity') },
          ...(cities.data ?? []).map((city) => ({
            value: String(city.id),
            label: localisedName(city, language),
          })),
        ]}
      />

      <Select
        label={t('adminRequests.trade')}
        value={String(filters.tradeId)}
        onChange={(value) => onChange({ ...filters, tradeId: value ? Number(value) : '' })}
        options={[
          { value: '', label: t('adminRequests.anyTrade') },
          ...(trades.data ?? []).map((trade) => ({
            value: String(trade.id),
            label: localisedName(trade, language),
          })),
        ]}
      />
    </div>
  )
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  return (
    <label className="flex min-w-40 flex-col gap-2">
      <span className="text-sm font-semibold text-fg">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="min-h-12 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function ListRow({
  row,
  language,
  selected,
  onSelect,
}: {
  row: AdminRequestRow
  language: Language
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full rounded-lg border p-3 text-start transition-colors duration-(--duration-fast)',
        selected
          ? 'border-primary bg-primary/5'
          : 'border-border bg-surface hover:border-fg-subtle',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span dir="auto" className="line-clamp-1 text-sm font-semibold text-fg">
          {row.title}
        </span>
        <RequestStatusBadge status={row.status} />
      </div>

      <p dir="auto" className="mt-1 line-clamp-1 text-xs text-fg-muted">
        {row.client.full_name} · {localisedName(row.city, language)}
      </p>

      <p className="mt-1 flex items-center gap-2 text-xs text-fg-subtle">
        <span className="numeric">#{row.id}</span>
        <span>{formatRelative(row.created_at, language)}</span>
        {row.offers_count > 0 && (
          <span className="numeric">
            · {t('adminRequests.offersShort', { count: row.offers_count })}
          </span>
        )}
      </p>
    </button>
  )
}

function Detail({ requestId, language }: { requestId: number; language: Language }) {
  const { t } = useTranslation()
  const request = useAdminRequest(requestId)

  if (request.isPending) return <Skeleton className="h-96" />
  if (request.isError) {
    return (
      <ErrorState error={request.error} onRetry={() => void request.refetch()} />
    )
  }

  const data = request.data

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="numeric text-xs text-fg-subtle">#{data.id}</p>
            <h2 dir="auto" className="text-xl font-bold text-fg">
              {data.title}
            </h2>
          </div>
          <RequestStatusBadge status={data.status} />
        </div>

        <p dir="auto" className="mt-3 whitespace-pre-line text-sm text-fg-muted">
          {data.description}
        </p>

        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <Row label={t('adminRequests.trade')} value={localisedName(data.trade, language)} />
          <Row label={t('adminRequests.city')} value={localisedName(data.city, language)} />
          <Row label={t('adminRequests.address')} value={data.address} />
          <Row label={t('adminRequests.urgency')} value={t(URGENCY_KEYS[data.urgency])} />
          <Row
            label={t('adminRequests.budget')}
            value={
              formatBudget(
                data.budget_min_centimes,
                data.budget_max_centimes,
                language,
              ) || t('adminRequests.noBudget')
            }
            numeric
          />
          <Row
            label={t('adminRequests.photos')}
            value={formatCount(data.photos, language)}
            numeric
          />
          <Row
            label={t('adminRequests.posted')}
            value={formatDateTime(data.created_at, language)}
            numeric
          />
          {data.expires_at && (
            <Row
              label={t('adminRequests.expires')}
              value={formatDateTime(data.expires_at, language)}
              numeric
            />
          )}
        </dl>

        {data.cancelled_at && (
          <Alert tone="warning" className="mt-5">
            <span className="font-semibold">
              {t('adminRequests.cancelledOn', {
                when: formatDateTime(data.cancelled_at, language),
              })}
            </span>
            {data.cancel_reason && (
              <span dir="auto" className="mt-1 block">
                {data.cancel_reason}
              </span>
            )}
          </Alert>
        )}
      </Card>

      <Person title={t('adminRequests.client')} person={data.client} />

      <Card>
        <h3 className="text-lg font-bold text-fg">
          {t('adminRequests.offers')}{' '}
          <span className="numeric text-fg-subtle">
            ({formatCount(data.offers.length, language)})
          </span>
        </h3>

        {data.offers.length === 0 ? (
          <p className="mt-3 text-sm text-fg-muted">{t('adminRequests.noOffers')}</p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {data.offers.map((offer) => (
              <li key={offer.id}>
                <OfferRow offer={offer} language={language} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      {data.job && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-bold text-fg">
              {t('adminRequests.job')}{' '}
              <span className="numeric text-fg-subtle">#{data.job.id}</span>
            </h3>
            <JobStatusBadge status={data.job.status} />
          </div>

          <dl className="mt-4 grid gap-4 sm:grid-cols-2">
            <Row
              label={t('adminRequests.agreedPrice')}
              value={formatDirhams(data.job.agreed_price_centimes, language)}
              numeric
            />
            {data.job.provider && (
              <Row
                label={t('adminRequests.provider')}
                value={data.job.provider.full_name}
              />
            )}
            {data.job.started_at && (
              <Row
                label={t('adminRequests.started')}
                value={formatDateTime(data.job.started_at, language)}
                numeric
              />
            )}
            {data.job.finished_at && (
              <Row
                label={t('adminRequests.finished')}
                value={formatDateTime(data.job.finished_at, language)}
                numeric
              />
            )}
            {data.job.confirmed_at && (
              <Row
                label={t('adminRequests.confirmed')}
                value={formatDateTime(data.job.confirmed_at, language)}
                numeric
              />
            )}
            {data.job.cancelled_at && (
              <Row
                label={t('adminRequests.cancelled')}
                value={formatDateTime(data.job.cancelled_at, language)}
                numeric
              />
            )}
          </dl>

          {data.job.cancel_reason && (
            <p dir="auto" className="mt-4 text-sm text-fg-muted">
              {data.job.cancel_reason}
            </p>
          )}
        </Card>
      )}

      {data.dispute && (
        <Alert tone="warning">
          <span className="font-semibold">
            {t('adminRequests.disputeOpen', {
              id: data.dispute.id,
            })}
          </span>{' '}
          <Link
            to="/mod/disputes"
            className="font-semibold text-primary underline-offset-2 hover:underline"
          >
            {t('adminRequests.seeDispute')}
          </Link>
        </Alert>
      )}

      <CancelPanel request={data} />
    </div>
  )
}

function Person({
  title,
  person,
}: {
  title: string
  person: { id: number; full_name: string; phone: string }
}) {
  const { t } = useTranslation()

  return (
    <Card>
      <h3 className="text-sm font-semibold text-fg-subtle">{title}</h3>
      <p dir="auto" className="mt-1 text-lg font-bold text-fg">
        {person.full_name}
      </p>
      <p className="mt-1 text-sm text-fg-muted">
        {/* The number is the point of this card: support is on the phone. */}
        <span className="numeric">{formatPhone(person.phone)}</span>
      </p>
      <Link
        to="/admin/users"
        className="mt-3 inline-block text-sm font-semibold text-primary underline-offset-2 hover:underline"
      >
        {t('adminRequests.seeAccount')}
      </Link>
    </Card>
  )
}

function OfferRow({
  offer,
  language,
}: {
  offer: AdminRequestOffer
  language: Language
}) {
  const { t } = useTranslation()

  return (
    <div className="rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span dir="auto" className="text-sm font-semibold text-fg">
          {offer.provider.full_name}
        </span>
        <div className="flex items-center gap-2">
          <span className="numeric text-sm font-bold text-fg">
            {formatDirhams(offer.price_centimes, language)}
          </span>
          <Badge tone={offer.status === 'accepted' ? 'success' : 'neutral'}>
            {t(OFFER_KEYS[offer.status])}
          </Badge>
        </div>
      </div>

      <p className="mt-1 text-xs text-fg-subtle">
        <span className="numeric">{formatPhone(offer.provider.phone)}</span>
        {' · '}
        {formatRelative(offer.created_at, language)}
      </p>

      {offer.message && (
        <p dir="auto" className="mt-2 text-sm text-fg-muted">
          {offer.message}
        </p>
      )}

      {offer.lead_fee_centimes !== null && (
        <p className="mt-2 text-xs text-fg-subtle">
          {t('adminRequests.feeCharged')}:{' '}
          <span className="numeric font-semibold text-fg">
            {formatDirhams(offer.lead_fee_centimes, language)}
          </span>
        </p>
      )}
    </div>
  )
}

/**
 * The screen's one action.
 *
 * When it is not available the panel says *why* rather than hiding: an admin
 * looking for a cancel button and finding nothing concludes the screen is
 * broken, and the answer — "this one has a tradesman on it, open a dispute" —
 * is the thing he actually needed to hear.
 */
function CancelPanel({ request }: { request: AdminRequest }) {
  const { t } = useTranslation()
  const cancel = useCancelRequest()
  const message = useErrorMessage()

  const [reason, setReason] = useState('')

  if (!request.can_cancel) {
    return (
      <Card>
        <h3 className="text-lg font-bold text-fg">{t('adminRequests.cancelTitle')}</h3>
        <p className="mt-2 text-sm text-fg-muted">
          {request.status === 'assigned' || request.status === 'done'
            ? t('adminRequests.cancelAssigned')
            : t('adminRequests.cancelClosed')}
        </p>
      </Card>
    )
  }

  return (
    <Card>
      <h3 className="text-lg font-bold text-fg">{t('adminRequests.cancelTitle')}</h3>
      <p className="mt-2 text-sm text-fg-muted">{t('adminRequests.cancelBody')}</p>

      {cancel.isError && (
        <Alert tone="danger" className="mt-4">
          {message(cancel.error)}
        </Alert>
      )}

      <div className="mt-4">
        <Field
          label={t('adminRequests.cancelReason')}
          hint={t('adminRequests.cancelReasonHint')}
          value={reason}
          maxLength={500}
          onChange={(event) => setReason(event.target.value)}
        />
      </div>

      <div className="mt-4">
        <ConfirmButton
          variant="danger"
          tone="danger"
          label={t('adminRequests.cancelAction')}
          question={t('adminRequests.cancelConfirm')}
          confirmLabel={t('adminRequests.cancelYes')}
          confirmDisabled={reason.trim().length === 0}
          loading={cancel.isPending}
          onConfirm={() => cancel.mutate({ id: request.id, reason: reason.trim() })}
        />
      </div>
    </Card>
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
    <div>
      <dt className="text-xs text-fg-subtle">{label}</dt>
      {/* `dir="auto"` reads the *first* strong character, so a value starting
          with a digit makes the whole block LTR and drags it to the far side
          of its label. It belongs on text a person wrote, and nowhere near a
          number — the `numeric` span already handles the number's own
          direction. */}
      <dd dir={numeric ? undefined : 'auto'} className="mt-0.5 text-sm font-medium text-fg">
        {numeric ? <span className="numeric">{value}</span> : value}
      </dd>
    </div>
  )
}
