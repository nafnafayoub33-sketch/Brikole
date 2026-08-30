/** Disputes, from either side of one and from the moderator's chair. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { JOBS_KEY } from '@/data/jobs'
import type { Page } from '@/data/types'

export type DisputeReason =
  | 'no_show'
  | 'work_not_done'
  | 'damage'
  | 'price_disagreement'
  | 'behaviour'
  | 'other'

export type DisputeStatus = 'open' | 'claimed' | 'resolved'
export type DisputeVerdict = 'client_at_fault' | 'provider_at_fault' | 'no_fault'

export const DISPUTE_REASONS: DisputeReason[] = [
  'no_show',
  'work_not_done',
  'damage',
  'price_disagreement',
  'behaviour',
  'other',
]

export interface DisputeParty {
  id: number
  full_name: string
  role: string
  provider_id: number | null
  rating_avg: number | null
  rating_count: number | null
  jobs_done: number | null
  disputes_lost: number
}

export interface DisputeMessage {
  id: number
  author_id: number
  author_name: string
  body: string
  attachment_url: string | null
  is_internal: boolean
  created_at: string
}

export interface DisputeJob {
  id: number
  title: string
  status: string
  agreed_price_centimes: number
  finished_at: string | null
  /** The only money figure a moderator is given, because he can refund it. */
  lead_fee_centimes: number | null
}

export interface Dispute {
  id: number
  reason: DisputeReason
  description: string
  status: DisputeStatus
  created_at: string
  job: DisputeJob
  opened_by: DisputeParty
  against: DisputeParty
  claimed_by_id: number | null
  claimed_by_name: string | null
  claimed_at: string | null
  verdict: DisputeVerdict | null
  resolution_note: string | null
  lead_fee_refunded: boolean
  resolved_at: string | null
  evidence: string[]
  messages: DisputeMessage[]
  is_stale: boolean
}

export interface DisputeRow {
  id: number
  reason: DisputeReason
  status: DisputeStatus
  created_at: string
  job_title: string
  opened_by_name: string
  against_name: string
  claimed_by_id: number | null
  is_stale: boolean
}

export type QueueTab = 'open' | 'mine' | 'resolved'

export const DISPUTES_KEY = ['disputes'] as const
export const QUEUE_KEY = ['mod', 'disputes'] as const

export function useMyDisputes() {
  return useQuery({
    queryKey: DISPUTES_KEY,
    queryFn: () => api<Page<DisputeRow>>('/disputes?per_page=50'),
    staleTime: 15_000,
  })
}

export function useDispute(disputeId: number | null) {
  return useQuery({
    queryKey: [...DISPUTES_KEY, disputeId],
    queryFn: () => api<Dispute>(`/disputes/${disputeId}`),
    enabled: disputeId !== null,
    staleTime: 10_000,
  })
}

export function useDisputeQueue(tab: QueueTab) {
  return useQuery({
    queryKey: [...QUEUE_KEY, tab],
    queryFn: () => api<Page<DisputeRow>>(`/mod/disputes?tab=${tab}&per_page=50`),
    staleTime: 10_000,
  })
}

/** Everything a dispute action touches: the case, both queues, and the job. */
function useDisputeMutation<TVariables>(request: (variables: TVariables) => Promise<Dispute>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (dispute) => {
      queryClient.setQueryData([...DISPUTES_KEY, dispute.id], dispute)
      void queryClient.invalidateQueries({ queryKey: DISPUTES_KEY })
      void queryClient.invalidateQueries({ queryKey: QUEUE_KEY })
      void queryClient.invalidateQueries({ queryKey: JOBS_KEY })
    },
  })
}

export function useOpenDispute() {
  return useDisputeMutation(
    ({
      jobId,
      ...body
    }: {
      jobId: number
      reason: DisputeReason
      description: string
      evidence_paths: string[]
    }) => api<Dispute>(`/jobs/${jobId}/dispute`, { method: 'POST', body }),
  )
}

export function useClaimDispute() {
  return useDisputeMutation((disputeId: number) =>
    api<Dispute>(`/mod/disputes/${disputeId}/claim`, { method: 'POST' }),
  )
}

export function useDisputeMessage() {
  return useDisputeMutation(
    ({ disputeId, body, isInternal }: { disputeId: number; body: string; isInternal?: boolean }) =>
      api<Dispute>(`/disputes/${disputeId}/messages`, {
        method: 'POST',
        body: { body, is_internal: isInternal ?? false },
      }),
  )
}

export function useResolveDispute() {
  return useDisputeMutation(
    ({
      disputeId,
      ...body
    }: {
      disputeId: number
      verdict: DisputeVerdict
      note: string
      refund_lead_fee: boolean
      suspend_at_fault: boolean
    }) => api<Dispute>(`/mod/disputes/${disputeId}/resolve`, { method: 'POST', body }),
  )
}
