import { useTranslation } from 'react-i18next'

import { formatCount } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { Button } from '@/ui/Button'

/**
 * Previous, where you are, next.
 *
 * Lifted out of A3 when A4 wanted the same thing. Two copies of a pager is how
 * one of them ends up letting somebody past the last page.
 *
 * The count is `formatCount`, not raw digits: page 3 of 21 sits beside prices
 * on these screens, and two numbering systems on one line is the bug this
 * project keeps having.
 */
export function Pager({
  page,
  pages,
  language,
  onChange,
}: {
  page: number
  pages: number
  language: Language
  onChange: (next: number) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-between gap-3">
      <Button
        size="sm"
        variant="secondary"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        {t('pager.previous')}
      </Button>

      <span className="numeric text-xs text-fg-subtle">
        {t('pager.pageOf', {
          page: formatCount(page, language),
          pages: formatCount(pages, language),
        })}
      </span>

      <Button
        size="sm"
        variant="secondary"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        {t('pager.next')}
      </Button>
    </div>
  )
}
