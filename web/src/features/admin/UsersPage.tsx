import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { AdminUser, AdminUserRow, UserFilters } from '@/data/admin'
import {
  USERS_PER_PAGE,
  useChangeRole,
  useReactivateUser,
  useResetPassword,
  useSuspendUser,
  useUser,
  useUsers,
} from '@/data/admin'
import { useSession } from '@/data/auth'
import { ROLES, localisedName } from '@/data/types'
import type { ProviderStatus, Role, UserStatus } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatCount, formatDate, formatDirhams, formatPhone, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { EmptyState } from '@/ui/EmptyState'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { Pager } from '@/ui/Pager'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'
import { REASON_KEYS, STATUS_KEYS, STATUS_TONES } from '@/ui/disputeLabels'

const STATUSES: UserStatus[] = ['active', 'suspended', 'deleted']

/** `status.*` at the top level is M2's — an application's state, not an
 *  account's. These are the account's, and they live with the screen. */
const STATUS_LABELS: Record<UserStatus, string> = {
  active: 'users.statusActive',
  suspended: 'users.statusSuspended',
  deleted: 'users.statusDeleted',
}

const PROVIDER_LABELS: Record<ProviderStatus, string> = {
  approved: 'users.providerApproved',
  pending: 'users.providerPending',
  rejected: 'users.providerRejected',
  suspended: 'users.providerSuspended',
}

/** What a suspension may be. `null` is permanent, and only an admin has it. */
const LENGTHS: { days: number | null; key: string }[] = [
  { days: 7, key: 'users.days7' },
  { days: 30, key: 'users.days30' },
  { days: 90, key: 'users.days90' },
  { days: null, key: 'users.forever' },
]

/**
 * A3 — accounts.
 *
 * The screen with the most power on the platform: the only place a role
 * changes, and the only place a suspension can be permanent. So the API
 * refuses what must be refused, and this screen's job is to make the refusals
 * legible before they happen — the admin's own row says so, a tradesman's role
 * panel says why it is locked — rather than letting somebody press a button
 * and read an error.
 */
export function UsersPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language

  const [filters, setFilters] = useState<UserFilters>({ q: '', role: null, status: null })
  const [pageNumber, setPageNumber] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const users = useUsers(filters, pageNumber)
  const page = users.data

  // A new search starts at the top. Staying on page 4 of the old result and
  // showing an empty list is the classic way this goes wrong.
  const changeFilters = (next: UserFilters) => {
    setFilters(next)
    setPageNumber(1)
  }

  const pages = page ? Math.max(1, Math.ceil(page.total / USERS_PER_PAGE)) : 1

  // The selection has to follow the list: filtering it away must not leave the
  // pane pointing at a row that is no longer on screen.
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
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <h1 className="text-2xl font-bold text-fg">{t('users.title')}</h1>
          {page && (
            <span className="text-sm font-medium text-fg-muted">
              {page.total === 1
                ? t('users.foundOne')
                : t('users.found', { value: formatCount(page.total, language) })}
            </span>
          )}
        </div>

        <Link
          to="/admin/staff"
          className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
        >
          {t('users.toStaff')}
        </Link>
      </div>

      <Filters filters={filters} onChange={changeFilters} />

      {users.isPending ? (
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      ) : users.isError ? (
        <ErrorState error={users.error} onRetry={() => void users.refetch()} />
      ) : users.data.items.length === 0 ? (
        <EmptyState title={t('users.empty')} body={t('users.emptyBody')} />
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[340px_1fr]">
          <div className="flex flex-col gap-3 lg:sticky lg:top-6">
            {/* The list scrolls inside itself. Three hundred accounts down one
                page push the detail — the thing being read — off the screen. */}
            <ul className="flex max-h-[70vh] flex-col gap-2 overflow-y-auto pe-1">
              {users.data.items.map((row) => (
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
            <EmptyState title={t('users.pick')} />
          ) : (
            <Detail key={selectedId} userId={selectedId} language={language} />
          )}
        </div>
      )}
    </div>
  )
}

