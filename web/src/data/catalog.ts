/** Trades and cities. Public, cached hard — an admin changes them rarely. */

import { useQuery } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { City, Trade } from '@/data/types'

/** Named so A6 can invalidate them when an admin changes what the product
 *  offers. `TRADES_KEY` is a prefix: it matches every per-city variant. */
export const TRADES_KEY = ['trades'] as const
export const CITIES_KEY = ['cities'] as const

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
    queryKey: [...TRADES_KEY, cityId],
    queryFn: () => api<Trade[]>(`/trades${query}`, { authenticated: false }),
    staleTime: 10 * 60_000,
  })
}

export function useCities() {
  return useQuery({
    queryKey: CITIES_KEY,
    queryFn: () => api<City[]>('/cities', { authenticated: false }),
    staleTime: 60 * 60_000,
  })
}
