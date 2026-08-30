import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { formatDirhams } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'
import { Card } from '@/ui/Card'

/**
 * What M4 and M5 show instead of work he cannot take.
 *
 * It says the number, says when it is charged, and gives him the one action
 * that fixes it. A tradesman who is blocked and not told why assumes the
 * platform is broken and does not come back.
 */
export function OutOfCredit({
  feeCentimes,
  language,
}: {
  feeCentimes: number
  language: Language
}) {
  const { t } = useTranslation()

  return (
    <Card className="mx-auto max-w-xl text-center">
      <span
        aria-hidden
        className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-warning-soft"
      >
        <WalletGlyph />
      </span>
      <h2 className="text-xl font-bold text-fg">{t('feed.blockedTitle')}</h2>
      <p className="mt-3 text-fg-muted">
        {t('feed.blockedBody', { fee: formatDirhams(feeCentimes, language) })}
      </p>
      <Link to="/pro/credit" className="mt-6 inline-block">
        <Button size="pro">{t('feed.blockedCta')}</Button>
      </Link>
    </Card>
  )
}

function WalletGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-7 text-warning"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H18a1 1 0 0 1 1 1v2" />
      <rect x="3" y="7.5" width="18" height="12" rx="2.5" />
      <path d="M16 13.5h2.5" />
    </svg>
  )
}
