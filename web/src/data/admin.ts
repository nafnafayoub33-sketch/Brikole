/** A7 and A8 — the platform's dials, and the record of who turned them. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { CREDIT_KEY } from '@/data/offers'
import { CREDIT_PAGE_KEY } from '@/data/credit'
import type { Page } from '@/data/types'

export interface Setting {
  key: string
  value: unknown
  /** Null while nobody has changed it: the value is the shipped default. */
  updated_at: string | null
  updated_by_name: string | null
}

export interface BankValue {
  bank_name: string
  account_holder: string
  rib: string
  instructions: string
}

export interface AuditEntry {
  id: number
  action: string
  target_type: string
  target_id: number | null
  actor_id: number | null
  /** Null when the actor's account is gone. The row survives — that is the point. */
  actor_name: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  note: string | null
  ip: string | null
  created_at: string
}

export interface AuditFilters {
  actions: string[]
  target_types: string[]
}

export const SETTINGS_KEY = ['admin', 'settings'] as const
export const AUDIT_KEY = ['admin', 'audit'] as const

export function useSettings() {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: () => api<{ items: Setting[] }>('/admin/settings'),
    staleTime: 30_000,
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      api<{ items: Setting[] }>('/admin/settings', { method: 'PATCH', body: { values } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SETTINGS_KEY })
      // A7 is not a display: the fee and the bank panel are read elsewhere.
      void queryClient.invalidateQueries({ queryKey: AUDIT_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_PAGE_KEY })
    },
  })
}

export function useAudit(filters: { action?: string | null; targetType?: string | null }) {
  const params = new URLSearchParams({ per_page: '100' })
  if (filters.action) params.set('action', filters.action)
  if (filters.targetType) params.set('target_type', filters.targetType)

  return useQuery({
    queryKey: [...AUDIT_KEY, filters.action ?? null, filters.targetType ?? null],
    queryFn: () => api<Page<AuditEntry>>(`/admin/audit?${params}`),
    staleTime: 15_000,
  })
}

export function useAuditFilters() {
  return useQuery({
    queryKey: [...AUDIT_KEY, 'filters'],
    queryFn: () => api<AuditFilters>('/admin/audit/filters'),
    staleTime: 60_000,
  })
}
