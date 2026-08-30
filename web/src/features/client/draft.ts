/**
 * The request being written, kept across a closed tab.
 *
 * Describing a job takes real effort — four steps, photos, an address — and
 * losing it to a misplaced tap is the difference between a request posted and
 * a visitor who does not come back. Only paths are stored, never the local
 * preview URLs: an object URL dies with the document, and a request photo is
 * public, so its path is enough to show it again.
 */

import type { Urgency } from '@/data/requests'

const KEY = 'brikole.requestDraft'
const VERSION = 1

export interface RequestDraft {
  version: number
  step: number
  tradeId: number | null
  title: string
  description: string
  photoPaths: string[]
  cityId: number | null
  address: string
  urgency: Urgency
  budgetMin: string
  budgetMax: string
}

export const EMPTY_DRAFT: RequestDraft = {
  version: VERSION,
  step: 1,
  tradeId: null,
  title: '',
  description: '',
  photoPaths: [],
  cityId: null,
  address: '',
  urgency: 'flexible',
  budgetMin: '',
  budgetMax: '',
}

export function readDraft(): RequestDraft {
  try {
    const stored = localStorage.getItem(KEY)
    if (!stored) return EMPTY_DRAFT

    const parsed = JSON.parse(stored) as Partial<RequestDraft>
    // A draft from an older shape is discarded rather than half-restored.
    if (parsed.version !== VERSION) return EMPTY_DRAFT
    return { ...EMPTY_DRAFT, ...parsed }
  } catch {
    return EMPTY_DRAFT
  }
}

export function writeDraft(draft: RequestDraft): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(draft))
  } catch {
    // Site data blocked. Losing the draft is bad; refusing to let him type
    // would be worse.
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Nothing to do about it, and nothing depends on it having worked.
  }
}
