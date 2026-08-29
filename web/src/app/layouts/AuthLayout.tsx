import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { AuthArt } from '@/ui/illustrations/AuthArt'
import { Logo, LogoOnBrand } from '@/ui/illustrations/Logo'
import { LanguageSelect } from '@/ui/LanguageSelect'
import { ThemeToggle } from '@/ui/ThemeToggle'

/**
 * The frame P4, P5 and P6 sit in.
 *
 * Two columns: the form on paper, and a navy panel carrying the illustration
 * and the three promises. The panel is `hidden lg:flex` — on a phone the form
 * is the whole screen, which is where most of these accounts will be made.
 *
 * The columns are ordinary grid children, so `dir="rtl"` mirrors them and the
 * panel moves to the other side without a second layout.
 */
export function AuthLayout({
  children,
  promises,
}: {
  children: ReactNode
  promises: string[]
}) {
  const { t } = useTranslation()

  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,46%)]">
      <div className="flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" aria-label={t('common.appName')}>
            <Logo />
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <LanguageSelect />
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>

      <aside className="brand-panel relative hidden overflow-hidden lg:flex lg:flex-col">
        <div className="brand-grid absolute inset-0 opacity-60" aria-hidden />

        <div className="relative p-10">
          <LogoOnBrand />
        </div>

        <div className="relative flex min-h-0 flex-1 items-center px-10">
          <AuthArt className="mx-auto max-h-full w-full max-w-lg" />
        </div>

        <ul className="relative flex flex-col gap-3 p-10">
          {promises.map((promise) => (
            <li key={promise} className="flex items-start gap-3 text-sm text-fg-on-brand">
              <svg
                viewBox="0 0 20 20"
                className="mt-0.5 size-5 shrink-0"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <circle cx="10" cy="10" r="8.5" strokeOpacity="0.4" />
                <path d="m6.5 10.4 2.4 2.4 4.6-5" />
              </svg>
              <span>{promise}</span>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
