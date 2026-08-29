import { useTranslation } from 'react-i18next'

import { ApiError } from '@/data/client'

/**
 * Turn whatever went wrong into a sentence, in the reader's language.
 *
 * This is the other half of the API's contract: the server sends a code, this
 * turns it into words. A code with no translation falls back to the generic
 * message rather than showing the reader a raw identifier.
 */
export function useErrorMessage(): (error: unknown) => string | null {
  const { t, i18n } = useTranslation()

  return (error: unknown) => {
    if (!error) return null

    if (!(error instanceof ApiError)) return t('errors.generic')
    if (error.isNetwork) return t('errors.network')

    const key = `errors.${error.code}`
    if (!i18n.exists(key)) return t('errors.generic')

    // A lockout is only useful if it says for how long.
    if (error.code === 'account_locked') {
      const seconds = Number(error.details.retry_after_seconds ?? 0)
      return t(key, { minutes: Math.max(1, Math.ceil(seconds / 60)) })
    }

    return t(key)
  }
}
