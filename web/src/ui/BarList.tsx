import type { ReactNode } from 'react'

import { cn } from '@/ui/cn'

export interface BarRow {
  id: string
  label: string
  /** What the bar length encodes. */
  value: number
  /** Shown at the end of the row, already formatted. */
  display: string
  /** A second fact about the row — money, people — as words, never a bar. */
  note?: ReactNode
}

/**
 * A ranked list of categories: label, bar, number.
 *
 * Twenty cities and sixteen trades are past the point where colour can carry
 * identity, so this is the form the data asks for — a table with the bar
 * drawn in it. Every bar is the same hue: the categories have no order of
 * their own, and colouring them by size would spend the identity channel
 * repeating what the length already says.
 *
 * Built from divs rather than SVG so it flips with the page: in Arabic the
 * bars grow from the right, which is where the reader starts.
 */
export function BarList({
  rows,
  emptyLabel,
  max: given,
}: {
  rows: BarRow[]
  emptyLabel: string
  /** Force the scale — pass it when two lists must be read against each other. */
  max?: number
}) {
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-fg-subtle">{emptyLabel}</p>
  }

  const max = given ?? Math.max(...rows.map((row) => row.value), 1)

  return (
    <ol className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.id} className="grid grid-cols-[9rem_1fr_auto] items-center gap-3">
          <span className="truncate text-sm text-fg" title={row.label}>
            {row.label}
          </span>

          {/* The track is a lighter step of the same ramp, so an empty row still
              reads as a row rather than as missing data. */}
          <span className="h-3 rounded-pill bg-chart-track">
            <span
              className="block h-3 rounded-pill bg-chart-fill"
              style={{ inlineSize: `${Math.max((row.value / max) * 100, row.value > 0 ? 2 : 0)}%` }}
            />
          </span>

          <span className="flex items-baseline gap-2 justify-self-end">
            <span className="numeric text-sm font-semibold text-fg">{row.display}</span>
            {row.note && <span className="text-xs text-fg-subtle">{row.note}</span>}
          </span>
        </li>
      ))}
    </ol>
  )
}

/** A section heading for a chart: the title carries what is plotted, so a
 *  one-series chart needs no legend box under it. */
export function ChartHeader({
  title,
  hint,
  className,
}: {
  title: string
  hint?: string
  className?: string
}) {
  return (
    <div className={cn('mb-4', className)}>
      <h2 className="text-base font-semibold text-fg">{title}</h2>
      {hint && <p className="mt-1 text-xs text-fg-subtle">{hint}</p>}
    </div>
  )
}
