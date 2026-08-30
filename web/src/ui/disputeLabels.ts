/** Translation keys for the dispute vocabulary, kept out of the component file
 *  so Fast Refresh keeps working on the badges. */

import type { DisputeReason, DisputeStatus, DisputeVerdict } from '@/data/disputes'

export const REASON_KEYS: Record<DisputeReason, string> = {
  no_show: 'dispute.reasonNoShow',
  work_not_done: 'dispute.reasonWorkNotDone',
  damage: 'dispute.reasonDamage',
  price_disagreement: 'dispute.reasonPrice',
  behaviour: 'dispute.reasonBehaviour',
  other: 'dispute.reasonOther',
}

export const STATUS_TONES = {
  open: 'warning',
  claimed: 'brand',
  resolved: 'success',
} as const

export const STATUS_KEYS: Record<DisputeStatus, string> = {
  open: 'dispute.statusOpen',
  claimed: 'dispute.statusClaimed',
  resolved: 'dispute.statusResolved',
}

export const VERDICT_KEYS: Record<DisputeVerdict, string> = {
  client_at_fault: 'dispute.verdictClientAtFault',
  provider_at_fault: 'dispute.verdictProviderAtFault',
  no_fault: 'dispute.verdictNoFault',
}
