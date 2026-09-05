/**
 * A6 — the two lists everything else points at.
 *
 * Every write returns the whole catalogue rather than the row it changed, so
 * the cache is replaced rather than patched: a screen that splices one row
 * into a list it already had drifts out of step with the database the first
 * time two admins are editing at once.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { AUDIT_KEY } from '@/data/admin'
import { CITIES_KEY, TRADES_KEY } from '@/data/catalog'
import { api } from '@/data/client'

export const ADMIN_CATALOG_KEY = ['admin', 'catalog'] as const

export interface Usage {
  providers: number
  requests: number
  jobs: number
}

export interface AdminTrade {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
  icon: string
  /** Null means "use the platform default from A7", never "free". */
  lead_fee_centimes: number | null
  sort_order: number
  is_active: boolean
  usage: Usage
}

export interface AdminCity {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
  latitude: number
  longitude: number
  is_active: boolean
  usage: Usage
}

export interface Catalog {
  trades: AdminTrade[]
  cities: AdminCity[]
}

export interface TradeFields {
  name_ar: string
  name_fr: string
  name_en: string
  icon: string
  lead_fee_centimes: number | null
  sort_order: number
}

export interface CityFields {
  name_ar: string
  name_fr: string
  name_en: string
  latitude: number
  longitude: number
}

export function useCatalog() {
  return useQuery({
    queryKey: ADMIN_CATALOG_KEY,
    queryFn: () => api<Catalog>('/admin/catalog'),
    staleTime: 15_000,
  })
}

/**
 * Every write here changes what the whole product offers, so all of them
 * refresh the public lists too — a trade turned off must leave C1's picker
 * without a reload.
 */
function useCatalogMutation<TVariables>(send: (variables: TVariables) => Promise<Catalog>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: send,
    onSuccess: (catalog) => {
      queryClient.setQueryData(ADMIN_CATALOG_KEY, catalog)
      void queryClient.invalidateQueries({ queryKey: TRADES_KEY })
      void queryClient.invalidateQueries({ queryKey: CITIES_KEY })
      void queryClient.invalidateQueries({ queryKey: AUDIT_KEY })
    },
  })
}

export function useCreateTrade() {
  return useCatalogMutation((body: TradeFields & { slug: string }) =>
    api<Catalog>('/admin/catalog/trades', { method: 'POST', body }),
  )
}

export function useUpdateTrade() {
  return useCatalogMutation(({ id, ...body }: TradeFields & { id: number }) =>
    api<Catalog>(`/admin/catalog/trades/${id}`, { method: 'PATCH', body }),
  )
}

export function useSetTradeActive() {
  return useCatalogMutation(({ id, isActive }: { id: number; isActive: boolean }) =>
    api<Catalog>(`/admin/catalog/trades/${id}/active`, {
      method: 'PATCH',
      body: { is_active: isActive },
    }),
  )
}

export function useCreateCity() {
  return useCatalogMutation((body: CityFields & { slug: string }) =>
    api<Catalog>('/admin/catalog/cities', { method: 'POST', body }),
  )
}

export function useUpdateCity() {
  return useCatalogMutation(({ id, ...body }: CityFields & { id: number }) =>
    api<Catalog>(`/admin/catalog/cities/${id}`, { method: 'PATCH', body }),
  )
}

export function useSetCityActive() {
  return useCatalogMutation(({ id, isActive }: { id: number; isActive: boolean }) =>
    api<Catalog>(`/admin/catalog/cities/${id}/active`, {
      method: 'PATCH',
      body: { is_active: isActive },
    }),
  )
}