function Filters({
  filters,
  onChange,
}: {
  filters: UserFilters
  onChange: (next: UserFilters) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="mb-6 flex flex-wrap items-end gap-3">
      <div className="min-w-56 flex-1">
        <Field
          label={t('users.search')}
          hint={t('users.searchHint')}
          value={filters.q}
          onChange={(event) => onChange({ ...filters, q: event.target.value })}
        />
      </div>

      <select
        className="h-11 rounded-md border border-border-strong bg-surface px-3 text-sm text-fg"
        value={filters.role ?? ''}
        onChange={(event) =>
          onChange({ ...filters, role: (event.target.value || null) as Role | null })
        }
      >
        <option value="">{t('users.allRoles')}</option>
        {ROLES.map((role) => (
          <option key={role} value={role}>
            {t(`roles.${role}`)}
          </option>
        ))}
      </select>

      <select
        className="h-11 rounded-md border border-border-strong bg-surface px-3 text-sm text-fg"
        value={filters.status ?? ''}
        onChange={(event) =>
          onChange({ ...filters, status: (event.target.value || null) as UserStatus | null })
        }
      >
        <option value="">{t('users.allStatuses')}</option>
        {STATUSES.map((status) => (
          <option key={status} value={status}>
            {t(STATUS_LABELS[status])}
          </option>
        ))}
      </select>
    </div>
  )
}

function ListRow({
  row,
  language,
  selected,
  onSelect,
}: {
  row: AdminUserRow
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
        'w-full rounded-lg border bg-surface p-4 text-start shadow-sm',
        'transition-colors duration-(--duration-fast)',
        selected ? 'border-primary' : 'border-border hover:border-primary/40',
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate font-semibold text-fg">{row.full_name}</span>
        <StatusBadge status={row.status} />
      </div>

      <p className="numeric mt-1 text-sm text-fg-muted">{formatPhone(row.phone)}</p>

      <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-fg-subtle">
        <Badge tone={row.role === 'admin' ? 'brand' : 'neutral'}>{t(`roles.${row.role}`)}</Badge>
        {row.city && <span>{localisedName(row.city, language)}</span>}
      </p>
    </button>
  )
}

function StatusBadge({ status }: { status: UserStatus }) {
  const { t } = useTranslation()
  const tone = status === 'active' ? 'success' : status === 'suspended' ? 'danger' : 'neutral'
  return <Badge tone={tone}>{t(STATUS_LABELS[status])}</Badge>
}

function Detail({ userId, language }: { userId: number; language: Language }) {
  const { t } = useTranslation()
  const query = useUser(userId)
  const me = useSession()

  if (query.isPending) return <Skeleton className="h-96" />
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  }

  const user = query.data
  const isSelf = me.data?.id === user.id

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-xl font-bold text-fg">{user.full_name}</h2>
            <p className="numeric mt-1 text-sm text-fg-muted">{formatPhone(user.phone)}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={user.role === 'admin' ? 'brand' : 'neutral'}>
              {t(`roles.${user.role}`)}
            </Badge>
            <StatusBadge status={user.status} />
          </div>
        </div>

        <dl className="mt-4 flex flex-col gap-1 text-sm text-fg-muted">
          <div>{t('users.joined', { date: formatDate(user.created_at, language) })}</div>
          <div>
            {user.last_login_at
              ? t('users.lastSeen', { date: formatRelative(user.last_login_at, language) })
              : t('users.neverSignedIn')}
          </div>
          {user.city && <div>{localisedName(user.city, language)}</div>}
          {user.provider && <div>{t('users.alsoProvider')}</div>}
        </dl>

        {user.status === 'suspended' && (
          <Alert tone="danger" className="mt-4">
            <p className="font-semibold">
              {user.suspended_until
                ? t('users.suspendedUntil', {
                    date: formatDate(user.suspended_until, language),
                  })
                : t('users.suspendedForever')}
            </p>
            {user.suspension_reason && (
              <p className="mt-1">
                {t('users.reason')} — {user.suspension_reason}
              </p>
            )}
          </Alert>
        )}

        {user.locked_until && user.status === 'active' && (
          <Alert tone="warning" className="mt-4">
            {t('users.lockedOut')}
          </Alert>
        )}
      </Card>

      <Activity user={user} language={language} />

      {user.provider && <ProviderPanel user={user} language={language} />}

      <Disputes user={user} language={language} />

      <Actions user={user} isSelf={isSelf} />
    </div>
  )
}

function Activity({ user, language }: { user: AdminUser; language: Language }) {
  const { t } = useTranslation()
  const { activity } = user
  const count = (value: number) => formatCount(value, language)

  return (
    <Card>
      <h3 className="text-base font-semibold text-fg">{t('users.activityTitle')}</h3>

      <div className="mt-4 grid gap-6 sm:grid-cols-2">
        <Group title={t('users.asClient')}>
          <Line label={t('users.requestsPosted')} value={count(activity.requests_posted)} />
          <Line label={t('users.jobsHired')} value={count(activity.jobs_hired)} />
          <Line
            label={t('users.spent')}
            value={formatDirhams(activity.spent_centimes, language)}
          />
          <Line label={t('users.reviewsWritten')} value={count(activity.reviews_written)} />
        </Group>

        <Group title={t('users.asProvider')}>
          <Line label={t('users.offersSent')} value={count(activity.offers_sent)} />
          <Line label={t('users.jobsWorked')} value={count(activity.jobs_worked)} />
        </Group>

        {activity.staff_actions > 0 && (
          <Group title={t('users.asStaff')}>
            <Line label={t('users.staffActions')} value={count(activity.staff_actions)} />
          </Group>
        )}
      </div>
    </Card>
  )
}

