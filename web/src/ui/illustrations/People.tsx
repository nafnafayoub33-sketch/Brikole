/**
 * The people.
 *
 * Flat figures, drawn on a 160×260 local grid and placed with a transform, so
 * a scene composes them the way a photograph would. No faces beyond a hint:
 * a marketplace serves everybody, and the less specific the features, the more
 * readers see themselves in them.
 *
 * The palette is fixed rather than tokenised — skin and denim do not invert
 * with the theme, and both scenes sit on the navy panel in either one.
 */

const SKIN = { warm: '#e0ab84', deep: '#b97a53', light: '#f0c9a8' }
const HAIR = '#231a15'
const DENIM = '#2c4f74'
const DENIM_DARK = '#22405f'
const SHIRT = '#d7e3ef'
const SHIRT_ALT = '#cfe0ee'
const HELMET = '#e8a33d'
const BOOT = '#1a2a3d'
const TOOL = '#c05e46'

/** A tradesman: helmet, overalls, a wrench, and a toolbox at his feet. */
export function Tradesman({ x = 0, y = 0, scale = 1 }: { x?: number; y?: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      {/* boots */}
      <rect x="30" y="224" width="36" height="16" rx="7" fill={BOOT} />
      <rect x="82" y="224" width="36" height="16" rx="7" fill={BOOT} />

      {/* legs */}
      <rect x="40" y="146" width="24" height="84" rx="12" fill={DENIM_DARK} />
      <rect x="84" y="146" width="24" height="84" rx="12" fill={DENIM_DARK} />

      {/* sleeves */}
      <rect x="16" y="80" width="20" height="66" rx="10" fill={SHIRT} />
      <rect x="112" y="72" width="20" height="52" rx="10" fill={SHIRT} />

      {/* torso in overalls */}
      <rect x="30" y="72" width="88" height="86" rx="16" fill={DENIM} />
      <path d="M48 72v-12a8 8 0 0 1 16 0v12M84 72V60a8 8 0 0 1 16 0v12" fill={DENIM} />
      <rect x="56" y="104" width="36" height="26" rx="5" fill={DENIM_DARK} />

      {/* hands */}
      <circle cx="26" cy="150" r="10" fill={SKIN.warm} />
      <circle cx="122" cy="126" r="10" fill={SKIN.warm} />

      {/* the wrench in the raised hand */}
      <g transform="translate(118 92) rotate(18)">
        <rect x="0" y="0" width="8" height="40" rx="4" fill="#9aa8b8" />
        <path d="M-4 0a8 8 0 0 1 16 0l-4 4H0l-4-4Z" fill="#c3ccd8" />
      </g>

      {/* neck and head */}
      <rect x="60" y="50" width="24" height="26" rx="9" fill={SKIN.deep} />
      <circle cx="72" cy="36" r="26" fill={SKIN.warm} />
      <path d="M52 40a20 20 0 0 1 40 0v-6a20 20 0 0 0-40 0Z" fill={HAIR} />
      <path d="M62 46a10 10 0 0 0 20 0Z" fill={SKIN.deep} opacity="0.5" />

      {/* helmet */}
      <path
        d="M44 30a28 26 0 0 1 56 0v2h6a5 5 0 0 1 0 10H38a5 5 0 0 1 0-10h6Z"
        fill={HELMET}
      />
      <path d="M66 6h12v26H66Z" fill="#d18f2c" />

      {/* toolbox on the ground */}
      <rect x="134" y="196" width="72" height="44" rx="8" fill={TOOL} />
      <rect x="134" y="210" width="72" height="8" fill="#a04c37" />
      <path d="M156 196v-8a14 8 0 0 1 28 0v8" fill="none" stroke="#a04c37" strokeWidth="6" />
    </g>
  )
}

/** A client, phone in hand, reading the offers that came back. */
export function Client({ x = 0, y = 0, scale = 1 }: { x?: number; y?: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      {/* shoes */}
      <rect x="34" y="224" width="34" height="16" rx="7" fill={BOOT} />
      <rect x="82" y="224" width="34" height="16" rx="7" fill={BOOT} />

      {/* legs */}
      <rect x="42" y="150" width="24" height="80" rx="12" fill={DENIM} />
      <rect x="84" y="150" width="24" height="80" rx="12" fill={DENIM} />

      {/* torso */}
      <rect x="32" y="74" width="86" height="84" rx="18" fill={SHIRT_ALT} />
      <path d="M56 74h38l-8 20H64Z" fill={SHIRT} />

      {/* one arm down, one bent up holding the phone */}
      <rect x="18" y="82" width="19" height="64" rx="9.5" fill={SHIRT_ALT} />
      <circle cx="27.5" cy="150" r="9.5" fill={SKIN.light} />
      <path
        d="M114 88c10 4 14 14 10 24l-8 20"
        fill="none"
        stroke={SHIRT_ALT}
        strokeWidth="19"
        strokeLinecap="round"
      />
      <circle cx="112" cy="130" r="9.5" fill={SKIN.light} />

      {/* the phone */}
      <rect x="98" y="104" width="28" height="44" rx="6" fill="#12253a" />
      <rect x="102" y="109" width="20" height="34" rx="3" fill="#dbe8f4" />
      <rect x="105" y="114" width="14" height="3.5" rx="1.75" fill="#9fb6cb" />
      <rect x="105" y="121" width="10" height="3.5" rx="1.75" fill="#9fb6cb" />

      {/* neck and head */}
      <rect x="62" y="52" width="22" height="26" rx="9" fill={SKIN.warm} />
      <circle cx="73" cy="38" r="25" fill={SKIN.light} />
      <path
        d="M48 44c0-18 11-28 25-28s25 10 25 28c0 6-3 9-3 9V38c0-9-9-13-22-13S51 29 51 38v15s-3-3-3-9Z"
        fill={HAIR}
      />
      <path d="M94 40c8 2 11 10 9 20l-9-4Z" fill={HAIR} />
    </g>
  )
}

/** Stacked heads, for "N tradesmen work in this trade". */
export function AvatarStack({ count = 3, className = '' }: { count?: number; className?: string }) {
  const tones = [SKIN.warm, SKIN.light, SKIN.deep, SKIN.warm]

  return (
    <span className={`inline-flex -space-x-1.5 rtl:space-x-reverse ${className}`}>
      {Array.from({ length: count }, (_, index) => (
        <svg
          key={index}
          viewBox="0 0 32 32"
          className="size-6 rounded-full ring-2 ring-surface"
          aria-hidden
        >
          <rect width="32" height="32" rx="16" fill="#cfe0ee" />
          <circle cx="16" cy="13" r="6" fill={tones[index % tones.length]} />
          <path d="M4 32c1.6-7.4 6.2-11 12-11s10.4 3.6 12 11Z" fill={tones[index % tones.length]} />
        </svg>
      ))}
    </span>
  )
}
