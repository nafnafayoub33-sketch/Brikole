import { useState } from 'react'

export interface ColumnPoint {
  id: string
  /** Under the column. Keep it to a few characters. */
  label: string
  /** A second line under the label, printed only where it changes — the year,
   *  so thirteen months do not show "sept." twice with nothing to tell them
   *  apart. */
  sublabel?: string
  /** What the height encodes. */
  value: number
  /** The whole truth about this column, for the tooltip. */
  detail: string
}

/**
 * A trend over time: one series, one hue, columns.
 *
 * Built from divs rather than SVG because it has to be responsive and hold
 * real text: an SVG that scales to its container scales its labels with it,
 * and a 9px month name is not a label.
 *
 * The chart is pinned LTR in all three languages. Time is a number line, and
 * this codebase already keeps numbers, prices and dates reading left to right
 * in Arabic — a trend that ran backwards would be the one exception.
 */
export function ColumnChart({
  points,
  ticks,
  formatTick,
  emptyLabel,
}: {
  points: ColumnPoint[]
  /** How many gridlines above the baseline. */
  ticks?: number
  formatTick: (value: number) => string
  emptyLabel: string
}) {
  const [hovered, setHovered] = useState<string | null>(null)

  const max = Math.max(...points.map((point) => point.value), 0)
  if (points.length === 0 || max === 0) {
    return <p className="py-8 text-center text-sm text-fg-subtle">{emptyLabel}</p>
  }

  // Round the top of the scale up to something a person would say out loud, so
  // the tick labels are 0 / 25 / 50, never 0 / 23 / 46.
  const lines = ticks ?? 4
  const step = niceStep(max / lines)
  const top = step * lines
  const tallest = points.reduce((best, point) => (point.value > best.value ? point : best))

  return (
    <div dir="ltr" className="flex gap-3">
      <div className="flex w-16 shrink-0 flex-col-reverse justify-between pb-8 text-end">
        {Array.from({ length: lines + 1 }, (_, index) => (
          <span
            key={index}
            className="numeric -mb-2 whitespace-nowrap text-[0.6875rem] text-fg-subtle"
          >
            {formatTick(step * index)}
          </span>
        ))}
      </div>

      <div className="min-w-0 flex-1">
        <div className="relative h-48">
          {/* Gridlines: hairline, solid, one step off the surface. They carry the
              values that are not directly labelled, so they earn their ink. */}
          {Array.from({ length: lines + 1 }, (_, index) => (
            <span
              key={index}
              className="absolute inset-x-0 border-t border-chart-grid"
              style={{ bottom: `${(index / lines) * 100}%` }}
            />
          ))}

          <div className="absolute inset-0 flex items-end">
            {points.map((point) => {
              const height = (point.value / top) * 100
              const isTallest = point.id === tallest.id

              return (
                <button
                  type="button"
                  key={point.id}
                  onMouseEnter={() => setHovered(point.id)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(point.id)}
                  onBlur={() => setHovered(null)}
                  aria-label={point.detail}
                  /* The hit target is the whole band, not the column: a thin
                     bar is a miserable thing to have to point at. */
                  className="group relative flex h-full flex-1 items-end justify-center px-[2px]"
                >
                  {isTallest && (
                    <span
                      className="numeric absolute text-[0.6875rem] font-semibold text-fg-muted"
                      style={{ bottom: `calc(${height}% + 4px)` }}
                    >
                      {formatTick(point.value)}
                    </span>
                  )}

                  <span
                    className="w-full max-w-6 rounded-t-[4px] bg-chart-fill transition-colors duration-(--duration-fast) group-hover:bg-chart-fill-hover"
                    style={{ blockSize: `${height}%` }}
                  />

                  {hovered === point.id && (
                    <span className="pointer-events-none absolute bottom-full z-10 mb-1 whitespace-nowrap rounded-sm border border-border bg-surface px-2 py-1 text-xs text-fg shadow-md">
                      {point.detail}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex">
          {points.map((point, index) => (
            <span
              key={point.id}
              className="flex flex-1 flex-col items-center pt-2 text-[0.6875rem] text-fg-subtle"
            >
              <span className="w-full truncate text-center">{point.label}</span>
              {point.sublabel !== points[index - 1]?.sublabel && (
                <span className="numeric w-full truncate text-center">{point.sublabel}</span>
              )}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

/** 1, 2, 5 × a power of ten — the numbers people put on an axis. */
function niceStep(rough: number): number {
  if (rough <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const normalised = rough / magnitude
  const snapped = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10
  return snapped * magnitude
}
