import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { cn } from '@/ui/cn'

/**
 * The search box, in the header where it belongs.
 *
 * It lands on P2 with the term in the URL, so a result page can be shared,
 * bookmarked and reloaded — a search that only lives in component state is a
 * search nobody can send to anybody.
 */
export function HeaderSearch({ className }: { className?: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [query, setQuery] = useState(() => params.get('q') ?? '')

  function submit(event: FormEvent) {
    event.preventDefault()
    const term = query.trim()
    navigate(term ? `/services?q=${encodeURIComponent(term)}` : '/services')
  }

  return (
    <form
      onSubmit={submit}
      role="search"
      className={cn(
        'flex min-w-0 items-center rounded-md border border-border-strong bg-surface',
        'transition-colors duration-(--duration-fast)',
        'focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/12',
        className,
      )}
    >
      <label htmlFor="header-search" className="sr-only">
        {t('header.searchPlaceholder')}
      </label>
      <SearchGlyph />
      <input
        id="header-search"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={t('header.searchPlaceholder')}
        className="min-h-10 w-full min-w-0 bg-transparent px-2 text-sm text-fg outline-none placeholder:text-fg-subtle"
      />
      <button
        type="submit"
        className="m-1 shrink-0 rounded-sm bg-primary px-3.5 py-2 text-sm font-semibold text-primary-fg transition-colors duration-(--duration-fast) hover:bg-primary-hover"
      >
        {t('landing.searchCta')}
      </button>
    </form>
  )
}

function SearchGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="ms-3 size-4.5 shrink-0 text-fg-subtle"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 4 4" />
    </svg>
  )
}
