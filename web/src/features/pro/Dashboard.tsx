import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useMyJobs } from '@/data/jobs'
import { useCredit, useFeed, useMyOffers } from '@/data/offers'
import type { MyProviderProfile } from '@/data/pro'
import { ApiError } from '@/data/client'
import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { Skeleton } from '@/ui/Skeleton'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * M3 — what he checks in the morning.
 *
 * The balance is the loudest thing on it, because it is the one number that
 * decides whether the rest of the screen means anything: at zero the feed is
 * closed and every other figure here is about work he cannot take.
 */
export function Dashboard({
  profile,
  language,
}: {
  profile: MyProviderProfile
  language: Language
}) {
  const { t } = useTranslation()

  const credit = useCredit()
  const feed = useFeed({})
  const offers = useMyOffers()
  const jobs = useMyJobs()

  const blocked =
    credit.data?.can_take_work === false ||
    (feed.error instanceof ApiError && feed.error.code === 'insufficient_credit')

  const balance = credit.data?.balance_centimes ?? 0
  const fee = credit.data?.default_lead_fee_centimes ?? 0
  const freeLeads = credit.data?.free_leads_left ?? 0
  // "Low" is measured in leads he can still afford, not in dirhams.
  const leadsLeft = fee > 0 ? Math.floor(Math.max(0, balance) / fee) + freeLeads : freeLeads
  const low = !blocked && leadsLeft <= 1

  const waiting = (offers.data?.items ?? []).filter((offer) => offer.status === 'pending').length
  const active = (jobs.data?.items ?? []).filter(
    (job) => job.status === 'assigned' || job.status === 'in_progress',
  ).length

  return (
    <div className="mx-auto max-w-3xl">
      <h1 dir="auto" className="text-2xl font-bold text-fg sm:text-3xl">
        {t('dash.hello', { name: profile.full_name })}
      </h1>

      {blocked && (
        <Alert tone="warning" className="mt-5">
          {t('dash.outOfCredit')}
        </Alert>
      )}
      {low && (
        <Alert tone="warning" className="mt-5">
          {t('dash.lowCredit')}
        </Alert>
      )}

      <Card className="mt-6">
        <p className="text-sm text-fg-subtle">{t('dash.balance')}</p>
        {credit.isPending ? (
          <Skeleton className="mt-2 h-12 w-40" />
        ) : (
          <p
            className={cn(
              'numeric mt-1 text-4xl font-bold',
              blocked ? 'text-danger' : 'text-fg',
            )}
          >
            {formatDirhams(balance, language)}
          </p>
        )}
        {freeLeads > 0 && (
          <p className="mt-2 text-sm text-success">
            {freeLeads === 1
              ? t('feed.freeLeadsOne')
              : t('feed.freeLeads', { count: freeLeads })}
          </p>
        )}
        <Link to="/pro/credit" className="mt-5 inline-block">
          <Button size="pro" variant={blocked ? 'primary' : 'secondary'}>
            {t('dash.topUp')}
          </Button>
        </Link>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Stat
          label={t('dash.newRequests')}
          value={blocked ? '—' : String(feed.data?.total ?? 0)}
          to="/pro/requests"
          loading={feed.isPending}
        />
        <Stat
          label={t('dash.pendingOffers')}
          value={String(waiting)}
          to="/pro/offers"
          loading={offers.isPending}
        />
        <Stat
          label={t('dash.activeJobs')}
          value={String(active)}
          to="/pro/jobs"
          loading={jobs.isPending}
        />
      </div>

      <Card className="mt-6">
        <p className="text-sm text-fg-subtle">{t('dash.rating')}</p>
        {profile.rating_count > 0 ? (
          <div className="mt-2 flex items-center gap-3">
            <Stars value={profile.rating_avg} />
            <span className="numeric font-bold text-fg">{profile.rating_avg.toFixed(1)}</span>
            <span className="text-sm text-fg-subtle">
              {t('provider.jobsDone', { count: profile.jobs_done })}
            </span>
          </div>
        ) : (
          <p className="mt-2 text-fg-subtle">{t('dash.noRating')}</p>
        )}
      </Card>

      {!blocked && (
        <div className="mt-8">
          <Link to="/pro/requests">
            <Button size="pro">{t('dash.seeFeed')}</Button>
          </Link>
        </div>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  to,
  loading,
}: {
  label: string
  value: string
  to: string
  loading: boolean
}) {
  return (
    <Link
      to={to}
      className="rounded-lg border border-border bg-surface p-5 shadow-sm transition-all duration-(--duration-fast) hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
    >
      <p className="text-sm text-fg-subtle">{label}</p>
      {loading ? (
        <Skeleton className="mt-2 h-9 w-12" />
      ) : (
        <p className="numeric mt-1 text-3xl font-bold text-fg">{value}</p>
      )}
    </Link>
  )
}
