/**
 * One line icon per trade.
 *
 * Drawn here rather than pulled from an icon library: `docs/SCREENS.md` puts a
 * trade grid on the landing page and in the request wizard, and a grid of
 * generic glyphs is what makes a marketplace look unfinished. They are strokes
 * on a 24-unit grid using `currentColor`, so they inherit the text colour and
 * work in both themes with nothing extra.
 *
 * The `icon` key comes from the `trades` table, so an admin adding a trade at
 * A6 picks one of these names. Anything unknown falls back to a toolbox.
 */

interface TradeIconProps {
  name: string
  className?: string
}

const PATHS: Record<string, React.ReactNode> = {
  // plumber
  droplet: (
    <>
      <path d="M12 3.5c0 0 5.8 6.1 5.8 10.1a5.8 5.8 0 1 1-11.6 0C6.2 9.6 12 3.5 12 3.5Z" />
      <path d="M9.6 14.2a2.5 2.5 0 0 0 2.4 2.6" />
    </>
  ),
  // electrician
  zap: <path d="M13.2 2.5 4.8 13.4h5.6l-1 8.1 8.8-11.2h-5.7l.7-7.8Z" />,
  // painter
  brush: (
    <>
      <path d="M14.4 3.6 20.4 9.6 12 18h-6v-6l8.4-8.4Z" />
      <path d="M6 12h6v6" />
      <path d="M4.2 20.4c1.2.6 2.6.3 3.4-.7" />
    </>
  ),
  // carpenter
  hammer: (
    <>
      <path d="M6.5 8.2 9.7 5c1.9-1.9 4.6-2 6-.6l2.4 2.4-2.5 2.5-1.4-1.4-1.6 1.6 1.4 1.4-2.5 2.5-2.4-2.4a3.1 3.1 0 0 1-.6-1.4Z" />
      <path d="M10.9 13.4 5.4 18.9a1.9 1.9 0 0 0 2.7 2.7l5.5-5.5" />
    </>
  ),
  // mobile car wash
  car: (
    <>
      <path d="M3.5 13.6 5.6 8.2A2 2 0 0 1 7.5 7h9a2 2 0 0 1 1.9 1.2l2.1 5.4v4.2h-17v-4.2Z" />
      <path d="M3.5 13.6h17" />
      <circle cx="7.5" cy="18" r="1.6" />
      <circle cx="16.5" cy="18" r="1.6" />
    </>
  ),
  // air conditioning
  wind: (
    <>
      <path d="M3 8.5h9.5a2.8 2.8 0 1 0-2.8-2.9" />
      <path d="M3 12.5h13a2.8 2.8 0 1 1-2.8 2.9" />
      <path d="M3 16.5h6.5" />
    </>
  ),
  // mason
  brick: (
    <>
      <rect x="3" y="5.5" width="18" height="13.5" rx="1.4" />
      <path d="M3 10h18M3 14.5h18" />
      <path d="M9 5.5V10M15 5.5V10M12 10v4.5M6 14.5V19M18 14.5V19" />
    </>
  ),
  // locksmith
  key: (
    <>
      <circle cx="8" cy="8" r="4.2" />
      <path d="M11 11 20 20" />
      <path d="M17.2 17.2 15.4 19M19 19l-1.8 1.8" />
    </>
  ),
  // tiler
  grid: (
    <>
      <rect x="3.5" y="3.5" width="7.5" height="7.5" rx="1.2" />
      <rect x="13" y="3.5" width="7.5" height="7.5" rx="1.2" />
      <rect x="3.5" y="13" width="7.5" height="7.5" rx="1.2" />
      <rect x="13" y="13" width="7.5" height="7.5" rx="1.2" />
    </>
  ),
  // gardener
  leaf: (
    <>
      <path d="M20 4C9.5 4 4 9.5 4 20c10.5 0 16-5.5 16-16Z" />
      <path d="M4 20 14 10" />
    </>
  ),
  // house cleaning
  sparkles: (
    <>
      <path d="M11 3.5 12.6 8 17 9.6 12.6 11.2 11 15.7 9.4 11.2 5 9.6 9.4 8 11 3.5Z" />
      <path d="M18 14.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" />
    </>
  ),
  // moving
  truck: (
    <>
      <path d="M2.8 6.5h10.4v9.8H2.8z" />
      <path d="M13.2 10h3.6l3.4 3.2v3.1h-7z" />
      <circle cx="7" cy="18" r="1.7" />
      <circle cx="17" cy="18" r="1.7" />
    </>
  ),
  // glazier
  square: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="1.5" />
      <path d="M12 3.5v17M3.5 12h17" />
    </>
  ),
  // appliance repair
  plug: (
    <>
      <path d="M9 3.5v5M15 3.5v5" />
      <path d="M6 8.5h12v2.2a6 6 0 0 1-6 6 6 6 0 0 1-6-6V8.5Z" />
      <path d="M12 16.7v3.8" />
    </>
  ),
  // welder — a mask, not a flame: a flame at 24px is a droplet with a notch
  flame: (
    <>
      <path d="M5 4.5h14v9.2a6.8 6.8 0 0 1-7 6.8 6.8 6.8 0 0 1-7-6.8V4.5Z" />
      <rect x="8" y="8.5" width="8" height="3.6" rx="1.2" />
      <path d="M9 16.5h6" />
    </>
  ),
  // antenna and satellite
  radio: (
    <>
      <path d="M3.6 12.4a8.8 8.8 0 0 0 8 8 8.8 8.8 0 0 0 .4-16.8 8.8 8.8 0 0 0-8.4 8.8Z" />
      <circle cx="11.8" cy="12.2" r="2" />
      <path d="M13.2 13.8 18 20.5M15 20.5h6" />
    </>
  ),
  // fallback
  tool: (
    <>
      <path d="M3.5 7.5h17v11a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5v-11Z" />
      <path d="M8.5 7.5V5.8A1.8 1.8 0 0 1 10.3 4h3.4a1.8 1.8 0 0 1 1.8 1.8v1.7" />
      <path d="M3.5 12.5h17" />
    </>
  ),
}

export function TradeIcon({ name, className = 'size-6' }: TradeIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {PATHS[name] ?? PATHS.tool}
    </svg>
  )
}
