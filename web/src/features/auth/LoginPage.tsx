import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { AuthLayout } from '@/app/layouts/AuthLayout'
import { useLogin, useSession } from '@/data/auth'
import { useErrorMessage } from '@/hooks/useErrorMessage'
import { Alert } from '@/ui/Alert'
import { Button } from '@/ui/Button'
import { Field, PasswordField } from '@/ui/Field'

/** P4 — phone and password. */
export function LoginPage() {
  const { t } = useTranslation()
  const location = useLocation()
  const { data: user } = useSession()
  const login = useLogin()
  const message = useErrorMessage()

  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')

  if (user) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? user.home_path} replace />
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    login.mutate({ phone, password })
  }

  return (
    <AuthLayout promises={[t('auth.promise1'), t('auth.promise2'), t('auth.promise3')]}>
      <h1 className="text-3xl font-bold text-fg">{t('auth.loginTitle')}</h1>
      <p className="mt-2 text-fg-muted">{t('auth.loginSubtitle')}</p>

      <form onSubmit={submit} className="mt-8 flex flex-col gap-5" noValidate>
        {login.isError && <Alert tone="danger">{message(login.error)}</Alert>}

        <Field
          label={t('auth.phone')}
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
          autoComplete="current-password"
          revealLabel={t('auth.show')}
          hideLabel={t('auth.hide')}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        <div className="-mt-1 flex justify-end">
          <Link
            to="/forgot"
            className="text-sm font-medium text-fg-muted underline-offset-4 hover:text-primary hover:underline"
          >
            {t('auth.forgot')}
          </Link>
        </div>

        <Button type="submit" size="lg" fullWidth loading={login.isPending}>
          {t('auth.loginCta')}
        </Button>
      </form>

      <p className="mt-8 text-sm text-fg-muted">
        {t('auth.noAccount')}{' '}
        <Link
          to="/register"
          className="font-semibold text-primary underline-offset-4 hover:underline"
        >
          {t('common.signUp')}
        </Link>
      </p>
    </AuthLayout>
  )
}
