import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import {
  useChangePassword,
  useCommitments,
  useDeleteAccount,
  useEditAccount,
} from '@/data/account'
import { useLogout, useSession } from '@/data/auth'
import { useCities } from '@/data/catalog'
import { localisedName } from '@/data/types'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { formatPhone } from '@/lib/format'
import { LANGUAGES, LANGUAGE_LABELS, setLanguage, type Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'
import { ConfirmButton } from '@/ui/ConfirmButton'
import { ErrorState } from '@/ui/ErrorState'
import { Field } from '@/ui/Field'
import { PhotoInput, type PickedPhoto } from '@/ui/PhotoInput'
import { Skeleton } from '@/ui/Skeleton'

/**
 * C7, M11 and D4 — one screen, three roles.
 *
 * A client, a tradesman and a moderator edit the same row, so they get the
 * same screen; what changes is the layout around it, which is the router's
 * business rather than three copies of a form. The tradesman gets one extra
 * line pointing at M8, because the headline and the trades a client reads are
 * *not* here and somebody will come looking for them.
 *
 * The phone is shown and cannot be edited. It is the identity — it signs him
 * in and it is what an admin asks for on the P6 call — so the screen says why
 * rather than leaving a greyed-out box to be argued with.
 */
export function AccountPage() {
  const { t, i18n } = useTranslation()
  const session = useSession()

  if (session.isPending) return <Skeleton className="h-96" />
  if (session.isError) {
    return <ErrorState error={session.error} onRetry={() => void session.refetch()} />
  }
  if (!session.data) return null

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-bold text-fg">{t('account.title')}</h1>

      <Identity key={session.data.id} language={i18n.language as Language} />
      <Password />
      <Leaving />
    </div>
  )
}

function Identity({ language }: { language: Language }) {
  const { t } = useTranslation()
  const session = useSession()
  const cities = useCities()
  const edit = useEditAccount()
  const message = useErrorMessage()

  const me = session.data
  const [name, setName] = useState(me?.full_name ?? '')
  const [cityId, setCityId] = useState<number | null>(me?.city_id ?? null)
  const [photo, setPhoto] = useState<PickedPhoto | null>(null)
  const [saved, setSaved] = useState(false)

  if (!me) return null

  // The language is *not* form state seeded from the stored preference. The
  // two can legitimately disagree — the header switcher changes the interface
  // without saving anything — and seeding from the stored one means pressing
  // "save" on a name change also flips the whole app to a language he did not
  // ask for just now. So the select shows the language he is reading, switches
  // it the moment he picks, like every other language control in the app, and
  // saving is what makes it stick to the account.
  const pickLanguage = (value: Language) => {
    setSaved(false)
    void setLanguage(value)
  }

  const save = () => {
    setSaved(false)
    edit.mutate(
      {
        full_name: name,
        city_id: cityId,
        language,
        ...(photo ? { avatar_path: photo.path } : {}),
      },
      { onSuccess: () => setSaved(true) },
    )
  }

  return (
    <Card>
      <h2 className="text-base font-semibold text-fg">{t('account.youTitle')}</h2>

      <div className="mt-4 flex flex-col gap-5">
        <PhotoInput
          label={t('account.photo')}
          hint={t('account.photoHint')}
          purpose="avatar"
          value={photo}
          onChange={setPhoto}
          round
        />

        <Field
          label={t('account.name')}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />

        <div className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-fg">{t('account.phone')}</span>
          <p className="numeric text-base font-semibold text-fg">{formatPhone(me.phone)}</p>
          <p className="text-sm text-fg-subtle">{t('account.phoneLocked')}</p>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="account-city" className="text-sm font-semibold text-fg">
            {t('account.city')}
          </label>
          <select
            id="account-city"
            value={cityId ?? ''}
            onChange={(event) => setCityId(Number(event.target.value) || null)}
            className="min-h-12 rounded-md border border-border-strong bg-surface px-3.5 text-fg outline-none focus:border-primary"
          >
            <option value="">—</option>
            {(cities.data ?? []).map((city) => (
              <option key={city.id} value={city.id}>
                {localisedName(city, language)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="account-language" className="text-sm font-semibold text-fg">
            {t('account.language')}
          </label>
          <select
            id="account-language"
            value={language}
            onChange={(event) => pickLanguage(event.target.value as Language)}
            className="min-h-12 rounded-md border border-border-strong bg-surface px-3.5 text-fg outline-none focus:border-primary"
          >
            {LANGUAGES.map((option) => (
              <option key={option} value={option}>
                {LANGUAGE_LABELS[option]}
              </option>
            ))}
          </select>
        </div>

        {me.provider && (
          <p className="text-sm text-fg-muted">
            {t('account.shopWindow')}{' '}
            <Link
              to="/pro/profile"
              className="font-semibold text-primary underline-offset-2 hover:underline"
            >
              {t('account.shopWindowLink')}
            </Link>
          </p>
        )}

        {edit.error && <Alert tone="danger">{message(edit.error)}</Alert>}
        {saved && !edit.isPending && <Alert tone="success">{t('account.saved')}</Alert>}

        {/* The one primary button on the screen. Everything below it is a
            secondary or a refusal. */}
        <div>
          <Button onClick={save} loading={edit.isPending} disabled={name.trim().length === 0}>
            {t('common.save')}
          </Button>
        </div>
      </div>
    </Card>
  )
}

function Password() {
  const { t } = useTranslation()
  const change = useChangePassword()
  const message = useErrorMessage()

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [done, setDone] = useState(false)

  const submit = () => {
    setDone(false)
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setDone(true)
          setCurrent('')
          setNext('')
        },
      },
    )
  }

  return (
    <Card>
      <h2 className="text-base font-semibold text-fg">{t('account.passwordTitle')}</h2>
      {/* The other end of P6: somebody signing in with a temporary password an
          admin read to him over the phone lands here to replace it. */}
      <p className="mt-1 text-sm text-fg-muted">{t('account.passwordBody')}</p>

      <div className="mt-4 flex flex-col gap-5">
        <Field
          label={t('account.currentPassword')}
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(event) => setCurrent(event.target.value)}
        />
        <Field
          label={t('account.newPassword')}
          hint={t('auth.passwordHint')}
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(event) => setNext(event.target.value)}
        />

        {change.error && <Alert tone="danger">{message(change.error)}</Alert>}
        {done && <Alert tone="success">{t('account.passwordChanged')}</Alert>}

        <div>
          <Button
            variant="secondary"
            onClick={submit}
            loading={change.isPending}
            disabled={current.length === 0 || next.length === 0}
          >
            {t('account.changePassword')}
          </Button>
        </div>
      </div>
    </Card>
  )
}

