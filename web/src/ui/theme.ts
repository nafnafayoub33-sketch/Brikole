/**
 * The design tokens, as TypeScript.
 *
 * The *values* live in `src/styles.css` — this file names them so code that
 * genuinely needs a token outside a class (an inline SVG fill, a canvas, a
 * meta theme-color) references the same variable rather than pasting a hex.
 * There is one source of truth and it is the stylesheet.
 */

export const color = {
  bg: 'var(--bg)',
  surface: 'var(--surface)',
  surface2: 'var(--surface-2)',
  surfaceInset: 'var(--surface-inset)',
  surfaceBrand: 'var(--surface-brand)',

  fg: 'var(--fg)',
  fgMuted: 'var(--fg-muted)',
  fgSubtle: 'var(--fg-subtle)',
  fgOnBrand: 'var(--fg-on-brand)',

  border: 'var(--border)',
  borderStrong: 'var(--border-strong)',

  primary: 'var(--primary)',
  primaryHover: 'var(--primary-hover)',
  primaryFg: 'var(--primary-fg)',
  primarySoft: 'var(--primary-soft)',

  accent: 'var(--accent)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  danger: 'var(--danger)',
  star: 'var(--star)',
  focus: 'var(--focus)',
} as const

/** Depth. Cards lift, the primary action lifts a little more, sheets lift most. */
export const shadow = {
  sm: 'var(--shadow-sm)',
  md: 'var(--shadow-md)',
  lg: 'var(--shadow-lg)',
  brand: 'var(--shadow-brand)',
} as const

export const radius = {
  sm: 'var(--radius-sm)',
  md: 'var(--radius-md)',
  lg: 'var(--radius-lg)',
  xl: 'var(--radius-xl)',
  pill: 'var(--radius-pill)',
} as const

/**
 * The motion budget. Motion is for something real changing — a sheet opening,
 * a row leaving a list. Nothing decorative, and nothing slower than `slow`.
 */
export const duration = {
  fast: 'var(--duration-fast)',
  base: 'var(--duration-base)',
  slow: 'var(--duration-slow)',
} as const

/** Minimum touch targets. `pro` is for the tradesman's own screens. */
export const tapSize = {
  min: 'min-h-tap',
  pro: 'min-h-tap-pro',
} as const

export type ThemeChoice = 'light' | 'dark' | 'system'

const THEME_STORAGE_KEY = 'brikole.theme'

/**
 * Apply a theme choice to the document.
 *
 * `system` removes the attribute entirely so the stylesheet's
 * `prefers-color-scheme` block takes over — rather than us guessing what the
 * system preference currently is and baking it in.
 */
export function applyTheme(choice: ThemeChoice): void {
  const root = document.documentElement

  // Every colour changes at once here. Muting transitions across the swap
  // stops the page cross-fading between two palettes, which is motion that
  // reports nothing.
  root.classList.add('theme-switching')

  if (choice === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', choice)
  }

  // Read a layout property to flush the change before transitions come back.
  void root.offsetHeight
  requestAnimationFrame(() => root.classList.remove('theme-switching'))
}

export function readStoredTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // Private mode, or site data blocked. The default is a fine answer.
  }
  return 'system'
}

export function storeTheme(choice: ThemeChoice): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, choice)
  } catch {
    // Not being able to remember the choice is not a reason to fail to apply it.
  }
  applyTheme(choice)
}
