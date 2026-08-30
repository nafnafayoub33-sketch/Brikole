/** A client's own job requests. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { Page, ProviderCity, Trade } from '@/data/types'

export type Urgency = 'today' | 'this_week' | 'flexible'
export type RequestStatus = 'open' | 'assigned' | 'done' | 'cancelled' | 'expired'

export interface RequestPhoto {
  id: number
  url: string
}

export interface ServiceRequest {
  id: number
  title: string
  description: string
  address: string
  latitude: number | null
  longitude: number | null
  trade: Trade
  city: ProviderCity
  urgency: Urgency
  status: RequestStatus
  budget_min_centimes: number | null
  budget_max_centimes: number | null
  /** How many tradesmen have answered. The loudest number on C2. */
  offers_count: number
  photos: RequestPhoto[]
  created_at: string
  expires_at: string | null
  cancelled_at: string | null
  cancel_reason: string | null
}

export interface NewRequestBody {
  trade_id: number
  city_id: number
  title: string
  description: string
  address: string
  latitude: number | null
  longitude: number | null
  urgency: Urgency
  budget_min_centimes: number | null
  budget_max_centimes: number | null
  photo_paths: string[]
}

export const REQUESTS_KEY = ['client', 'requests'] as const

export function useMyRequests() {
  return useQuery({
    queryKey: REQUESTS_KEY,
    queryFn: () => api<Page<ServiceRequest>>('/client/requests?per_page=50'),
    staleTime: 15_000,
  })
}

export function useMyRequest(requestId: number | null) {
  return useQuery({
    queryKey: [...REQUESTS_KEY, requestId],
    queryFn: () => api<ServiceRequest>(`/client/requests/${requestId}`),
    enabled: requestId !== null,
    staleTime: 15_000,
  })
}

export function useCreateRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: NewRequestBody) =>
      api<ServiceRequest>('/client/requests', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
  })
}

export function useCancelRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ requestId, reason }: { requestId: number; reason?: string }) =>
      api<ServiceRequest>(`/client/requests/${requestId}/cancel`, {
        method: 'POST',
        body: { reason: reason ?? null },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
  })
}

export type OfferStatus = 'pending' | 'accepted' | 'rejected' | 'withdrawn' | 'expired'

export interface OfferProvider {
  id: number
  full_name: string
  avatar_url: string | null
  headline: string | null
  city: ProviderCity
  rating_avg: number
  rating_count: number
  jobs_done: number
  years_experience: number
}

export interface Offer {
  id: number
  price_centimes: number
  message: string
  available_from: string | null
  status: OfferStatus
  created_at: string
  provider: OfferProvider
}

export function useRequestOffers(requestId: number | null) {
  return useQuery({
    queryKey: [...REQUESTS_KEY, requestId, 'offers'],
    queryFn: () => api<Offer[]>(`/client/requests/${requestId}/offers`),
    enabled: requestId !== null,
    staleTime: 15_000,
  })
}
