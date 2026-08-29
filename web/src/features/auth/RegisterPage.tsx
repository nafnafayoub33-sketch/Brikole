import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate } from 'react-router-dom'

import { AuthLayout } from '@/app/layouts/AuthLayout'
import { useRegister, useSession } from '@/data/auth'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import type { Language } from '@/lib/i18n'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Field, PasswordField } from '@/ui/Field'
import { cn } from '@/ui/cn'

type SelfRegisterableRole = 'client' | 'provider'

/**
 * P5 — the two cards, then the account.
 *
 * Only `client` and `provider` are offered, and the API refuses anything else
 * regardless of what is posted: hiding a control is not a control.
 */
export function RegisterPage() {
  const { t, i18n } = useTranslation()
  const { data: user } = useSession()
  const register = useRegister()
  const message = useErrorMessage()

  const [role, setRole] = useState<SelfRegisterableRole>('client')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')

  if (user) return <Navigate to={user.home_path} replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    register.mutate({
      phone,
      full_name: fullName,
      password,
      role,
      language: i18n.language as Language,
    })
  }

  return (
    <AuthLayout promises={[t('auth.promise1'), t('auth.promise2'), t('auth.promise3')]}>
      <h1 className="text-3xl font-bold text-fg">{t('auth.registerTitle')}</h1>
      <p className="mt-2 text-fg-muted">{t('auth.registerSubtitle')}</p>

      <fieldset className="mt-7">
        <legend className="mb-3 text-sm font-semibold text-fg">{t('auth.chooseRole')}</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {(['client', 'provider'] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={role === option}
              onClick={() => setRole(option)}
              className={cn(
                'group relative flex flex-col gap-1.5 rounded-md border-2 p-4 text-start',
                'transition-all duration-(--duration-fast)',
                role === option
                  ? 'border-primary bg-primary-soft shadow-sm'
                  : 'border-border bg-surface hover:border-border-strong',
              )}
            >
              <span
                aria-hidden
                className={cn(
                  'mb-1 flex size-9 items-center justify-center rounded-md',
                  role === option
                    ? 'bg-primary text-primary-fg'
                    : 'bg-surface-inset text-fg-muted',
                )}
              >
                {option === 'client' ? <HouseGlyph /> : <ToolboxGlyph />}
              </span>
              <span className="font-semibold text-fg">
                {t(option === 'client' ? 'auth.roleClientTitle' : 'auth.roleProviderTitle')}
              </span>
              <span className="text-xs leading-relaxed text-fg-muted">
                {t(option === 'client' ? 'auth.roleClientBody' : 'auth.roleProviderBody')}
              </span>
            </button>
          ))}
        </div>
        <p className="mt-2.5 text-xs text-fg-subtle">{t('auth.roleLockedNote')}</p>
      </fieldset>

      <form onSubmit={submit} className="mt-7 flex flex-col gap-5" noValidate>
        {register.isError && <Alert tone="danger">{message(register.error)}</Alert>}

        <Field
          label={t('auth.fullName')}
          autoComplete="name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          required
        />
        <Field
          label={t('auth.phone')}
          hint={t('auth.phoneHint')}
          prefix="+212"
          numeric
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="612 345 678"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          required
        />
        <PasswordField
          label={t('auth.password')}
          hint={t('auth.passwordHint')}
          autoComplete="new-password"
          revealLabel={t('auth.show')}
          hideLabel={t('auth.hide')}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <Button type="submit" size="lg" fullWidth loading={register.isPending}>
          {t('auth.registerCta')}
        </Button>
      </form>

      <p className="mt-8 text-sm text-fg-muted">
        {t('auth.haveAccount')}{' '}
        <Link to="/login" className="font-semibold text-primary underline-offset-4 hover:underline">
          {t('common.signIn')}
        </Link>
      </p>
    </AuthLayout>
  )
}

function HouseGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9.5Z" />
      <path d="M9.5 21v-6h5v6" />
    </svg>
  )
}

function ToolboxGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M3.5 8.5h17V19a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V8.5Z" />
      <path d="M8.5 8.5V6.8A1.8 1.8 0 0 1 10.3 5h3.4a1.8 1.8 0 0 1 1.8 1.8v1.7" />
      <path d="M3.5 13.5h17" />
    </svg>
  )
}
