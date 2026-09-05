/**
 * C7, M11 and D4 — a person's own account.
 *
 * One module for three screens, because the row is the same whatever the role.
 * Every mutation here lands in `SESSION_KEY`, so the header, the role gate and
 * the language all follow without anything else being told.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { SESSION_KEY } from '@/data/auth'
import { sessionStore } from '@/data/session'
import type { Me } from '@/data/types'

export const COMMITMENTS_KEY = ['account', 'commitments'] as const

export interface AccountEdit {
  full_name: string
  city_id: number | null
  language: string
  avatar_path?: string
}

export interface Commitments {
  live_jobs: number
  live_disputes: number
  /** Answered by the API rather than recomputed here, so the screen and
   *  `core.account.assert_can_delete` cannot drift apart. */
  can_delete: boolean
}

export function useEditAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: AccountEdit) => api<Me>('/account', { method: 'PATCH', body }),
    onSuccess: (me) => queryClient.setQueryData(SESSION_KEY, me),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api<void>('/auth/change-password', { method: 'POST', body }),
  })
}

/** What is still hanging off the account. Read before the delete button is
 *  offered, so somebody with a job in progress reads why. */
export function useCommitments() {
  return useQuery({
    queryKey: COMMITMENTS_KEY,
    queryFn: () => api<Commitments>('/account/commitments'),
    staleTime: 30_000,
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/account', { method: 'DELETE' }),
    onSuccess: () => {
      // He is gone. Same teardown as signing out — anything still cached
      // belongs to an account the API will now refuse.
      sessionStore.clear()
      queryClient.setQueryData(SESSION_KEY, null)
      void queryClient.invalidateQueries()
    },
  })
}
