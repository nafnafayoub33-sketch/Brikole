/** The balance, the ledger behind it, and the transfers that fill it. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { CREDIT_KEY, FEED_KEY } from '@/data/offers'
import type { Page } from '@/data/types'

export type TopupStatus = 'pending' | 'approved' | 'rejected'
export type TransactionType =
  | 'lead_fee'
  | 'topup'
  | 'refund'
  | 'adjustment'
  | 'free_lead'
  | 'boost'

export interface BankDetails {
  bank_name: string
  account_holder: string
  rib: string
  instructions: string
}

export interface LedgerEntry {
  id: number
  type: TransactionType
  /** Signed: negative took money out. */
  amount_centimes: number
  balance_after_centimes: number
  reason: string
  job_id: number | null
  created_at: string
}

export interface Topup {
  id: number
  amount_centimes: number
  reference: string
  status: TopupStatus
  created_at: string
  reviewed_at: string | null
  rejection_reason: string | null
  /** Private bucket — a path, never a URL. */
  receipt_path: string | null
}

export interface Boost {
  /** Answered by the API, not derived here from `expires_at`: the clock that
   *  decides it is the one the search ordering uses, and a phone with the
   *  wrong time must not disagree with the results. */
  active: boolean
  expires_at: string | null
  price_centimes: number
  days: number
  /** Whether the balance covers it. A button he can press and be refused by is
   *  worse than one that is not offered. */
  affordable: boolean
}

export interface CreditPage {
  balance_centimes: number
  free_leads_left: number
  default_lead_fee_centimes: number
  can_take_work: boolean
  boost: Boost
  bank: BankDetails
  preset_amounts: number[]
  topups: Topup[]
  ledger: LedgerEntry[]
}

export interface PendingTopup extends Topup {
  provider: {
    id: number
    full_name: string
    phone: string
    balance_centimes: number
  }
}

export const CREDIT_PAGE_KEY = ['pro', 'credit', 'page'] as const
export const TOPUP_QUEUE_KEY = ['admin', 'topups'] as const

export function useCreditPage() {
  return useQuery({
    queryKey: CREDIT_PAGE_KEY,
    queryFn: () => api<CreditPage>('/pro/credit/page'),
    staleTime: 15_000,
  })
}

export function useSubmitTopup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { amount_centimes: number; reference: string; receipt_path: string | null }) =>
      api<Topup>('/pro/topups', { method: 'POST', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CREDIT_PAGE_KEY }),
  })
}

/** Buying placement moves his balance and reorders every listing he is in. */
export function useBuyBoost() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api<Boost>('/pro/boost', { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CREDIT_PAGE_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_KEY })
    },
  })
}

export function useTopupQueue() {
  return useQuery({
    queryKey: TOPUP_QUEUE_KEY,
    queryFn: () => api<Page<PendingTopup>>('/admin/topups?per_page=50'),
    staleTime: 10_000,
  })
}

/** Approving moves money, so it refreshes everything that shows a balance. */
function useReviewMutation<TVariables>(request: (variables: TVariables) => Promise<Topup>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: TOPUP_QUEUE_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_PAGE_KEY })
      void queryClient.invalidateQueries({ queryKey: CREDIT_KEY })
      // His feed opens again the moment the balance moves.
      void queryClient.invalidateQueries({ queryKey: FEED_KEY })
    },
  })
}

export function useApproveTopup() {
  return useReviewMutation((topupId: number) =>
    api<Topup>(`/admin/topups/${topupId}/approve`, { method: 'POST' }),
  )
}

export function useRejectTopup() {
  return useReviewMutation(({ topupId, reason }: { topupId: number; reason: string }) =>
    api<Topup>(`/admin/topups/${topupId}/reject`, { method: 'POST', body: { reason } }),
  )
}