function ProviderPanel({ user, language }: { user: AdminUser; language: Language }) {
  const { t } = useTranslation()
  const profile = user.provider
  if (!profile) return null

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-base font-semibold text-fg">{t('users.providerTitle')}</h3>
        <Badge tone={profile.status === 'approved' ? 'success' : 'warning'}>
          {t(PROVIDER_LABELS[profile.status])}
        </Badge>
      </div>

      {profile.headline && <p className="mt-2 text-sm text-fg-muted">{profile.headline}</p>}

      <dl className="mt-4 flex flex-col gap-2">
        <Line
          label={t('users.rating')}
          value={
            profile.rating_count > 0
              ? `${profile.rating_avg.toFixed(1)} · ${formatCount(profile.rating_count, language)}`
              : '—'
          }
        />
        <Line
          label={t('users.balance')}
          value={formatDirhams(profile.balance_centimes, language)}
        />
        <Line
          label={t('users.freeLeads')}
          value={formatCount(profile.free_leads_left, language)}
        />
      </dl>
    </Card>
  )
}

function Disputes({ user, language }: { user: AdminUser; language: Language }) {
  const { t } = useTranslation()

  return (
    <Card>
      <h3 className="text-base font-semibold text-fg">{t('users.disputesTitle')}</h3>

      {user.disputes.length === 0 ? (
        <p className="mt-3 text-sm text-fg-subtle">{t('users.noDisputes')}</p>
      ) : (
        <ul className="mt-3 flex flex-col divide-y divide-border">
          {user.disputes.map((dispute) => (
            <li
              key={dispute.id}
              className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="min-w-0">
                <p className="text-sm text-fg">{t(REASON_KEYS[dispute.reason as keyof typeof REASON_KEYS])}</p>
                <p className="mt-0.5 text-xs text-fg-subtle">
                  {dispute.opened_by_them ? t('users.theyOpened') : t('users.againstThem')} ·{' '}
                  {formatDate(dispute.created_at, language)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={STATUS_TONES[dispute.status]}>
                  {t(STATUS_KEYS[dispute.status])}
                </Badge>
                <Link
                  to={`/mod/disputes/${dispute.id}`}
                  className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
                >
                  {t('users.openDispute')}
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function Actions({ user, isSelf }: { user: AdminUser; isSelf: boolean }) {
  const { t } = useTranslation()
  const message = useErrorMessage()

  const suspend = useSuspendUser()
  const reactivate = useReactivateUser()
  const changeRole = useChangeRole()
  const resetPassword = useResetPassword()

  const [reason, setReason] = useState('')
  const [days, setDays] = useState<number | null>(7)
  const [role, setRole] = useState<Role>(user.role)

  const error =
    message(suspend.error) ??
    message(reactivate.error) ??
    message(changeRole.error) ??
    message(resetPassword.error)

  if (isSelf) {
    return (
      <Card>
        <h3 className="text-base font-semibold text-fg">{t('users.actionsTitle')}</h3>
        <p className="mt-2 text-sm text-fg-muted">{t('users.selfNote')}</p>
      </Card>
    )
  }

  const locked = user.provider !== null

  return (
    <Card>
      <h3 className="text-base font-semibold text-fg">{t('users.actionsTitle')}</h3>

      {error && (
        <Alert tone="danger" className="mt-4">
          {error}
        </Alert>
      )}

      {/* `items-start`, or the column stretches the buttons and a destructive
          action becomes the widest, loudest thing on the screen. */}
      <div className="mt-4 flex flex-col items-start gap-6">
        {/* Distinct keys, deliberately. Without them React reuses the one
            instance across the swap and the new button inherits the old one's
            "are you sure?" state — so suspending somebody lands the admin on
            an armed prompt to undo it, one stray click from putting the
            account back. */}
        {user.status === 'suspended' ? (
          <ConfirmButton
            key="reactivate"
            label={t('users.reactivate')}
            question={t('users.reactivateQuestion')}
            confirmLabel={t('users.reactivateConfirm')}
            loading={reactivate.isPending}
            onConfirm={() => reactivate.mutate({ id: user.id })}
          />
        ) : (
          <ConfirmButton
            key="suspend"
            variant="danger"
            tone="danger"
            label={t('users.suspend')}
            question={t('users.suspendQuestion')}
            confirmLabel={t('users.suspendConfirm')}
            loading={suspend.isPending}
            confirmDisabled={reason.trim().length === 0}
            onConfirm={() =>
              suspend.mutate(
                { id: user.id, days, reason },
                { onSuccess: () => setReason('') },
              )
            }
          >
            <div className="flex flex-col gap-3">
              <Field
                label={t('users.suspendReason')}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <fieldset className="flex flex-wrap gap-2">
                <legend className="mb-2 text-sm font-semibold text-fg">
                  {t('users.suspendLength')}
                </legend>
                {LENGTHS.map((length) => (
                  <Button
                    key={length.key}
                    size="sm"
                    variant={length.days === days ? 'primary' : 'secondary'}
                    onClick={() => setDays(length.days)}
                  >
                    {t(length.key)}
                  </Button>
                ))}
              </fieldset>
            </div>
          </ConfirmButton>
        )}

        <div className="w-full border-t border-border pt-6">
          <h4 className="text-sm font-semibold text-fg">{t('users.roleTitle')}</h4>

          {locked ? (
            <p className="mt-2 text-sm text-fg-muted">{t('users.roleLocked')}</p>
          ) : (
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <select
                className="h-11 rounded-md border border-border-strong bg-surface px-3 text-sm text-fg"
                value={role}
                onChange={(event) => setRole(event.target.value as Role)}
              >
                {/* `provider` is missing on purpose: a m3allem is an
                    application with a CIN behind it, not a dropdown. */}
                {(['client', 'moderator', 'admin'] as const).map((option) => (
                  <option key={option} value={option}>
                    {t(`roles.${option}`)}
                  </option>
                ))}
              </select>

              <ConfirmButton
                label={t('users.roleConfirm')}
                question={t('users.roleQuestion')}
                confirmLabel={t('users.roleConfirm')}
                disabled={role === user.role}
                loading={changeRole.isPending}
                onConfirm={() => changeRole.mutate({ id: user.id, role })}
              />
            </div>
          )}
        </div>

        <Password user={user} reset={resetPassword} />
      </div>
    </Card>
  )
}

/**
 * P6's other half. The forgot-password screen tells people an admin resets it,
 * and this is where he does — so the block reads as the end of a phone call
 * rather than as a button: what it does to the old password, the new one in
 * one line big enough to read out, and the fact that closing the pane is the
 * last time anybody sees it.
 */
function Password({
  user,
  reset,
}: {
  user: AdminUser
  reset: ReturnType<typeof useResetPassword>
}) {
  const { t } = useTranslation()

  return (
    <div className="w-full border-t border-border pt-6">
      <h4 className="text-sm font-semibold text-fg">{t('users.passwordTitle')}</h4>

      {/* Refused before it is pressed. A new password for an account sign-in
          turns away is five minutes on the phone spelling out a code, and then
          the person reads "your account is suspended" for the first time. */}
      {user.status !== 'active' ? (
        <p className="mt-2 text-sm text-fg-muted">{t('users.passwordBlocked')}</p>
      ) : reset.data ? (
        <Alert tone="warning" className="mt-3">
          <p className="font-semibold">{t('users.passwordOnce')}</p>
          {/* `.numeric` for the same reason a plate number wears it: a Latin
              code stays Latin and stays LTR, in all three languages. */}
          <p className="numeric mt-2 text-xl font-bold tracking-widest text-fg">
            {reset.data.password}
          </p>
          <p className="mt-2">{t('users.passwordThenChange')}</p>
        </Alert>
      ) : (
        <>
          <p className="mt-2 text-sm text-fg-muted">{t('users.passwordBody')}</p>
          <ConfirmButton
            className="mt-3"
            variant="secondary"
            tone="danger"
            label={t('users.passwordReset')}
            question={t('users.passwordQuestion')}
            confirmLabel={t('users.passwordConfirm')}
            loading={reset.isPending}
            onConfirm={() => reset.mutate({ id: user.id })}
          />
        </>
      )}
    </div>
  )
}


function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-fg">{title}</h4>
      <dl className="mt-2 flex flex-col gap-2">{children}</dl>
    </div>
  )
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-sm text-fg-muted">{label}</dt>
      <dd className="numeric text-sm font-semibold text-fg">{value}</dd>
    </div>
  )
}
