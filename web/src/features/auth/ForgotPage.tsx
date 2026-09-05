import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { AuthLayout } from '@/app/layouts/AuthLayout'
import { Alert } from '@/ui/Alert'

/** The three steps, in the order they happen. */
const STEPS = ['auth.forgotStep1', 'auth.forgotStep2', 'auth.forgotStep3']

/**
 * P6 — honest about what does not exist yet. SMS reset lands in Phase 4.
 *
 * Until then the reset is a phone call, and a screen that only says so is a
 * dead end: somebody who has just been locked out needs to know who does it,
 * what he will be asked for, and that the password he is given is temporary.
 * A3 is the other half — `StaffService.reset_password` is the admin's end of
 * this same call.
 */
export function ForgotPage() {
  const { t } = useTranslation()

  return (
    <AuthLayout promises={[t('auth.promise1'), t('auth.promise2'), t('auth.promise3')]}>
      <h1 className="text-3xl font-bold text-fg">{t('auth.forgot')}</h1>

      <div className="mt-6">
        <Alert tone="info">{t('auth.forgotBody')}</Alert>
      </div>

      <h2 className="mt-8 text-sm font-semibold text-fg">{t('auth.forgotHow')}</h2>
      {/* `ms-5`, not `ml-5`: the marker sits on the start side in all three
          languages. */}
      <ol className="mt-3 flex list-decimal flex-col gap-2 ms-5 text-sm text-fg-muted">
        {STEPS.map((step) => (
          <li key={step}>{t(step)}</li>
        ))}
      </ol>

      <p className="mt-6 text-sm text-fg-subtle">{t('auth.forgotBring')}</p>

      <p className="mt-8 text-sm">
        <Link
          to="/login"
          className="font-semibold text-primary underline-offset-4 hover:underline"
        >
          {t('common.back')}
        </Link>
      </p>
    </AuthLayout>
  )
}
