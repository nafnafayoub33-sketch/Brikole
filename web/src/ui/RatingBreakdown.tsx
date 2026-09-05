import { Stars } from '@/ui/Stars'
import { cn } from '@/ui/cn'

/**
 * The average, and how the scores fall behind it.
 *
 * P3 shows it to a client deciding, M10 shows the same thing to the tradesman
 * it is about — the same picture, so neither of them is reading a different
 * version of his reputation. Extracted here the moment there were two.
 *
 * All five rows are drawn, zeros included: a chart missing its empty bars is a
 * chart with different categories.
 */
export function RatingBreakdown({
  breakdown,
  total,
  average,
  className,
}: {
  breakdown: Record<string, number>
  total: number
  average: number
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-10 gap-y-5 rounded-lg border border-border bg-surface-2 p-5',
        className,
      )}
    >
      <div className="text-center">
        <p className="numeric text-4xl font-bold text-fg">{average.toFixed(1)}</p>
        <Stars value={average} className="mt-1" />
      </div>

      <ul className="min-w-56 flex-1 space-y-1.5">
        {[5, 4, 3, 2, 1].map((score) => {
          const count = breakdown[String(score)] ?? 0
          const share = total === 0 ? 0 : Math.round((count / total) * 100)
          return (
            <li key={score} className="flex items-center gap-3 text-xs">
              <span className="numeric w-3 text-fg-muted">{score}</span>
              <span className="h-2 flex-1 overflow-hidden rounded-pill bg-surface-inset">
                <span
                  className="block h-full rounded-pill bg-star"
                  style={{ width: `${share}%` }}
                />
              </span>
              <span className="numeric w-8 text-end text-fg-subtle">{count}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
