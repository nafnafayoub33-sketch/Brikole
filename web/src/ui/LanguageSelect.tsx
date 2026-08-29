import { useTranslation } from 'react-i18next'

import { LANGUAGES, LANGUAGE_LABELS, setLanguage, type Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'

/**
 * The language picker, as a real `<select>`.
 *
 * Three buttons in a row was fine at three languages and stops being fine the
 * moment there is a fourth; a select is also what a phone already knows how to
 * open, in a native wheel, without us building one.
 */
export function LanguageSelect({ className }: { className?: string }) {
  const { i18n, t } = useTranslation()
  const current = i18n.language as Language

  return (
    <div
      className={cn(
        'relative inline-flex items-center rounded-md border border-border bg-surface',
        'transition-colors duration-(--duration-fast) hover:border-border-strong',
        'focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/12',
        className,
      )}
    >
      <GlobeGlyph />
      <select
        aria-label={t('common.language')}
        value={current}
        onChange={(event) => void setLanguage(event.target.value as Language)}
        className="min-h-9 cursor-pointer appearance-none bg-transparent ps-1.5 pe-7 text-sm font-medium text-fg outline-none"
      >
        {LANGUAGES.map((language) => (
          <option key={language} value={language}>
            {LANGUAGE_LABELS[language]}
          </option>
        ))}
      </select>
      <ChevronGlyph />
    </div>
  )
}

function GlobeGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="pointer-events-none ms-2.5 size-4 shrink-0 text-fg-muted"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.4 2.6 3.6 5.6 3.6 9s-1.2 6.4-3.6 9c-2.4-2.6-3.6-5.6-3.6-9s1.2-6.4 3.6-9Z" />
    </svg>
  )
}

function ChevronGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="pointer-events-none absolute end-2 size-4 text-fg-subtle"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}
