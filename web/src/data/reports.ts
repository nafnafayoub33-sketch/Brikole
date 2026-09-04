/** Flagging a profile or a review, and D3 — clearing the queue of them. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { Page } from '@/data/types'

export type ReportTarget = 'provider_profile' | 'review'
/** A reason a person can pick when filing. */
export type FilableReason = 'spam' | 'offensive' | 'fake' | 'wrong_info' | 'other'

/** Every reason a report can arrive with. `contact_sharing` is filed by the
 *  platform and by nobody else, so it is readable but never offered — which
 *  is why the two types are not one. */
export type ReportReason = FilableReason | 'contact_sharing'
export type ReportOutcome = 'dismissed' | 'content_hidden' | 'warned' | 'suspended'

export const REPORT_REASONS: FilableReason[] = [
  'spam',
  'offensive',
  'fake',
  'wrong_info',
  'other',
]

/** The ceiling a moderator works under. Closing an account is an admin's. */
export const REPORT_OUTCOMES: ReportOutcome[] = [
  'dismissed',
  'content_hidden',
  'warned',
  'suspended',
]

export interface ReportedContent {
  kind: ReportTarget
  title: string
  body: string
  rating: number | null
  is_hidden: boolean
  provider_id: number | null
  owner_id: number | null
  owner_name: string | null
}

export interface Report {
  id: number
  target_type: ReportTarget
  target_id: number
  reason: ReportReason
  description: string | null
  status: string
  created_at: string
  /** Null when the platform filed it rather than a person. */
  reporter_id: number | null
  reporter_name: string | null
  handled_by_name: string | null
  handled_at: string | null
  outcome: ReportOutcome | null
  content: ReportedContent | null
  /** Other open reports on the same thing: three complaints is a different
   *  decision from one. */
  also_reported: number
}

export const REPORTS_KEY = ['mod', 'reports'] as const

export function useFileReport() {
  return useMutation({
    mutationFn: (body: {
      target_type: ReportTarget
      target_id: number
      reason: ReportReason
      description: string | null
    }) => api<Report>('/reports', { method: 'POST', body }),
  })
}

export function useReportQueue(tab: 'open' | 'handled') {
  return useQuery({
    queryKey: [...REPORTS_KEY, tab],
    queryFn: () => api<Page<Report>>(`/mod/reports?tab=${tab}&per_page=50`),
    staleTime: 10_000,
  })
}

export function useHandleReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      reportId,
      outcome,
      note,
    }: {
      reportId: number
      outcome: ReportOutcome
      note: string
    }) =>
      api<Report>(`/mod/reports/${reportId}/handle`, {
        method: 'POST',
        body: { outcome, note },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REPORTS_KEY }),
  })
}