function Leaving() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const logout = useLogout()
  const commitments = useCommitments()
  const remove = useDeleteAccount()
  const message = useErrorMessage()

  // The second confirmation. Not a second "are you sure?" — the consequence
  // itself, ticked, so nobody closes an account without reading that the
  // number stays on it.
  const [understood, setUnderstood] = useState(false)

  const blocked = commitments.data && !commitments.data.can_delete

  return (
    <Card>
      <h2 className="text-base font-semibold text-fg">{t('account.leavingTitle')}</h2>

      <div className="mt-4 flex flex-col items-start gap-6">
        <Button
          variant="secondary"
          loading={logout.isPending}
          onClick={() => logout.mutate(undefined, { onSuccess: () => navigate('/') })}
        >
          {t('account.signOut')}
        </Button>

        <div className="w-full border-t border-border pt-6">
          <h3 className="text-sm font-semibold text-fg">{t('account.deleteTitle')}</h3>

          {commitments.isPending ? (
            <Skeleton className="mt-3 h-10" />
          ) : blocked ? (
            /* Refused before it is pressed, and named: finishing the job is
               what unblocks it, so say which one is holding him. */
            <Alert tone="warning" className="mt-3">
              {commitments.data.live_jobs > 0
                ? t('account.deleteBlockedJobs')
                : t('account.deleteBlockedDisputes')}
            </Alert>
          ) : (
            <>
              <p className="mt-2 text-sm text-fg-muted">{t('account.deleteBody')}</p>

              {remove.error && (
                <Alert tone="danger" className="mt-3">
                  {message(remove.error)}
                </Alert>
              )}

              <ConfirmButton
                className="mt-3"
                variant="danger"
                tone="danger"
                label={t('account.delete')}
                question={t('account.deleteQuestion')}
                confirmLabel={t('account.deleteConfirm')}
                loading={remove.isPending}
                confirmDisabled={!understood}
                onConfirm={() =>
                  remove.mutate(undefined, { onSuccess: () => navigate('/') })
                }
              >
                <label className="flex items-start gap-3 text-sm text-fg">
                  <input
                    type="checkbox"
                    checked={understood}
                    onChange={(event) => setUnderstood(event.target.checked)}
                    className="mt-0.5 size-4 accent-[var(--danger)]"
                  />
                  <span>{t('account.deleteUnderstand')}</span>
                </label>
              </ConfirmButton>
            </>
          )}
        </div>
      </div>
    </Card>
  )
}
