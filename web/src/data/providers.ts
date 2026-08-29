/** The tradesmen a client browses. */

import { useQuery } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { Page, Provider, ProviderProfile, Review } from '@/data/types'

export type ProviderSort = 'rating' | 'jobs' | 'price' | 'newest'

interface ProviderQuery {
  query?: string | null
  tradeId?: number | null
  cityId?: number | null
  sort?: ProviderSort
  page?: number
  perPage?: number
  /** Hold the request until the caller knows what to ask for. */
  enabled?: boolean
}

export function useProviders({
  query = null,
  tradeId = null,
  cityId = null,
  sort = 'rating',
  page = 1,
  perPage = 12,
  enabled = true,
}: ProviderQuery = {}) {
  const params = new URLSearchParams({
    sort,
    page: String(page),
    per_page: String(perPage),
  })
  if (query) params.set('q', query)
  if (tradeId !== null) params.set('trade_id', String(tradeId))
  if (cityId !== null) params.set('city_id', String(cityId))

  return useQuery({
    queryKey: ['providers', { query, tradeId, cityId, sort, page, perPage }],
    queryFn: () => api<Page<Provider>>(`/providers?${params}`, { authenticated: false }),
    staleTime: 60_000,
    enabled,
  })
}


export function useProvider(providerId: number | null) {
  return useQuery({
    queryKey: ['provider', providerId],
    queryFn: () => api<ProviderProfile>(`/providers/${providerId}`, { authenticated: false }),
    enabled: providerId !== null,
    staleTime: 60_000,
  })
}

export function useProviderReviews(
  providerId: number | null,
  { page = 1, perPage = 10 }: { page?: number; perPage?: number } = {},
) {
  return useQuery({
    queryKey: ['provider-reviews', providerId, page, perPage],
    queryFn: () =>
      api<Page<Review>>(`/providers/${providerId}/reviews?page=${page}&per_page=${perPage}`, {
        authenticated: false,
      }),
    enabled: providerId !== null,
    staleTime: 60_000,
  })
}
