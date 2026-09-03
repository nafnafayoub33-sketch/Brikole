/** A job, read from whichever side of it you are on. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { REQUESTS_KEY } from '@/data/requests'
import type { Page, ProviderCity, Trade } from '@/data/types'

export type JobStatus = 'assigned' | 'in_progress' | 'done' | 'confirmed' | 'cancelled'
export type CancelledBy = 'client' | 'provider' | 'admin'

export interface JobParty {
  id: number
  full_name: string
  avatar_url: string | null
  /** On this type and no other: it appears only once an offer is accepted. */
  phone: string
  rating_avg: number | null
  rating_count: number | null
  jobs_done: number | null
}

export interface JobReview {
  id: number
  rating: number
  comment: string | null
  created_at: string
  reply: string | null
  replied_at: string | null
}

export interface Job {
  id: number
  request_id: number
  status: JobStatus
  title: string
  description: string
  trade: Trade
  city: ProviderCity
  address: string
  agreed_price_centimes: number
  /** Null on the client's copy — what the lead cost is the m3allem's business. */
  lead_fee_centimes: number | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancelled_by: CancelledBy | null
  cancel_reason: string | null
  client: JobParty
  provider: JobParty
  review: JobReview | null
}

export const JOBS_KEY = ['jobs'] as const

export function useMyJobs() {
  return useQuery({
    queryKey: JOBS_KEY,
    queryFn: () => api<Page<Job>>('/jobs?per_page=50'),
    staleTime: 15_000,
  })
}

export function useJob(jobId: number | null) {
  return useQuery({
    queryKey: [...JOBS_KEY, jobId],
    queryFn: () => api<Job>(`/jobs/${jobId}`),
    enabled: jobId !== null,
    staleTime: 15_000,
  })
}

/** Everything a job transition touches, in one place. */
function useJobMutation<TVariables>(
  request: (variables: TVariables) => Promise<Job>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: (job) => {
      queryClient.setQueryData([...JOBS_KEY, job.id], job)
      void queryClient.invalidateQueries({ queryKey: JOBS_KEY })
      // Accepting, cancelling and confirming all move the request too.
      void queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
    },
  })
}

// There is no `useAcceptOffer` any more, and no route behind one. A job is
// created when both sides have signed the same terms in the chat — see
// `useAgree` in `data/chat` — so the client no longer commits to a price
// before he has been able to ask a single question about it.

export function useStartJob() {
  return useJobMutation((jobId: number) => api<Job>(`/jobs/${jobId}/start`, { method: 'POST' }))
}

export function useFinishJob() {
  return useJobMutation((jobId: number) => api<Job>(`/jobs/${jobId}/finish`, { method: 'POST' }))
}

export function useConfirmJob() {
  return useJobMutation((jobId: number) => api<Job>(`/jobs/${jobId}/confirm`, { method: 'POST' }))
}

export function useCancelJob() {
  return useJobMutation(({ jobId, reason }: { jobId: number; reason?: string }) =>
    api<Job>(`/jobs/${jobId}/cancel`, { method: 'POST', body: { reason: reason ?? null } }),
  )
}

export function useReviewJob() {
  return useJobMutation(
    ({ jobId, rating, comment }: { jobId: number; rating: number; comment?: string }) =>
      api<Job>(`/jobs/${jobId}/review`, {
        method: 'POST',
        body: { rating, comment: comment?.trim() || null },
      }),
  )
}
