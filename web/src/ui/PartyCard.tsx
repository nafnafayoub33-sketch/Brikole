import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import type { JobParty } from '@/data/jobs'
import { formatPhone } from '@/lib/format'
import { Button } from '@/ui/Button'
import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * The other person on a job, with the one thing this screen exists to hand
 * over: their phone number.
 *
 * It appears here and nowhere earlier in the product. Before an offer is
 * accepted nobody has agreed to anything; after it, two people have to meet,
 * and making them come back to a screen to find a number is the kind of
 * friction that sends them to WhatsApp and off the platform for good.
 */
export function PartyCard({
  party,
  label,
  callLabel,
  profileHref,
  size = 'md',
}: {
  party: JobParty
  label: string
  callLabel: string
  /** Set for a tradesman; a client has no public profile. */
  profileHref?: string
  size?: 'md' | 'pro'
}) {
  const { t } = useTranslation()
  const rated = party.rating_count !== null && party.rating_count > 0

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-fg-subtle uppercase">{label}</h3>

      <div className="flex flex-wrap items-center gap-4">
        <Avatar url={party.avatar_url} name={party.full_name} />

        <div className="min-w-0 flex-1">
          {profileHref ? (
            <Link
              to={profileHref}
              dir="auto"
              className="font-semibold text-fg hover:text-primary hover:underline"
            >
              {party.full_name}
            </Link>
          ) : (
            <p dir="auto" className="font-semibold text-fg">
              {party.full_name}
            </p>
          )}

          {rated && (
            <span className="mt-1 flex items-center gap-1.5 text-sm text-fg-muted">
              <Stars value={party.rating_avg ?? 0} size="sm" />
              <span className="numeric font-medium text-fg">
                {(party.rating_avg ?? 0).toFixed(1)}
              </span>
              <span className="text-fg-subtle">
                {t('provider.jobsDone', { count: party.jobs_done ?? 0 })}
              </span>
            </span>
          )}

          <p className="mt-1 text-sm text-fg-muted">
            {t('job.phone')}: <span className="numeric">{formatPhone(party.phone)}</span>
          </p>
        </div>

        {/* A real tel: link — on the phone this is one tap, which is the point. */}
        <a href={`tel:${party.phone}`} className={cn('shrink-0')}>
          <Button variant="secondary" size={size === 'pro' ? 'pro' : 'md'}>
            {callLabel}
          </Button>
        </a>
      </div>
    </div>
  )
}

function Avatar({ url, name }: { url: string | null; name: string }) {
  if (url) {
    return (
      <img
        src={url}
        alt=""
        className="size-14 shrink-0 rounded-full border border-border object-cover"
      />
    )
  }

  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')

  return (
    <span
      aria-hidden
      className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary-soft text-lg font-bold text-primary"
    >
      {initials}
    </span>
  )
}
