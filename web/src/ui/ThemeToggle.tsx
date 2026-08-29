import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { readStoredTheme, storeTheme, type ThemeChoice } from '@/ui/theme'
import { cn } from '@/ui/cn'

const DARK_QUERY = '(prefers-color-scheme: dark)'

/** What the reader is actually looking at, which is what the icon must match. */
function resolve(choice: ThemeChoice): 'light' | 'dark' {
  if (choice !== 'system') return choice
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

/**
 * One button: a moon while the page is light, a sun while it is dark.
 *
 * A three-way control for something the reader judges by looking at the screen
 * is a control too many. The stored choice still starts at `system`; the first
 * press just makes it explicit.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { t } = useTranslation()
  const [choice, setChoice] = useState<ThemeChoice>(() => readStoredTheme())
  const [effective, setEffective] = useState<'light' | 'dark'>(() => resolve(readStoredTheme()))

  // While the choice is `system`, the reader's OS can change underneath us and
  // the icon has to follow it.
  useEffect(() => {
    setEffective(resolve(choice))
    if (choice !== 'system') return

    const media = window.matchMedia(DARK_QUERY)
    const onChange = () => setEffective(media.matches ? 'dark' : 'light')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [choice])

  const next: ThemeChoice = effective === 'dark' ? 'light' : 'dark'

  return (
    <button
      type="button"
      onClick={() => {
        storeTheme(next)
        setChoice(next)
      }}
      aria-label={t(next === 'dark' ? 'common.themeDark' : 'common.themeLight')}
      title={t(next === 'dark' ? 'common.themeDark' : 'common.themeLight')}
      className={cn(
        'inline-flex size-9 items-center justify-center rounded-md border border-border bg-surface text-fg-muted',
        'transition-colors duration-(--duration-fast) hover:border-border-strong hover:text-fg',
        className,
      )}
    >
      {effective === 'dark' ? <SunGlyph /> : <MoonGlyph />}
    </button>
  )
}

function MoonGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-4.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M20.5 14.2A8.6 8.6 0 0 1 9.8 3.5a8.8 8.8 0 1 0 10.7 10.7Z" />
    </svg>
  )
}

function SunGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-4.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.6v2.2M12 19.2v2.2M4.4 4.4l1.6 1.6M18 18l1.6 1.6M2.6 12h2.2M19.2 12h2.2M4.4 19.6 6 18M18 6l1.6-1.6" />
    </svg>
  )
}
