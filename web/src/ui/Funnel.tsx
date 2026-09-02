export interface FunnelStep {
  id: string
  label: string
  value: number
  /** Already formatted — the page owns how a number reads. */
  display: string
  /** What falls out between the step before and this one, in words. */
  lost?: string
}

const STEP_FILL = [
  'bg-chart-step-1',
  'bg-chart-step-2',
  'bg-chart-step-3',
  'bg-chart-step-4',
] as const

/** Whole percents, except where rounding would hide a real loss: 1073 of
 *  1076 is 99.7%, and printing it as 100% next to a step that dropped three
 *  requests is the chart telling a comfortable lie. */
function readPercent(value: number, first: number): string {
  if (first <= 0) return '0'
  const percent = (value / first) * 100
  const rounded = Math.round(percent)
  if (value < first && rounded === 100) return percent.toFixed(1)
  return String(rounded)
}

/**
 * Published → answered → hired → confirmed.
 *
 * The one thing on the dashboard that says whether the marketplace works: a
 * request nobody answers is the failure the platform exists to prevent.
 *
 * The steps have an order, so they take an ordinal ramp — one hue, getting
 * darker along the sequence — rather than four identities. Every step is
 * measured against the first, so the bars are comparable to each other and
 * not just to their own neighbour.
 */
export function Funnel({
  steps,
  share,
}: {
  steps: FunnelStep[]
  /** Renders "84%" — the arithmetic is ours, the wording is the page's. */
  share: (percent: string) => string
}) {
  const first = steps[0]?.value ?? 0

  return (
    <ol className="flex flex-col gap-4">
      {steps.map((step, index) => {
        const percent = first > 0 ? (step.value / first) * 100 : 0

        return (
          <li key={step.id}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm text-fg">{step.label}</span>
              <span className="flex items-baseline gap-2">
                <span className="numeric text-sm font-semibold text-fg">{step.display}</span>
                <span className="numeric text-xs text-fg-subtle">
                  {share(readPercent(step.value, first))}
                </span>
              </span>
            </div>

            <div className="mt-1.5 h-3 rounded-pill bg-chart-track">
              <div
                className={`h-3 rounded-pill ${STEP_FILL[Math.min(index, STEP_FILL.length - 1)]}`}
                style={{ inlineSize: `${Math.max(percent, step.value > 0 ? 2 : 0)}%` }}
              />
            </div>

            {step.lost && <p className="mt-1 text-xs text-fg-subtle">{step.lost}</p>}
          </li>
        )
      })}
    </ol>
  )
}
