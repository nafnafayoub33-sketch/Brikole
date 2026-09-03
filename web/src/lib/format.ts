/**
 * Formatting for humans. The only place a raw value becomes a string.
 *
 * Money is integer centimes everywhere else in the codebase; it becomes
 * "1 200,00 DH" here and nowhere earlier.
 */

import type { Language } from '@/lib/i18n'

const CENTIMES_PER_DIRHAM = 100

/**
 * Centimes to a displayable amount.
 *
 * Latin digits in all three languages, deliberately: prices, phone numbers and
 * reference numbers are read as numbers by everyone in Morocco, including
 * people reading the Arabic interface. `ar-MA-u-nu-latn` is what pins that.
 */
export function formatDH(centimes: number, language: Language = 'ar'): string {
  const amount = centimes / CENTIMES_PER_DIRHAM
  const locale = localeFor(language)
  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
  return `${formatted} DH`
}

/** Whole dirhams, for a price that has no centimes worth showing. */
export function formatDirhams(centimes: number, language: Language = 'ar'): string {
  const locale = localeFor(language)
  const formatted = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(
    Math.round(centimes / CENTIMES_PER_DIRHAM),
  )
  return `${formatted} DH`
}

/** Wrap a value so it keeps its own direction inside a sentence in another.
 *
 *  `550 DH` interpolated into an Arabic line renders as `DH 550` — the Latin
 *  run is laid out by the paragraph's direction unless it is isolated. CSS
 *  cannot reach inside an interpolated string, so the isolate travels with the
 *  value: U+2066 LEFT-TO-RIGHT ISOLATE … U+2069 POP DIRECTIONAL ISOLATE. */
export function isolate(text: string): string {
  return `\u2066${text}\u2069`
}

/** A plain count: `1073` → `1.073`, in the same grouping the prices use.
 *  Two separators on one screen — `1,073` beside `10.700 DH` — reads as two
 *  different numbering systems, which is exactly what it is. */
export function formatCount(value: number, language: Language = 'ar'): string {
  return new Intl.NumberFormat(localeFor(language)).format(value)
}

/** A range, for a budget. One side missing still reads correctly. */
export function formatBudget(
  minCentimes: number | null,
  maxCentimes: number | null,
  language: Language = 'ar',
): string | null {
  if (minCentimes == null && maxCentimes == null) return null
  if (minCentimes != null && maxCentimes != null) {
    return `${formatDirhams(minCentimes, language)} – ${formatDirhams(maxCentimes, language)}`
  }
  return formatDirhams((minCentimes ?? maxCentimes) as number, language)
}

/** `+212612345678` → `06 12 34 56 78`. Display only; the stored form is E.164. */
export function formatPhone(e164: string): string {
  if (!e164.startsWith('+212')) return e164
  const national = `0${e164.slice(4)}`
  return national.replace(/^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/, '$1 $2 $3 $4 $5')
}

export function formatDate(iso: string, language: Language = 'ar'): string {
  return new Intl.DateTimeFormat(localeFor(language), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

export function formatDateTime(iso: string, language: Language = 'ar'): string {
  return new Intl.DateTimeFormat(localeFor(language), {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

const MINUTE = 60_000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/** "3 hours ago". Used for how long a request has been waiting for offers. */
export function formatRelative(iso: string, language: Language = 'ar', now = Date.now()): string {
  const elapsed = new Date(iso).getTime() - now
  const relative = new Intl.RelativeTimeFormat(localeFor(language), { numeric: 'auto' })

  const absolute = Math.abs(elapsed)
  if (absolute < HOUR) return relative.format(Math.round(elapsed / MINUTE), 'minute')
  if (absolute < DAY) return relative.format(Math.round(elapsed / HOUR), 'hour')
  return relative.format(Math.round(elapsed / DAY), 'day')
}

/** `2026-08` → `août`, or `غشت`. The A1 trend labels its columns with these. */
export function formatMonth(month: string, language: Language = 'ar'): string {
  return new Intl.DateTimeFormat(localeFor(language), { month: 'short' }).format(
    firstOfMonth(month),
  )
}

/** The same month with its year, for a tooltip where the column has no axis. */
export function formatMonthLong(month: string, language: Language = 'ar'): string {
  return new Intl.DateTimeFormat(localeFor(language), {
    month: 'long',
    year: 'numeric',
  }).format(firstOfMonth(month))
}

/** `2026-08` is a month, not a day. UTC, so a negative offset cannot roll it
 *  back into July and label the column with the wrong month. */
function firstOfMonth(month: string): Date {
  const year = Number(month.slice(0, 4))
  const index = Number(month.slice(5, 7))
  return new Date(Date.UTC(year, index - 1, 1))
}

function localeFor(language: Language): string {
  // `-u-nu-latn` forces Latin digits, which is the point.
  return { ar: 'ar-MA-u-nu-latn', fr: 'fr-MA', en: 'en-MA' }[language]
}
