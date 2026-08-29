/** The tradesmen a client browses. */

import { useQuery } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { Page, Provider } from '@/data/types'

export type ProviderSort = 'rating' | 'jobs' | 'price' | 'newest'

interface ProviderQuery {
  tradeId?: number | null
  cityId?: number | null
  sort?: ProviderSort
  page?: number
  perPage?: number
}

export function useProviders({
  tradeId = null,
  cityId = null,
  sort = 'rating',
  page = 1,
  perPage = 12,
}: ProviderQuery = {}) {
  const params = new URLSearchParams({
    sort,
    page: String(page),
    per_page: String(perPage),
  })
  if (tradeId !== null) params.set('trade_id', String(tradeId))
  if (cityId !== null) params.set('city_id', String(cityId))

  return useQuery({
    queryKey: ['providers', { tradeId, cityId, sort, page, perPage }],
    queryFn: () => api<Page<Provider>>(`/providers?${params}`, { authenticated: false }),
    staleTime: 60_000,
  })
}
