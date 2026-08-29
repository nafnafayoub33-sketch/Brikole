import { useTranslation } from 'react-i18next'

/**
 * A placeholder that names the screen it stands in for.
 *
 * Every id here exists in docs/SCREENS.md — the point is that nobody has to
 * guess whether a blank page is a bug or a phase that has not landed.
 */
export function NotBuilt({ screen }: { screen: string }) {
  const { t } = useTranslation()

  return (
    <div className="mx-auto flex max-w-prose flex-col items-center gap-2 px-6 py-16 text-center">
      <span className="numeric rounded-md bg-surface-inset px-2.5 py-1 text-xs font-semibold text-fg-muted">
        {screen}
      </span>
      <h1 className="text-lg font-semibold text-fg">{t('notBuilt.title')}</h1>
      <p className="text-sm text-fg-muted">{t('notBuilt.body', { screen })}</p>
    </div>
  )
}
