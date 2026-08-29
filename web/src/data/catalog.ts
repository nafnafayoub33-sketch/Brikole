/** Trades and cities. Public, cached hard — an admin changes them rarely. */

import { useQuery } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { City, Trade } from '@/data/types'

/**
 * The trade grid.
 *
 * `cityId` changes the counts, not the list: a trade nobody works in that city
 * still appears, with zero, because hiding it would leave the visitor
 * wondering whether the trade exists at all.
 */
export function useTrades(cityId: number | null = null) {
  const query = cityId === null ? '' : `?city_id=${cityId}`
  return useQuery({
    queryKey: ['trades', cityId],
    queryFn: () => api<Trade[]>(`/trades${query}`, { authenticated: false }),
    staleTime: 10 * 60_000,
  })
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: () => api<City[]>('/cities', { authenticated: false }),
    staleTime: 60 * 60_000,
  })
}
