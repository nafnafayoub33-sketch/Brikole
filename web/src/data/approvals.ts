/** A2 — the applications waiting for an admin. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { MyProviderProfile } from '@/data/pro'
import type { Page } from '@/data/types'

export interface Application extends MyProviderProfile {
  phone: string
  submitted_at: string
}

export const APPROVALS_KEY = ['admin', 'approvals'] as const

export function usePendingApplications(page = 1, perPage = 20) {
  return useQuery({
    queryKey: [...APPROVALS_KEY, page, perPage],
    queryFn: () => api<Page<Application>>(`/admin/approvals?page=${page}&per_page=${perPage}`),
    // A queue two admins share goes stale the moment one of them acts.
    staleTime: 0,
  })
}

export function useApprove() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (providerId: number) =>
      api<Application>(`/admin/approvals/${providerId}/approve`, { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: APPROVALS_KEY }),
  })
}

export function useReject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ providerId, reason }: { providerId: number; reason: string }) =>
      api<Application>(`/admin/approvals/${providerId}/reject`, {
        method: 'POST',
        body: { reason },
      }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: APPROVALS_KEY }),
  })
}
