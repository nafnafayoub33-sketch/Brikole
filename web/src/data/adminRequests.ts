/**
 * A4 — the support browser.
 *
 * Its own module rather than another thousand lines in `admin.ts`: nothing
 * here is shared with the accounts screen except the audit key it invalidates.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { AUDIT_KEY, STATS_KEY } from '@/data/admin'
import { api } from '@/data/client'
import type { JobStatus } from '@/data/jobs'
import type { RequestStatus, Urgency } from '@/data/requests'
import type { City, Page, Trade } from '@/data/types'

export const REQUESTS_PER_PAGE = 25

export const ADMIN_REQUESTS_KEY = ['admin', 'requests'] as const

export interface RequestPerson {
  id: number
  full_name: string
  /** Here because A4 exists while somebody is *on* the phone. An admin who has
   *  to leave the screen to find the number reads it out wrong. */
  phone: string
}

export interface AdminRequestRow {
  id: number
  title: string
  status: RequestStatus
  urgency: Urgency
  offers_count: number
  created_at: string
  client: RequestPerson
  trade: Trade
  city: City
}

export interface AdminRequestOffer {
  id: number
  price_centimes: number
  message: string | null
  status: 'pending' | 'accepted' | 'rejected' | 'withdrawn' | 'expired'
  created_at: string
  /** Frozen when it was accepted; null on an offer nobody took. */
  lead_fee_centimes: number | null
  provider: RequestPerson
  provider_id: number
}

export interface AdminRequestJob {
  id: number
  status: JobStatus
  agreed_price_centimes: number
  started_at: string | null
  finished_at: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancelled_by: string | null
  cancel_reason: string | null
  provider: RequestPerson | null
}

export interface AdminRequestDispute {
  id: number
  status: 'open' | 'claimed' | 'resolved'
  reason: string
  opened_by_id: number
}

export interface AdminRequest {
  id: number
  title: string
  description: string
  status: RequestStatus
  urgency: Urgency
  address: string
  budget_min_centimes: number | null
  budget_max_centimes: number | null
  photos: number
  offers_count: number

  created_at: string
  expires_at: string | null
  cancelled_at: string | null
  cancel_reason: string | null

  client: RequestPerson
  trade: Trade
  city: City

  offers: AdminRequestOffer[]
  job: AdminRequestJob | null
  dispute: AdminRequestDispute | null

  /** Answered by the API rather than derived here from `status`, so the button
   *  and the endpoint agree about what "open" means. */
  can_cancel: boolean
}

export interface RequestFilters {
  q: string
  status: RequestStatus | ''
  cityId: number | ''
  tradeId: number | ''
}

export function useAdminRequests(filters: RequestFilters, page: number) {
  const params = new URLSearchParams({
    per_page: String(REQUESTS_PER_PAGE),
    page: String(page),
  })
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.status) params.set('status', filters.status)
  if (filters.cityId) params.set('city_id', String(filters.cityId))
  if (filters.tradeId) params.set('trade_id', String(filters.tradeId))

  return useQuery({
    queryKey: [
      ...ADMIN_REQUESTS_KEY,
      filters.q.trim(),
      filters.status,
      filters.cityId,
      filters.tradeId,
      page,
    ],
    queryFn: () => api<Page<AdminRequestRow>>(`/admin/requests?${params}`),
    staleTime: 15_000,
    // Stepping through pages must not blink the list back to a skeleton.
    placeholderData: (previous) => previous,
  })
}

export function useAdminRequest(requestId: number | null) {
  return useQuery({
    queryKey: [...ADMIN_REQUESTS_KEY, 'one', requestId],
    queryFn: () => api<AdminRequest>(`/admin/requests/${requestId}`),
    enabled: requestId !== null,
  })
}

/** The one thing this screen can change, so the one thing that writes an
 *  audit row — which A8 reads. */
export function useCancelRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      api<AdminRequest>(`/admin/requests/${id}/cancel`, {
        method: 'POST',
        body: { reason },
      }),
    onSuccess: (request) => {
      queryClient.setQueryData([...ADMIN_REQUESTS_KEY, 'one', request.id], request)
      void queryClient.invalidateQueries({ queryKey: ADMIN_REQUESTS_KEY })
      void queryClient.invalidateQueries({ queryKey: AUDIT_KEY })
      void queryClient.invalidateQueries({ queryKey: STATS_KEY })
    },
  })
}
