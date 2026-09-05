import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { useCities, useTrades } from '@/data/catalog'
import type { MyProviderProfile, ProfileEdit } from '@/data/pro'
import {
  useAddPhoto,
  useEditProfile,
  useMyProfile,
  useRemovePhoto,
  useSetAvailability,
} from '@/data/pro'
import { localisedName } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { usePrivateImage } from '@/hooks/usePrivateImage'
import { formatDate, formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Badge } from '@/ui/Badge'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { PhotoInput, type PickedPhoto } from '@/ui/PhotoInput'
import { Skeleton } from '@/ui/Skeleton'
import { cn } from '@/ui/cn'

/**
 * M8 — his shop window.
 *
 * Everything a client reads about him is here, and nothing that decided
 * whether he got here: no CIN, no status. His identity was checked once at A2,
 * and a card he can swap afterwards makes that check mean nothing.
 *
 * Editing is per section rather than one long form with one save at the
 * bottom. A tradesman fixing a typo in his headline should not have to scroll
 * past his portfolio to save it, and a failed save should not put nine other
 * fields at risk.
 */
export function ProfilePage() {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const profile = useMyProfile()

  if (profile.isPending) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (profile.isError) {
    return (
      <div className="mx-auto max-w-2xl">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    )
  }

  // No profile at all, or one still being judged: the screen he needs is M1
  // or M2, and editing a shop window he does not have yet is not a thing.
  if (profile.data === null || profile.data.status !== 'approved') {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('myProfile.title')}</h1>
        <Alert tone="info" className="mt-6">
          {t('myProfile.notYet')}{' '}
          <Link
            to={profile.data === null ? '/pro/onboarding' : '/pro/status'}
            className="font-semibold text-primary underline-offset-2 hover:underline"
          >
            {t('myProfile.goToStatus')}
          </Link>
        </Alert>
      </div>
    )
  }

  const me = profile.data

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">{t('myProfile.title')}</h1>
      <p className="mt-2 text-fg-muted">{t('myProfile.subtitle')}</p>

      <Availability profile={me} language={language} />
      <Work profile={me} language={language} />
      <Portfolio profile={me} />
      <Identity profile={me} language={language} />
    </div>
  )
}

/**
 * Taking work, or away.
 *
 * First on the screen because it is the one thing here with a consequence
 * today: while it is off, no client finds him. It says exactly that, and
 * exactly what it does not do — his own feed stays open, so a good job can
 * still bring him back early.
 */
