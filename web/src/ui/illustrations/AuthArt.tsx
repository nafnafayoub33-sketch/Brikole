import { Client, Tradesman } from '@/ui/illustrations/People'

/**
 * The scenes on the navy panels.
 *
 * They draw what the product does — somebody describes a job, a tradesman
 * answers with a price — because a decorative shape on a sign-in page teaches a
 * first-time visitor nothing. The city on the pin is the point of the whole
 * design: a plumber in Meknès is no use to somebody in Rabat, so the
 * illustration says where before it says how much.
 */

function OfferCard({
  x,
  y,
  width = 210,
  price,
  faded = false,
}: {
  x: number
  y: number
  width?: number
  price: string
  faded?: boolean
}) {
  const height = 74
  return (
    <g transform={`translate(${x} ${y})`} opacity={faded ? 0.55 : 1}>
      <rect
        width={width}
        height={height}
        rx="16"
        fill={faded ? 'rgb(255 255 255 / 0.14)' : '#ffffff'}
        stroke={faded ? 'rgb(255 255 255 / 0.22)' : 'transparent'}
        strokeWidth="1.5"
      />
      <circle cx="38" cy="37" r="17" fill={faded ? 'rgb(255 255 255 / 0.25)' : '#dce9f5'} />
      <circle cx="38" cy="32" r="6.5" fill={faded ? '#ffffff' : '#7fa8cc'} />
      <path
        d="M26 48c2.2-5.2 6.4-8 12-8s9.8 2.8 12 8Z"
        fill={faded ? '#ffffff' : '#7fa8cc'}
      />
      <rect
        x="66"
        y="20"
        width="74"
        height="9"
        rx="4.5"
        fill={faded ? 'rgb(255 255 255 / 0.5)' : '#103a5e'}
        opacity={faded ? 1 : 0.55}
      />
      <g fill={faded ? 'rgb(255 255 255 / 0.45)' : '#e8a33d'}>
        {[0, 17, 34].map((offset) => (
          <path
            key={offset}
            d={`M${66 + offset} 40l1.9 3.9 4.3.6-3.1 3 .7 4.3-3.8-2-3.8 2 .7-4.3-3.1-3 4.3-.6L${66 + offset} 40Z`}
          />
        ))}
      </g>
      <rect
        x={width - 76}
        y="22"
        width="60"
        height="30"
        rx="15"
        fill={faded ? 'rgb(255 255 255 / 0.28)' : '#103a5e'}
      />
      <text
        x={width - 46}
        y="42"
        textAnchor="middle"
        fontSize="15"
        fontWeight="700"
        fill="#ffffff"
        fontFamily="Inter, system-ui, sans-serif"
      >
        {price}
      </text>
    </g>
  )
}

function CityPin({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect
        x="24"
        y="-2"
        width={label.length * 8.4 + 34}
        height="34"
        rx="17"
        fill="rgb(255 255 255 / 0.16)"
        stroke="rgb(255 255 255 / 0.26)"
        strokeWidth="1.5"
      />
      <g stroke="#ffffff" strokeWidth="2" fill="none">
        <path d="M0 10c0-6.6 5.4-12 12-12s12 5.4 12 12c0 8.4-12 20-12 20S0 18.4 0 10Z" />
        <circle cx="12" cy="9.6" r="4" />
      </g>
      <text
        x="46"
        y="21"
        fontSize="14"
        fontWeight="600"
        fill="#ffffff"
        fontFamily="Inter, system-ui, sans-serif"
      >
        {label}
      </text>
    </g>
  )
}

/** For the auth panel: one tradesman, and the offers he sends. */
export function AuthArt({
  className = '',
  city = 'Casablanca',
}: {
  className?: string
  city?: string
}) {
  return (
    <svg
      viewBox="0 0 470 380"
      className={className}
      style={{ direction: 'ltr' }}
      role="img"
      aria-hidden
    >
      <ellipse cx="150" cy="330" rx="120" ry="16" fill="rgb(0 0 0 / 0.22)" />
      <Tradesman x={36} y={82} scale={0.94} />
      <CityPin x={36} y={26} label={city} />
      <OfferCard x={244} y={116} price="450" />
      <OfferCard x={262} y={214} width={186} price="520" faded />
      <path
        d="M232 196c26 6 34 14 34 28"
        stroke="rgb(255 255 255 / 0.3)"
        strokeWidth="1.8"
        strokeDasharray="5 7"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** For the landing hero: the client, the tradesman, and the offer between. */
export function HeroArt({
  className = '',
  city = 'Casablanca',
}: {
  className?: string
  city?: string
}) {
  return (
    <svg
      viewBox="0 0 560 400"
      className={className}
      style={{ direction: 'ltr' }}
      role="img"
      aria-hidden
    >
      <ellipse cx="118" cy="348" rx="104" ry="15" fill="rgb(0 0 0 / 0.2)" />
      <ellipse cx="418" cy="348" rx="116" ry="16" fill="rgb(0 0 0 / 0.2)" />

      <Client x={18} y={104} scale={0.9} />
      <Tradesman x={300} y={98} scale={0.94} />

      <path
        d="M186 176c50-34 108-34 150-8"
        stroke="rgb(255 255 255 / 0.3)"
        strokeWidth="1.8"
        strokeDasharray="5 7"
        fill="none"
        strokeLinecap="round"
      />

      <OfferCard x={172} y={22} price="450" />
      <CityPin x={392} y={40} label={city} />

      <g fill="rgb(255 255 255 / 0.22)">
        <circle cx="530" cy="150" r="4.5" />
        <circle cx="510" cy="196" r="3" />
        <circle cx="24" cy="70" r="4" />
      </g>
    </svg>
  )
}
