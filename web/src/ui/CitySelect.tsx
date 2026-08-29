import { useTranslation } from 'react-i18next'

import { useCities } from '@/data/catalog'
import { useCityStore } from '@/data/cityPreference'
import { localisedName } from '@/data/types'
import type { Language } from '@/lib/i18n'
import { cn } from '@/ui/cn'

/**
 * Where the work is.
 *
 * Sits beside the search box rather than behind a filter, because it is not a
 * refinement — it is half the question. Everything the visitor is then shown
 * is counted inside this city.
 */
export function CitySelect({
  className,
  onBrand = false,
}: {
  className?: string
  onBrand?: boolean
}) {
  const { t, i18n } = useTranslation()
  const language = i18n.language as Language
  const cities = useCities()
  const { cityId, setCity } = useCityStore()

  return (
    <div
      className={cn(
        'relative flex items-center rounded-md',
        onBrand ? 'bg-white' : 'border border-border-strong bg-surface',
        className,
      )}
    >
      <PinGlyph />
      <select
        aria-label={t('landing.city')}
        value={cityId ?? ''}
        onChange={(event) => setCity(event.target.value === '' ? null : Number(event.target.value))}
        disabled={cities.isPending}
        className={cn(
          'min-h-12 w-full cursor-pointer appearance-none bg-transparent ps-1.5 pe-8 text-sm font-medium outline-none',
          onBrand ? 'text-navy-900' : 'text-fg',
        )}
      >
        <option value="">{t('landing.cityAll')}</option>
        {cities.data?.map((city) => (
          <option key={city.id} value={city.id}>
            {localisedName(city, language)}
          </option>
        ))}
      </select>
      <ChevronGlyph onBrand={onBrand} />
    </div>
  )
}

function PinGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="pointer-events-none ms-3 size-4.5 shrink-0 text-fg-subtle"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 21s7-6.6 7-11.4A7 7 0 0 0 5 9.6C5 14.4 12 21 12 21Z" />
      <circle cx="12" cy="9.6" r="2.6" />
    </svg>
  )
}

function ChevronGlyph({ onBrand }: { onBrand: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn(
        'pointer-events-none absolute end-2.5 size-4',
        onBrand ? 'text-navy-600' : 'text-fg-subtle',
      )}
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