function Availability({
  profile,
  language,
}: {
  profile: MyProviderProfile
  language: Language
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const set = useSetAvailability()

  const [backOn, setBackOn] = useState('')
  const { accepting_work: accepting, back_on: until } = profile.availability

  return (
    <Card className="mt-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-fg">{t('myProfile.availability')}</h2>
          <p className="mt-1 text-sm text-fg-muted">
            {accepting ? t('myProfile.takingWork') : t('myProfile.paused')}
          </p>
        </div>
        <Badge tone={accepting ? 'success' : 'warning'}>
          {accepting ? t('myProfile.on') : t('myProfile.off')}
        </Badge>
      </div>

      {!accepting && (
        <p className="mt-3 text-sm text-fg-muted">
          {until
            ? t('myProfile.backOn', { when: formatDate(until, language) })
            : t('myProfile.pausedOpenEnded')}
        </p>
      )}

      <p className="mt-3 text-sm text-fg-subtle">{t('myProfile.pauseExplains')}</p>

      {set.error && (
        <Alert tone="danger" className="mt-4">
          {message(set.error)}
        </Alert>
      )}

      {accepting ? (
        <div className="mt-5 flex flex-col gap-4">
          <Field
            label={t('myProfile.backOnLabel')}
            hint={t('myProfile.backOnHint')}
            type="date"
            numeric
            value={backOn}
            onChange={(event) => setBackOn(event.target.value)}
          />
          <div>
            <ConfirmButton
              variant="secondary"
              tone="danger"
              label={t('myProfile.pauseAction')}
              question={
                backOn
                  ? t('myProfile.pauseConfirmUntil', {
                      when: formatDate(backOn, language),
                    })
                  : t('myProfile.pauseConfirmOpen')
              }
              confirmLabel={t('myProfile.pauseYes')}
              loading={set.isPending}
              onConfirm={() =>
                set.mutate(
                  { accepting_work: false, back_on: backOn || null },
                  { onSuccess: () => setBackOn('') },
                )
              }
            />
          </div>
        </div>
      ) : (
        <div className="mt-5">
          <Button
            loading={set.isPending}
            onClick={() => set.mutate({ accepting_work: true, back_on: null })}
          >
            {t('myProfile.resume')}
          </Button>
        </div>
      )}
    </Card>
  )
}

/** Trades, city, radius — the three that decide which requests he ever sees. */
function Work({
  profile,
  language,
}: {
  profile: MyProviderProfile
  language: Language
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const edit = useEditProfile()
  const cities = useCities()
  const trades = useTrades()

  const [open, setOpen] = useState(false)
  const [tradeIds, setTradeIds] = useState<number[]>(profile.trades.map((one) => one.id))
  const [cityId, setCityId] = useState(profile.city.id)
  const [radius, setRadius] = useState(String(profile.radius_km))
  const [headline, setHeadline] = useState(profile.headline ?? '')
  const [bio, setBio] = useState(profile.bio)
  const [years, setYears] = useState(String(profile.years_experience))
  const [price, setPrice] = useState(
    profile.starting_price_centimes === null
      ? ''
      : String(profile.starting_price_centimes / 100),
  )

  function save() {
    const body: ProfileEdit = {
      trade_ids: tradeIds,
      city_id: cityId,
      radius_km: Number(radius) || 1,
      headline: headline.trim(),
      bio: bio.trim(),
      years_experience: Number(years) || 0,
      starting_price_centimes: price.trim() ? Math.round(Number(price) * 100) : null,
    }
    edit.mutate(body, { onSuccess: () => setOpen(false) })
  }

  if (!open) {
    return (
      <Card className="mt-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="text-lg font-bold text-fg">{t('myProfile.work')}</h2>
          <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
            {t('myProfile.edit')}
          </Button>
        </div>

        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <Row
            label={t('myProfile.trades')}
            value={profile.trades.map((one) => localisedName(one, language)).join(' · ')}
          />
          <Row label={t('myProfile.city')} value={localisedName(profile.city, language)} />
          <Row label={t('myProfile.radius')} value={`${profile.radius_km} km`} numeric />
          <Row
            label={t('myProfile.years')}
            value={String(profile.years_experience)}
            numeric
          />
          <Row
            label={t('myProfile.startingPrice')}
            value={
              profile.starting_price_centimes === null
                ? t('myProfile.noPrice')
                : formatDirhams(profile.starting_price_centimes, language)
            }
            numeric={profile.starting_price_centimes !== null}
          />
        </dl>

        <div className="mt-4">
          <p className="text-xs text-fg-subtle">{t('myProfile.headline')}</p>
          <p dir="auto" className="mt-0.5 text-sm font-medium text-fg">
            {profile.headline || '—'}
          </p>
        </div>

        {profile.bio && (
          <div className="mt-3">
            <p className="text-xs text-fg-subtle">{t('myProfile.bio')}</p>
            <p dir="auto" className="mt-0.5 whitespace-pre-line text-sm text-fg-muted">
              {profile.bio}
            </p>
          </div>
        )}
      </Card>
    )
  }

  return (
    <Card className="mt-4">
      <h2 className="text-lg font-bold text-fg">{t('myProfile.work')}</h2>

      {edit.error && (
        <Alert tone="danger" className="mt-4">
          {message(edit.error)}
        </Alert>
      )}

      <div className="mt-5 flex flex-col gap-5">
        <div>
          <p className="text-sm font-semibold text-fg">{t('myProfile.trades')}</p>
          <p className="mt-1 text-xs text-fg-subtle">{t('myProfile.tradesHint')}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {(trades.data ?? []).map((trade) => {
              const picked = tradeIds.includes(trade.id)
              return (
                <button
                  key={trade.id}
                  type="button"
                  onClick={() =>
                    setTradeIds((current) =>
                      picked
                        ? current.filter((id) => id !== trade.id)
                        : [...current, trade.id],
                    )
                  }
                  className={cn(
                    'rounded-pill border px-3 py-1.5 text-sm transition-colors duration-(--duration-fast)',
                    picked
                      ? 'border-primary bg-primary/10 font-semibold text-primary'
                      : 'border-border text-fg-muted hover:border-fg-subtle',
                  )}
                >
                  {localisedName(trade, language)}
                </button>
              )
            })}
          </div>
        </div>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-fg">{t('myProfile.city')}</span>
          <select
            value={cityId}
            onChange={(event) => setCityId(Number(event.target.value))}
            className="min-h-12 rounded-md border border-border-strong bg-surface px-3 text-fg outline-none focus:border-primary"
          >
            {(cities.data ?? []).map((city) => (
              <option key={city.id} value={city.id}>
                {localisedName(city, language)}
              </option>
            ))}
          </select>
        </label>

        <Field
          label={t('myProfile.radius')}
          hint={t('myProfile.radiusHint')}
          type="number"
          numeric
          min={1}
          max={100}
          value={radius}
          onChange={(event) => setRadius(event.target.value)}
        />

        <Field
          label={t('myProfile.headline')}
          hint={t('myProfile.headlineHint')}
          value={headline}
          maxLength={160}
          dir="auto"
          onChange={(event) => setHeadline(event.target.value)}
        />

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-fg">{t('myProfile.bio')}</span>
          <textarea
            value={bio}
            onChange={(event) => setBio(event.target.value)}
            rows={4}
            maxLength={1000}
            dir="auto"
            className="rounded-md border border-border-strong bg-surface p-3 text-fg outline-none focus:border-primary"
          />
        </label>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label={t('myProfile.years')}
            type="number"
            numeric
            min={0}
            value={years}
            onChange={(event) => setYears(event.target.value)}
          />
          <Field
            label={t('myProfile.startingPrice')}
            hint={t('myProfile.startingPriceHint')}
            type="number"
            numeric
            prefix="DH"
            value={price}
            onChange={(event) => setPrice(event.target.value)}
          />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button
          loading={edit.isPending}
          disabled={tradeIds.length === 0 || headline.trim().length === 0}
          onClick={save}
        >
          {t('myProfile.save')}
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>
          {t('myProfile.cancel')}
        </Button>
      </div>
    </Card>
  )
}

/** Photos of past work — the thing that turns a row in a list into a call. */
function Portfolio({ profile }: { profile: MyProviderProfile }) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const add = useAddPhoto()
  const remove = useRemovePhoto()

  const full = profile.photos.length >= 10
  const error = message(add.error) ?? message(remove.error)

  return (
    <Card className="mt-4">
      <h2 className="text-lg font-bold text-fg">{t('myProfile.portfolio')}</h2>
      <p className="mt-1 text-sm text-fg-muted">{t('myProfile.portfolioHint')}</p>

      {error && (
        <Alert tone="danger" className="mt-4">
          {error}
        </Alert>
      )}

      {profile.photos.length > 0 && (
        <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {profile.photos.map((photo) => (
            <li key={photo.id} className="relative">
              <img
                src={photo.url}
                alt=""
                className="h-28 w-full rounded-md object-cover"
              />
              <div className="mt-2">
                <ConfirmButton
                  size="sm"
                  variant="ghost"
                  tone="danger"
                  label={t('myProfile.removePhoto')}
                  question={t('myProfile.removePhotoConfirm')}
                  confirmLabel={t('myProfile.removePhotoYes')}
                  loading={remove.isPending}
                  onConfirm={() => remove.mutate(photo.id)}
                />
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* `PhotoInput` uploads and hands back the stored path; attaching it to
          the profile is the second step, and the only one this screen owns.
          Its value stays null because a saved photo appears in the gallery
          above, not back inside the picker. */}
      <div className="mt-4">
        {full ? (
          <p className="text-sm text-fg-subtle">{t('myProfile.portfolioFull')}</p>
        ) : (
          <PhotoInput
            label={t('myProfile.addPhoto')}
            purpose="portfolio"
            value={null}
            onChange={(picked: PickedPhoto | null) => {
              if (picked) add.mutate(picked.path)
            }}
          />
        )}
      </div>
    </Card>
  )
}

/** What he cannot change here, and why — rather than a section that is simply
 *  absent and leaves him looking for it. */
function Identity({
  profile,
  language,
}: {
  profile: MyProviderProfile
  language: Language
}) {
  const { t } = useTranslation()
  const card = usePrivateImage(profile.id_card_path)

  return (
    <Card className="mt-4">
      <h2 className="text-lg font-bold text-fg">{t('myProfile.identity')}</h2>
      <p className="mt-1 text-sm text-fg-muted">{t('myProfile.identityHint')}</p>

      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
        <Row label={t('myProfile.name')} value={profile.full_name} />
        <Row
          label={t('myProfile.memberSince')}
          value={formatDate(profile.member_since, language)}
          numeric
        />
      </dl>

      {card.url && (
        <img
          src={card.url}
          alt=""
          className="mt-4 max-h-40 rounded-md border border-border object-contain"
        />
      )}
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
