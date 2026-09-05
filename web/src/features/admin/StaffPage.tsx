import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { StaffMember, StaffWork } from '@/data/admin'
import {
  useCreateStaff,
  useReactivateUser,
  useStaff,
  useSuspendUser,
} from '@/data/admin'
import type { Role } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatCount, formatDate, formatPhone, formatRelative } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * A9 — moderators and admins, what they have handled, and deactivation.
 *
 * A3 lists every account; this one lists the people who can change them, and
 * shows the only thing about staff that A3 cannot: their work. The counts come
 * out of the audit log rather than a column somebody remembers to increment,
 * so they are right by construction — a staff action that is not logged is a
 * bug the product already has.
 *
 * Adding a moderator lives here rather than on A3. It was on A3 because that
 * is where the accounts were, but "add somebody who can suspend accounts" is a
 * staff decision, and two buttons in one product area that do the same thing
 * is how one of them gets found by accident.
 */

const KINDS = ['approvals', 'disputes', 'reports', 'money', 'accounts', 'platform'] as const

/** How long a suspension may be. `null` is permanent — for somebody who has
 *  left, which is what this screen's deactivation usually means. */
const LENGTHS: { days: number | null; key: string }[] = [
  { days: 7, key: 'users.days7' },
  { days: 30, key: 'users.days30' },
  { days: 90, key: 'users.days90' },
  { days: null, key: 'users.forever' },
]

export function StaffPage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const staff = useStaff()

  const [adding, setAdding] = useState(false)

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('staff.title')}</h1>
          <p className="mt-2 text-fg-muted">{t('staff.subtitle')}</p>
        </div>

        <Button variant="secondary" onClick={() => setAdding((open) => !open)}>
          {t('staff.new')}
        </Button>
      </div>

      {adding && <NewStaff onDone={() => setAdding(false)} />}

      {staff.isPending ? (
        <div className="mt-6 flex flex-col gap-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : staff.isError ? (
        <div className="mt-6">
          <ErrorState error={staff.error} onRetry={() => void staff.refetch()} />
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-3">
          {staff.data.members.map((person) => (
            <StaffCard key={person.id} person={person} language={language} />
          ))}
        </div>
      )}
    </div>
  )
}

