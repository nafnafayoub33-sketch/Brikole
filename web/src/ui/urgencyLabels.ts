import type { Urgency } from '@/data/requests'

/**
 * How soon somebody needs the work, as an i18n key.
 *
 * One copy. There were five, and the sixth got `request.urgencyThisWeek`
 * wrong — a key that does not exist renders as itself, and a screen showing
 * `request.urgencyThisWeek` to an admin is the whole cost of the duplication
 * in one line.
 */
export const URGENCY_KEYS: Record<Urgency, string> = {
  today: 'request.urgencyToday',
  this_week: 'request.urgencyWeek',
  flexible: 'request.urgencyFlexible',
}
