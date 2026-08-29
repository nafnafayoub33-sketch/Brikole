import { useTranslation } from 'react-i18next'

import { useErrorMessage } from '@/hooks/useErrorMessage'
import { Button } from '@/ui/Button'

/** The error state every list screen owes the reader — with a way to retry. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation()
  const message = useErrorMessage()

  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-lg border border-danger/30 bg-danger-soft px-6 py-10 text-center"
    >
      <p className="text-sm text-fg">{message(error)}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {t('common.retry')}
        </Button>
      )}
    </div>
  )
}
