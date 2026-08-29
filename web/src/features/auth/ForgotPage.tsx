import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { AuthLayout } from '@/app/layouts/AuthLayout'
import { Alert } from '@/ui/Alert'

/** P6 — honest about what does not exist yet. SMS reset lands in Phase 4. */
export function ForgotPage() {
  const { t } = useTranslation()

  return (
    <AuthLayout promises={[t('auth.promise1'), t('auth.promise2'), t('auth.promise3')]}>
      <h1 className="text-3xl font-bold text-fg">{t('auth.forgot')}</h1>
      <div className="mt-6">
        <Alert tone="info">{t('auth.forgotBody')}</Alert>
      </div>
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