function StaffCard({ person, language }: { person: StaffMember; language: Language }) {
  const { t } = useTranslation()
  const suspended = person.status === 'suspended'

  return (
    <Card className={cn(suspended && 'opacity-80')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p dir="auto" className="text-lg font-bold text-fg">
            {person.full_name}
            {person.is_me && (
              <span className="ms-2 text-sm font-medium text-fg-subtle">
                {t('staff.you')}
              </span>
            )}
          </p>
          <p className="numeric mt-0.5 text-sm text-fg-muted">
            {formatPhone(person.phone)}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={person.role === 'admin' ? 'brand' : 'neutral'}>
            {t(`roles.${person.role}`)}
          </Badge>
          {suspended && <Badge tone="warning">{t('users.statusSuspended')}</Badge>}
        </div>
      </div>

      {suspended && person.suspension_reason && (
        <Alert tone="warning" className="mt-4">
          <span dir="auto">{person.suspension_reason}</span>
          {person.suspended_until ? (
            <span className="mt-1 block">
              {t('staff.suspendedUntil', {
                when: formatDate(person.suspended_until, language),
              })}
            </span>
          ) : (
            <span className="mt-1 block font-semibold">{t('staff.suspendedForever')}</span>
          )}
        </Alert>
      )}

      <Work work={person.work} language={language} />

      <p className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-fg-subtle">
        <span>
          {t('staff.lastAction')}:{' '}
          <span className="font-semibold text-fg-muted">
            {person.last_action_at
              ? formatRelative(person.last_action_at, language)
              : t('staff.never')}
          </span>
        </span>
        <span>
          {t('staff.lastLogin')}:{' '}
          <span className="font-semibold text-fg-muted">
            {person.last_login_at
              ? formatRelative(person.last_login_at, language)
              : t('staff.never')}
          </span>
        </span>
        <span>
          {t('staff.since')}:{' '}
          <span className="numeric font-semibold text-fg-muted">
            {formatDate(person.created_at, language)}
          </span>
        </span>
      </p>

      <Actions person={person} />
    </Card>
  )
}

/**
 * Six kinds of work, always all six.
 *
 * A moderator who has never touched a dispute is a fact worth seeing, so a
 * zero is rendered rather than skipped — and the total sits apart, because a
 * total that does not match the six is the sign of an action nobody has
 * classified yet.
 */
function Work({ work, language }: { work: StaffWork; language: Language }) {
  const { t } = useTranslation()

  return (
    <div className="mt-5 rounded-md border border-border bg-surface-2 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-fg">{t('staff.handled')}</p>
        <p className="text-sm text-fg-subtle">
          {t('staff.total')}:{' '}
          <span className="numeric font-bold text-fg">
            {formatCount(work.total, language)}
          </span>
        </p>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {KINDS.map((kind) => (
          <div key={kind}>
            <dt className="text-xs text-fg-subtle">{t(`staff.kind_${kind}`)}</dt>
            <dd
              className={cn(
                'numeric mt-0.5 text-lg font-bold',
                work[kind] === 0 ? 'text-fg-subtle' : 'text-fg',
              )}
            >
              {formatCount(work[kind], language)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

/**
 * Deactivation, and the one refusal that is worth showing before it is
 * pressed: an admin acting on his own account. Suspending yourself locks you
 * out of the screen that would undo it, so the buttons are not offered at all.
 */
function Actions({ person }: { person: StaffMember }) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const suspend = useSuspendUser()
  const reactivate = useReactivateUser()

  const [days, setDays] = useState<number | null>(7)
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)

  if (person.is_me) {
    return <p className="mt-4 text-sm text-fg-subtle">{t('staff.notYourself')}</p>
  }

  if (person.status === 'suspended') {
    return (
      <div className="mt-4">
        {reactivate.error && (
          <Alert tone="danger" className="mb-3">
            {message(reactivate.error)}
          </Alert>
        )}
        <Button
          size="sm"
          variant="secondary"
          loading={reactivate.isPending}
          onClick={() => reactivate.mutate({ id: person.id })}
        >
          {t('staff.reactivate')}
        </Button>
      </div>
    )
  }

  if (!open) {
    return (
      <div className="mt-4">
        <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
          {t('staff.deactivate')}
        </Button>
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-md border border-border p-4">
      <p className="text-sm font-semibold text-fg">{t('staff.deactivate')}</p>

      {suspend.error && (
        <Alert tone="danger" className="mt-3">
          {message(suspend.error)}
        </Alert>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {LENGTHS.map((length) => (
          <Button
            key={String(length.days)}
            size="sm"
            variant={days === length.days ? 'primary' : 'secondary'}
            onClick={() => setDays(length.days)}
          >
            {t(length.key)}
          </Button>
        ))}
      </div>

      <div className="mt-4">
        <Field
          label={t('staff.reason')}
          hint={t('staff.reasonHint')}
          value={reason}
          maxLength={500}
          onChange={(event) => setReason(event.target.value)}
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <ConfirmButton
          size="sm"
          variant="danger"
          tone="danger"
          label={t('staff.deactivateAction')}
          question={
            days === null ? t('staff.confirmForever') : t('staff.confirmDays', { days })
          }
          confirmLabel={t('staff.confirmYes')}
          confirmDisabled={reason.trim().length === 0}
          loading={suspend.isPending}
          onConfirm={() =>
            suspend.mutate(
              { id: person.id, days, reason: reason.trim() },
              {
                onSuccess: () => {
                  setOpen(false)
                  setReason('')
                },
              },
            )
          }
        />
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          {t('staff.cancel')}
        </Button>
      </div>
    </div>
  )
}

/**
 * Adding a moderator or an admin.
 *
 * Moved here from A3, where it sat because that is where the accounts were.
 * "Add somebody who can suspend accounts" is a staff decision, and this is the
 * staff screen.
 */
function NewStaff({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const create = useCreateStaff()

  const [phone, setPhone] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('moderator')

  return (
    <Card className="mt-6">
      <h2 className="text-base font-semibold text-fg">{t('staff.new')}</h2>
      <p className="mt-1 max-w-prose text-sm text-fg-subtle">{t('staff.newHint')}</p>

      {create.error && (
        <Alert tone="danger" className="mt-4">
          {message(create.error)}
        </Alert>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Field
          label={t('users.fullName')}
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
        <Field
          label={t('users.phone')}
          numeric
          inputMode="tel"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
        />
        <Field
          label={t('users.password')}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-fg" htmlFor="new-staff-role">
            {t('users.roleTitle')}
          </label>
          <select
            id="new-staff-role"
            className="h-11 rounded-md border border-border-strong bg-surface px-3 text-sm text-fg"
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
          >
            {(['moderator', 'admin'] as const).map((option) => (
              <option key={option} value={option}>
                {t(`roles.${option}`)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          loading={create.isPending}
          disabled={!phone.trim() || !fullName.trim() || !password}
          onClick={() =>
            create.mutate(
              { phone, full_name: fullName, password, role },
              {
                onSuccess: () => {
                  setPhone('')
                  setFullName('')
                  setPassword('')
                  onDone()
                },
              },
            )
          }
        >
          {t('users.create')}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t('staff.cancel')}
        </Button>
      </div>
    </Card>
  )
}
