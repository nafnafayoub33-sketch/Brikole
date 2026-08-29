import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

/** S1 */
export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto flex max-w-prose flex-col items-center gap-3 px-6 py-24 text-center">
      <h1 className="text-xl font-semibold text-fg">{t('notFound.title')}</h1>
      <Link
        to="/"
        className="inline-flex min-h-tap items-center rounded-md border border-border-strong bg-surface px-4 text-sm font-medium text-fg hover:bg-surface-2"
      >
        {t('notFound.cta')}
      </Link>
    </div>
  )
}
