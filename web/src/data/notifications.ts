/**
 * C6 — the client's inbox.
 *
 * The API never ships a sentence: a row is a `kind` and a `payload`, and this
 * side turns them into a translated line and a link. That is what lets one row
 * read correctly in three languages, and what stops last week's notifications
 * being stuck in the language he has since left.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import type { Page } from '@/data/types'

export const NOTIFICATIONS_KEY = ['notifications'] as const

export const NOTIFICATIONS_PER_PAGE = 20

export type NotificationKind =
  | 'offer_received'
  | 'offer_accepted'
  | 'offer_rejected'
  | 'job_started'
  | 'job_done'
  | 'review_received'
  | 'provider_approved'
  | 'provider_rejected'
  | 'topup_approved'
  | 'topup_rejected'
  | 'dispute_update'
  | 'credit_low'

export interface Notification {
  id: number
  kind: NotificationKind
  /** Ids and numbers the screen interpolates, and the id it links to. */
  payload: Record<string, unknown>
  created_at: string
  read_at: string | null
}

export function useNotifications(page: number) {
  return useQuery({
    queryKey: [...NOTIFICATIONS_KEY, 'page', page],
    queryFn: () =>
      api<Page<Notification>>(
        `/notifications?page=${page}&per_page=${NOTIFICATIONS_PER_PAGE}`,
      ),
    staleTime: 15_000,
  })
}

/**
 * The number on the nav item.
 *
 * `enabled` because only the client has an inbox screen today: the endpoints
 * answer for anyone, but a shell with nowhere to send him should not be asking.
 */
export function useUnreadNotifications(enabled: boolean) {
  return useQuery({
    queryKey: [...NOTIFICATIONS_KEY, 'unread'],
    queryFn: () => api<{ count: number }>('/notifications/unread'),
    enabled,
    staleTime: 30_000,
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: number }) =>
      api<Notification>(`/notifications/${id}/read`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY }),
  })
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/notifications/read', { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY }),
  })
}
