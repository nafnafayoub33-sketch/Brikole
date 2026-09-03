/** The tradesman's side: his balance, his feed, and the offers he has sent. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { JOBS_KEY } from '@/data/jobs'
import type { OfferStatus, Urgency } from '@/data/requests'
import type { Page, ProviderCity, Trade } from '@/data/types'

export interface CreditSummary {
  balance_centimes: number
  free_leads_left: number
  default_lead_fee_centimes: number
  /** False when the feed is closed to him until he tops up. */
  can_take_work: boolean
}

export interface FeedRequest {
  id: number
  title: string
  excerpt: string
  trade: Trade
  city: ProviderCity
  urgency: Urgency
  budget_min_centimes: number | null
  budget_max_centimes: number | null
  offers_count: number
  photos_count: number
  created_at: string
  expires_at: string | null
  my_offer_id: number | null
  my_offer_price_centimes: number | null
}

export interface MyOffer {
  id: number
  request_id: number
  request_title: string
  trade: Trade
  city: ProviderCity
  price_centimes: number
  message: string
  available_from: string | null
  status: OfferStatus
  created_at: string
  responded_at: string | null
  job_id: number | null
  /** Set once the client has opened the thread on this offer. Null means
   *  nobody has replied yet, and M6 says so rather than linking to nothing. */
  conversation_id: number | null
}

export interface FeedRequestDetail extends FeedRequest {
  description: string
  photos: { id: number; url: string }[]
  /** What he pays **if** the client accepts. Never taken at this moment. */
  lead_fee_centimes: number
  my_offer: MyOffer | null
}

export interface NewOfferBody {
  price_centimes: number
  message: string | null
  available_from: string | null
}

export const CREDIT_KEY = ['pro', 'credit'] as const
export const FEED_KEY = ['pro', 'feed'] as const
export const MY_OFFERS_KEY = ['pro', 'offers'] as const

export function useCredit() {
  return useQuery({
    queryKey: CREDIT_KEY,
    queryFn: () => api<CreditSummary>('/pro/credit'),
    staleTime: 15_000,
  })
}

export function useFeed(filters: { tradeId?: number | null; urgency?: Urgency | null }) {
  const params = new URLSearchParams({ per_page: '50' })
  if (filters.tradeId) params.set('trade_id', String(filters.tradeId))
  if (filters.urgency) params.set('urgency', filters.urgency)

  return useQuery({
    queryKey: [...FEED_KEY, filters.tradeId ?? null, filters.urgency ?? null],
    queryFn: () => api<Page<FeedRequest>>(`/pro/requests?${params}`),
    staleTime: 15_000,
    // An empty balance answers 402, and that is a real answer the screen
    // renders — not a failure worth retrying three times first.
    retry: false,
  })
}

export function useFeedRequest(requestId: number | null) {
  return useQuery({
    queryKey: [...FEED_KEY, 'request', requestId],
    queryFn: () => api<FeedRequestDetail>(`/pro/requests/${requestId}`),
    enabled: requestId !== null,
    staleTime: 15_000,
    retry: false,
  })
}

export function useMyOffers() {
  return useQuery({
    queryKey: MY_OFFERS_KEY,
    queryFn: () => api<Page<MyOffer>>('/pro/offers?per_page=50'),
    staleTime: 15_000,
  })
}

/** Everything an offer touches: the feed row, his list, and the job it becomes. */
function useOfferMutation<TVariables>(request: (variables: TVariables) => Promise<MyOffer>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FEED_KEY })
      void queryClient.invalidateQueries({ queryKey: MY_OFFERS_KEY })
      void queryClient.invalidateQueries({ queryKey: JOBS_KEY })
    },
  })
}

export function useSendOffer() {
  return useOfferMutation(
    ({ requestId, ...body }: NewOfferBody & { requestId: number }) =>
      api<MyOffer>(`/pro/requests/${requestId}/offer`, { method: 'POST', body }),
  )
}

export function useWithdrawOffer() {
  return useOfferMutation((offerId: number) =>
    api<MyOffer>(`/pro/offers/${offerId}/withdraw`, { method: 'POST' }),
  )
}
