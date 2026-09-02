/** A7 and A8 — the platform's dials, and the record of who turned them. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/data/client'
import { CREDIT_KEY } from '@/data/offers'
import { CREDIT_PAGE_KEY } from '@/data/credit'
import type { DisputeStatus } from '@/data/disputes'
import type { City, Page, ProviderStatus, Role, UserStatus } from '@/data/types'

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

export interface PlatformMoney {
  taken_centimes: number
  /** Argued over between a client and a tradesman. The platform holds none of
   *  it — there is no escrow before phase 3. */
  in_dispute_centimes: number
  /** What the platform charged on those same jobs, and could be told to
   *  refund. This one is its own exposure; the line above is not. */
  disputed_lead_fees_centimes: number
  topups_waiting: number
  topups_waiting_centimes: number
  credit_held_centimes: number
  credit_owed_centimes: number
}

export interface StatsMonth {
  /** `2026-08`. */
  month: string
  leads: number
  value_centimes: number
  jobs: number
}

export interface StatsPlace {
  id: number
  slug: string
  name_ar: string
  name_fr: string
  name_en: string
  jobs: number
  open_requests: number
  providers: number
  value_centimes: number
}

export interface StatsFunnel {
  requests: number
  with_offer: number
  hired: number
  confirmed: number
}

export interface PlatformStats {
  new_users_this_week: number
  new_users_last_week: number
  providers_awaiting_approval: number
  open_requests: number
  jobs_done: number
  leads_sold: number
  /** What the platform actually took. The one figure it lives on. */
  leads_value_centimes: number
  disputes_open: number

  money: PlatformMoney
  /** Oldest first, gaps included: a quiet month is a fact, not a missing row. */
  months: StatsMonth[]
  cities: StatsPlace[]
  trades: StatsPlace[]
  funnel: StatsFunnel
}

export const STATS_KEY = ['admin', 'stats'] as const

export function useStats() {
  return useQuery({
    queryKey: STATS_KEY,
    queryFn: () => api<PlatformStats>('/admin/stats'),
    staleTime: 30_000,
  })
}

// -- A3: accounts -----------------------------------------------------------

export interface AdminUserRow {
  id: number
  phone: string
  full_name: string
  role: Role
  status: UserStatus
  avatar_url: string | null
  city: City | null
  created_at: string
  last_login_at: string | null
  suspended_until: string | null
  /** Set when this account also has a tradesman profile. */
  provider_status: ProviderStatus | null
}

export interface AdminUserProvider {
  id: number
  status: ProviderStatus
  headline: string | null
  rating_avg: number
  rating_count: number
  jobs_done: number
  balance_centimes: number
  free_leads_left: number
}

export interface AdminUserActivity {
  requests_posted: number
  jobs_hired: number
  spent_centimes: number
  reviews_written: number
  offers_sent: number
  jobs_worked: number
  disputes_opened: number
  disputes_against: number
  staff_actions: number
}

export interface AdminUserDispute {
  id: number
  job_id: number
  status: DisputeStatus
  reason: string
  created_at: string
  opened_by_them: boolean
}

export interface AdminUser extends AdminUserRow {
  language: string
  suspension_reason: string | null
  locked_until: string | null
  provider: AdminUserProvider | null
  activity: AdminUserActivity
  disputes: AdminUserDispute[]
}

export interface UserFilters {
  q: string
  role: Role | null
  status: UserStatus | null
}

/** Enough to scan without scrolling forever, and the pager reaches the rest. */
export const USERS_PER_PAGE = 25

export const USERS_KEY = ['admin', 'users'] as const

export function useUsers(filters: UserFilters, page: number) {
  const params = new URLSearchParams({
    per_page: String(USERS_PER_PAGE),
    page: String(page),
  })
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.role) params.set('role', filters.role)
  if (filters.status) params.set('status', filters.status)

  return useQuery({
    queryKey: [...USERS_KEY, filters.q.trim(), filters.role, filters.status, page],
    queryFn: () => api<Page<AdminUserRow>>(`/admin/users?${params}`),
    staleTime: 15_000,
    // Paging with the previous page still on screen: the list must not blink
    // back to a skeleton every time somebody steps through it.
    placeholderData: (previous) => previous,
  })
}

export function useUser(userId: number | null) {
  return useQuery({
    queryKey: [...USERS_KEY, 'one', userId],
    queryFn: () => api<AdminUser>(`/admin/users/${userId}`),
    enabled: userId !== null,
  })
}

/** Every action here changes somebody's account, so every one of them also
 *  lands in the audit log — which A8 reads. */
function useAccountAction<TVariables>(
  send: (variables: TVariables) => Promise<AdminUser>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: send,
    onSuccess: (user) => {
      queryClient.setQueryData([...USERS_KEY, 'one', user.id], user)
      void queryClient.invalidateQueries({ queryKey: USERS_KEY })
      void queryClient.invalidateQueries({ queryKey: AUDIT_KEY })
      void queryClient.invalidateQueries({ queryKey: STATS_KEY })
    },
  })
}

export function useSuspendUser() {
  return useAccountAction(
    ({ id, days, reason }: { id: number; days: number | null; reason: string }) =>
      api<AdminUser>(`/admin/users/${id}/suspend`, { method: 'POST', body: { days, reason } }),
  )
}

export function useReactivateUser() {
  return useAccountAction(({ id }: { id: number }) =>
    api<AdminUser>(`/admin/users/${id}/reactivate`, { method: 'POST' }),
  )
}

export function useChangeRole() {
  return useAccountAction(({ id, role }: { id: number; role: Role }) =>
    api<AdminUser>(`/admin/users/${id}/role`, { method: 'PATCH', body: { role } }),
  )
}

export function useCreateStaff() {
  return useAccountAction(
    (body: { phone: string; full_name: string; password: string; role: Role }) =>
      api<AdminUser>('/admin/users', { method: 'POST', body }),
  )
}
